from socket import *
import socket
import logging
from file_protocol import FileProtocol
import multiprocessing
import concurrent.futures

fp = FileProtocol()

def handle_client(connection, address):
    logging.warning(f"handling connection from {address}")
    buffer = ""
    try:
        while True:
            data = connection.recv(131072)
            if not data:
                break
            buffer += data.decode()
            while "\r\n\r\n" in buffer:
                command, buffer = buffer.split("\r\n\r\n", 1)
                result = fp.proses_string(command)
                response = result + "\r\n\r\n"
                connection.sendall(response.encode())
    except Exception as e:
        logging.warning(f"Error: {str(e)}")
    finally:
        logging.warning(f"Connection from {address} closed")
        connection.close()

class Server:
    def __init__(self, ipaddress='0.0.0.0', port=6767, pool_size=5):
        self.ipinfo = (ipaddress, port)
        self.pool_size = pool_size
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        logging.warning(f"Server is running at IP address {self.ipinfo} with a process pool size of {self.pool_size}")
        self.my_socket.bind(self.ipinfo)
        self.my_socket.listen(1)
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.pool_size) as executor:
            try:
                while True:
                    connection, client_address = self.my_socket.accept()
                    logging.warning(f"Connection from {client_address}")
                    
                    executor.submit(handle_client, connection, client_address)
            except KeyboardInterrupt:
                logging.warning("Server shutting down")
            except Exception as e:
                logging.warning(f"Error in server: {str(e)}")
            finally:
                if self.my_socket:
                    self.my_socket.close()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='File Server')
    parser.add_argument('--port', type=int, default=9090)
    parser.add_argument('--pool-size', type=int, default=5)
    args = parser.parse_args()
    serv = Server(ipaddress='0.0.0.0', port=args.port, pool_size=args.pool_size)
    serv.run()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
    main()