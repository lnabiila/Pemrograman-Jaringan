from socket import *
import socket
import threading
import logging
import time
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO)

def process_string(request_string, client_address):
    if request_string.startswith("TIME") and request_string.endswith("\r\n"):
        now = datetime.now()
        waktu = now.strftime("JAM %H:%M:%S")
        logging.info(f"Client {client_address} requested time")
        return f"{waktu}\r\n"
    
    elif request_string.startswith("QUIT") and request_string.endswith("\r\n"):
        logging.info(f"Client {client_address} sent QUIT")
        return "QUIT\r\n"

    return "OK\r\n"


class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        super().__init__()
        self.connection = connection
        self.address = address

    def run(self):
        while True:
            try:
                data = self.connection.recv(32)
                if data:
                    request_s = data.decode()
                    balas = process_string(request_s, self.address)
                    self.connection.sendall(balas.encode())
                    if balas == "QUIT\r\n":
                        break
                else:
                    break
            except Exception as e:
                logging.error(f"Error with client {self.address}: {e}")
                break

        self.connection.close()


class Server(threading.Thread):
    def __init__(self):
        super().__init__()
        self.the_clients = []
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def run(self):
        self.my_socket.bind(('172.16.16.101', 45000))
        self.my_socket.listen(5)
        logging.info("Server started on 172.16.16.101:45000")
        while True:
            conn, client_address = self.my_socket.accept()
            logging.info(f"Connection from {client_address}")
            client_thread = ProcessTheClient(conn, client_address)
            client_thread.start()
            self.the_clients.append(client_thread)


def main():
    svr = Server()
    svr.start()


if __name__ == "__main__":
    main()
