import socket
import json
import base64
import logging
import os
import sys
import time
import random
import threading
import multiprocessing
import concurrent.futures
import argparse
from collections import defaultdict
import statistics
import csv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stress_test.log"),
        logging.StreamHandler()
    ]
)

class StressTestClient:
    def __init__(self, server_address=('localhost', 9090)):
        self.server_address = server_address
        self.results = {
            'upload': [],
            'download': []
        }
        self.success_count = {
            'upload': 0,
            'download': 0
        }
        self.fail_count = {
            'upload': 0,
            'download': 0
        }
        if not os.path.exists('test'): os.makedirs('test')
        if not os.path.exists('download'): os.makedirs('download')

    def make_sample_file(self, size_mb):
        fn = f"{size_mb}MB.bin"
        path = os.path.join('test', fn)
        if os.path.exists(path) and os.path.getsize(path) == size_mb * 1024 * 1024:
            logging.info(f"{fn} already exists")
            return path
        logging.info(f"Preparing sample file {fn}")
        with open(path, 'wb') as f:
            chunk_size = 1024 * 1024 
            for _ in range(size_mb): f.write(os.urandom(chunk_size))
        logging.info(f"Sample file generated: {path}")
        return path

    def send_command(self, command_str=""):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(600) 
        try:
            start_connect = time.time()
            sock.connect(self.server_address)
            connect_time = time.time() - start_connect
            logging.debug(f"uccessfully connected in {connect_time:.2f}s")
            chunks = [command_str[i:i+65536] for i in range(0, len(command_str), 65536)]
            for chunk in chunks: sock.sendall(chunk.encode())
            sock.sendall("\r\n\r\n".encode())
            data_received = "" 
            while True:
                try:
                    data = sock.recv(8192)
                    if data:
                        data_received += data.decode()
                        if "\r\n\r\n" in data_received: break
                    else: break
                except socket.timeout:
                    logging.error("Socket did not respond in time during data reception")
                    return {'status': 'ERROR', 'data': 'Socket did not respond in time during data reception'}
            json_response = data_received.split("\r\n\r\n")[0]
            hasil = json.loads(json_response)
            return hasil
        except socket.timeout as e:
            logging.error(f"Socket timeout: {str(e)}")
            return {'status': 'ERROR', 'data': f'Socket timeout: {str(e)}'}
        except ConnectionRefusedError:
            logging.error("Could not connect: server might be down or unreachable.")
            return {'status': 'ERROR', 'data': 'Could not connect: server might be down or unreachable.'}
        except Exception as e:
            logging.error(f"Error in send_command: {str(e)}")
            return {'status': 'ERROR', 'data': str(e)}
        finally: sock.close()

    def remote_upload(self, file_path, worker_id):
        start_time = time.time()
        fn = os.path.basename(file_path)
        size = os.path.getsize(file_path)
        try:
            logging.info(f"Worker {worker_id}: Starting upload of {fn} ({size/1024/1024:.2f} MB)")
            with open(file_path, 'rb') as fp: b64 = base64.b64encode(fp.read()).decode()
            command_str = f"UPLOAD {fn} {b64}"
            result = self.send_command(command_str)
            end_time = time.time()
            duration = end_time - start_time
            throughput = size / duration if duration > 0 else 0
            if result['status'] == 'OK':
                logging.info(f"Worker {worker_id}: Upload successful - {fn} ({size/1024/1024:.2f} MB) in {duration:.2f}s - {throughput/1024/1024:.2f} MB/s")
                self.success_count['upload'] += 1
            else:
                logging.error(f"Worker {worker_id}: Upload failed - {fn}: {result['data']}")
                self.fail_count['upload'] += 1
            return {
                'worker_id': worker_id,
                'operation': 'upload',
                'file_size': size,
                'duration': duration,
                'throughput': throughput,
                'status': result['status']
            }
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            logging.error(f"Worker {worker_id}: Upload exception - {fn}: {str(e)}")
            self.fail_count['upload'] += 1
            return {
                'worker_id': worker_id,
                'operation': 'upload',
                'file_size': size,
                'duration': duration,
                'throughput': 0,
                'status': 'ERROR',
                'error': str(e)
            }

    def remote_download(self, filename, worker_id):
        start_time = time.time()
        try:
            logging.info(f"Worker {worker_id}: Starting download of {filename}")
            command_str = f"GET {filename}"
            result = self.send_command(command_str)
            if result['status'] == 'OK':
                b64 = base64.b64decode(result['data_file'])
                size = len(b64)
                download_path = os.path.join('download', f"worker{worker_id}_{filename}")
                with open(download_path, 'wb') as f: f.write(b64)
                end_time = time.time()
                duration = end_time - start_time
                throughput = size / duration if duration > 0 else 0
                logging.info(f"Worker {worker_id}: Download successful - {filename} ({size/1024/1024:.2f} MB) in {duration:.2f}s - {throughput/1024/1024:.2f} MB/s")
                self.success_count['download'] += 1
                return {
                    'worker_id': worker_id,
                    'operation': 'download',
                    'file_size': size,
                    'duration': duration,
                    'throughput': throughput,
                    'status': 'OK'
                }
            else:
                end_time = time.time()
                duration = end_time - start_time
                logging.error(f"Worker {worker_id}: Download failed - {filename}: {result['data']}")
                self.fail_count['download'] += 1
                return {
                    'worker_id': worker_id,
                    'operation': 'download',
                    'file_size': 0,
                    'duration': duration,
                    'throughput': 0,
                    'status': 'ERROR',
                    'error': result['data']
                }
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            logging.error(f"Worker {worker_id}: Download exception - {filename}: {str(e)}")
            self.fail_count['download'] += 1
            return {
                'worker_id': worker_id,
                'operation': 'download',
                'file_size': 0,
                'duration': duration,
                'throughput': 0,
                'status': 'ERROR',
                'error': str(e)
            }

    def counter_reinitialization(self):
        self.success_count = {
            'upload': 0,
            'download': 0
        }
        self.fail_count = {
            'upload': 0,
            'download': 0
        }
        self.results = {
            'upload': [],
            'download': []
        }

    def run_stress_test(self, operation, file_size_mb, client_pool_size, executor_type='thread'):
        self.counter_reinitialization()
        if operation not in ['upload', 'download']:
            logging.error(f"Invalid operation: {operation}")
            return
        logging.info(f"Running {operation} stress test on {file_size_mb}MB files with {client_pool_size} {executor_type} workers")
        test_file = None
        if operation == 'upload' or operation == 'download': test_file = self.make_sample_file(file_size_mb)
        if operation == 'download':
            logging.info(f"Ensuring test file availability on server for download testing")
            upload_result = self.remote_upload(test_file, 0) 
            if upload_result['status'] != 'OK':
                logging.error(f"Test file upload error on server: {upload_result.get('error', 'Unknown error')}")
                return None
        if executor_type == 'thread': executor_class = concurrent.futures.ThreadPoolExecutor
        else: executor_class = concurrent.futures.ProcessPoolExecutor
        all_results = []
        with executor_class(max_workers=client_pool_size) as executor:
            futures = []
            for i in range(client_pool_size):
                if operation == 'upload': futures.append(executor.submit(self.remote_upload, test_file, i))
                elif operation == 'download':
                    file_name = os.path.basename(test_file)
                    futures.append(executor.submit(self.remote_download, file_name, i))
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    all_results.append(result)
                    self.results[operation].append(result)
                except Exception as e:
                    logging.error(f"Worker threw an exception: {str(e)}")
        durations = [r['duration'] for r in all_results if r['status'] == 'OK']
        throughputs = [r['throughput'] for r in all_results if r.get('throughput', 0) > 0]
        if not durations:
            logging.warning("Unable to calculate statistics: no successful operations recorded")
            return {
                'operation': operation,
                'file_size_mb': file_size_mb,
                'client_pool_size': client_pool_size,
                'executor_type': executor_type,
                'success_count': self.success_count[operation],
                'fail_count': self.fail_count[operation]
            }
        stats = {
            'operation': operation,
            'file_size_mb': file_size_mb,
            'client_pool_size': client_pool_size,
            'executor_type': executor_type,
            'avg_duration': statistics.mean(durations) if durations else 0,
            'avg_throughput': statistics.mean(throughputs) if throughputs else 0,
            'success_count': self.success_count[operation],
            'fail_count': self.fail_count[operation]
        }
        logging.info(f"Test complete: {stats['success_count']} succeeded, {stats['fail_count']} failed")
        logging.info(f"Average duration: {stats['avg_duration']:.2f}s, Average throughput: {stats['avg_throughput']/1024/1024:.2f} MB/s")
        return stats

    def run_tests(self, file_sizes, client_pool_sizes, server_pool_sizes, executor_types, operations):
        all_stats = []
        for server_pool_size in server_pool_sizes:
            logging.info(f"Testing server pool size: {server_pool_size}")
            input("When the server is ready, hit Enter to proceed")
            for executor_type in executor_types:
                for operation in operations:
                    for size in file_sizes:
                        for client_pool_size in client_pool_sizes:
                            stats = self.run_stress_test(operation, size, client_pool_size, executor_type)
                            if stats:
                                stats['server_pool_size'] = server_pool_size
                                all_stats.append(stats)
        self.make_csv(all_stats)
        
    def make_csv(self, all_stats):
        fn = f"stress_test_results.csv"
        with open(fn, 'w', newline='') as csvfile:
            fieldnames = ['operation', 'file_size_mb', 'client_pool_size', 'server_pool_size', 'executor_type', 'avg_duration', 'avg_throughput', 'success_count', 'fail_count']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for stats in all_stats: writer.writerow(stats)
        logging.info(f"Results saved to {fn}")
        return fn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Stress Test')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=9090)
    parser.add_argument('--operation', choices=['upload', 'download', 'all'], default='all')
    parser.add_argument('--file-sizes', type=int, nargs='+', default=[10, 50, 100])
    parser.add_argument('--client-pools', type=int, nargs='+', default=[1, 5, 50])
    parser.add_argument('--server-pools', type=int, nargs='+', default=[1, 5, 50])
    parser.add_argument('--executor', choices=['thread', 'process', 'both'], default='thread')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    if args.debug: logging.getLogger().setLevel(logging.DEBUG)
    file_sizes = args.file_sizes
    client_pool_sizes = args.client_pools
    server_pool_sizes = args.server_pools
    if args.executor == 'both': executor_types = ['thread', 'process']
    else: executor_types = [args.executor]   
    if args.operation == 'all': operations = ['download', 'upload']
    else: operations = [args.operation]
    client = StressTestClient((args.host, args.port))
    if len(operations) == 1 and len(file_sizes) == 1 and len(client_pool_sizes) == 1 and len(server_pool_sizes) == 1:
        logging.info(f"Performing a single test using operation={operations[0]}, file size={file_sizes[0]}MB, client pool={client_pool_sizes[0]}")
        stats = client.run_stress_test(operations[0], file_sizes[0], client_pool_sizes[0], executor_types[0])
        if stats:
            stats['server_pool_size'] = server_pool_sizes[0]
            client.make_csv([stats])
    else: client.run_tests(file_sizes, client_pool_sizes, server_pool_sizes, executor_types, operations)