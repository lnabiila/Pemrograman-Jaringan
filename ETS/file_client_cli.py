import socket
import json
import base64
import logging
import os

server_address=('0.0.0.0',9090)

def send_command(command_str=""):
    global server_address
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_address)
    logging.warning(f"connecting to {server_address}")
    try:
        logging.warning(f"sending message ")
        sock.sendall((command_str + "\r\n\r\n").encode())
        # Look for the response, waiting until socket is done (no more data)
        data_received="" #empty string
        while True:
            #socket does not receive all data at once, data comes in part, need to be concatenated at the end of process
            data = sock.recv(4096)
            if data:
                #data is not empty, concat with previous content
                data_received += data.decode()
                if "\r\n\r\n" in data_received:
                    break
            else:
                # no more data, stop the process by break
                break
        # at this point, data_received (string) will contain all data coming from the socket
        # to be able to use the data_received as a dict, need to load it using json.loads()
        hasil = json.loads(data_received)
        logging.warning("data received from server:")
        return hasil
    except:
        logging.warning("error during data receiving")
        return False

def remote_list():
    command_str=f"LIST"
    hasil = send_command(command_str)
    if (hasil['status']=='OK'):
        print("daftar file : ")
        for nmfile in hasil['data']:
            print(f"- {nmfile}")
        return True
    else:
        print("Gagal")
        return False

def remote_get(filename=""):
    command_str=f"GET {filename}"
    hasil = send_command(command_str)
    if (hasil['status']=='OK'):
        #proses file dalam bentuk base64 ke bentuk bytes
        namafile= hasil['data_namafile']
        isifile = base64.b64decode(hasil['data_file'])
        fp = open(namafile,'wb+')
        fp.write(isifile)
        fp.close()
        return True
    else:
        print("Gagal")
        return False
        
def remote_upload(filepath):
    if not os.path.isfile(filepath):
        print(f"[UPLOAD ERROR] File lokal '{filepath}' tidak ditemukan.")
        return
    fn = os.path.basename(filepath)
    with open(filepath, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    command_str=f"UPLOAD {fn} {b64}"
    hasil = send_command(command_str)
    if (hasil['status']=='OK'):
        print(f"[UPLOAD] {hasil['data']}")
        return True
    else:
        print("Gagal")
        return False

def remote_delete(filename):
    command_str=f"DELETE {filename}"
    hasil = send_command(command_str)
    if (hasil['status']=='OK'):
        print(f"[DELETE] {hasil['data']}")
        return True
    else:
        print("Gagal")
        return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    remote_list()
    remote_get('donalbebek.jpg')
    remote_get('pokijan.jpg')
    remote_get('rfc2616.pdf')
    remote_upload('rfc2616_upload.pdf')
    remote_upload('donalbebek_upload.jpg')
    remote_list()
    remote_delete('rfc2616_upload.pdf')
    remote_delete('donalbebek_upload.jpg')