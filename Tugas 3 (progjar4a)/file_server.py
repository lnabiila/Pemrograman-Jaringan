from socket import *
import socket
import threading
import logging
import time
import sys

from file_protocol import  FileProtocol
fp = FileProtocol()

class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        threading.Thread.__init__(self)
        self.connection = connection
        self.address = address
        
    def run(self):
        buffer = ""
        while True:
            try:
                chunk = self.connection.recv(4096)
                if not chunk:
                    break
                buffer += chunk.decode()

                while "\r\n\r\n" in buffer:
                    cmd, _, buffer = buffer.partition("\r\n\r\n")
                    hasil = fp.proses_string(cmd)
                    hasil = hasil + "\r\n\r\n"
                    self.connection.sendall((hasil).encode())
            except Exception as e:
                logging.warning(f"Error saat memproses client: {e}")
                break
        self.connection.close()

class Server(threading.Thread):
    def __init__(self,ipaddress='0.0.0.0',port=9999):
        threading.Thread.__init__(self)
        self.ipinfo=(ipaddress,port)
        self.the_clients = []
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        logging.warning(f"server berjalan di ip address {self.ipinfo}")
        self.my_socket.bind(self.ipinfo)
        self.my_socket.listen(1)
        while True:
            self.connection, self.client_address = self.my_socket.accept()
            logging.warning(f"connection from {self.client_address}")

            clt = ProcessTheClient(self.connection, self.client_address)
            clt.start()
            self.the_clients.append(clt)

def main():
    svr = Server(ipaddress='0.0.0.0',port=9090)
    svr.start()

if __name__ == "__main__":
    main()