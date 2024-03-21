import cv2
import numpy as np
import socket
import sys
import pickle
import struct
import time
import threading
import logging

import os

logging.basicConfig(level=logging.DEBUG)

fps = 0
actual_time = 0
connecting = True

HOST_SERVER = '192.168.1.21'
PORT_SERVER = int('8090')

HOST_CLIENT = '192.168.1.21'
PORT_CLIENT = int('8091')

def initialise_data():
    global HOST_SERVER, PORT_SERVER, HOST_CLIENT, PORT_CLIENT
    if os.environ.get('HOST_SERVER'):
        HOST_SERVER = os.environ.get('HOST_SERVER')
    if os.environ.get('PORT_SERVER'):
        PORT_SERVER = int(os.environ.get('PORT_SERVER'))
    if os.environ.get('HOST_CLIENT'):
        HOST_CLIENT = os.environ.get('HOST_CLIENT')
    if os.environ.get('PORT_CLIENT'):
        PORT_CLIENT = int(os.environ.get('PORT_CLIENT'))


def initialise_server(host_server, port_server, host_client, port_client):
    global connecting
    global actual_time

    server = server_connection(host_server, port_server)

    conn, addr = server.accept()
    data = b''
    payload_size = struct.calcsize("L")

    clientsocket = client_connection(host_client, port_client)

    while True:
        try:
            timeout = time.time()

            # Retrieve message size
            while len(data) < payload_size:
                time_now = time.time()
                if(time_now - timeout > 1):
                    raise RuntimeError
                data += conn.recv(4096)

            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("L", packed_msg_size)[0]

            # Retrieve all data based on message size
            while len(data) < msg_size:
                data += conn.recv(4096)

            frame_data = data[:msg_size]
            data = data[msg_size:]

            # Extract frame
            frame = pickle.loads(frame_data)

            # Process
            frame = cv2.medianBlur(frame, 5)

            send_frame(clientsocket, frame)

        except (BrokenPipeError, ConnectionResetError):
            logging.info('Disconnected. retrying to connect...')
            connecting = True
            clientsocket = client_connection(host_client, port_client)
        except RuntimeError:
            logging.info('Error in the back server. Restarting connections...')
            connecting = True
            clientsocket.shutdown(2)
            clientsocket.close()
            server.shutdown(2)
            server.close()
            initialise_server(host_server, port_server, host_client, port_client)

def server_connection(host_server, port_server):
    connecting = True
    while connecting:
        try:
            logging.info(host_server)
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((host_server, port_server))
            server.listen(10)
            logging.info('Socket now listening')
            connecting = False
        except OSError:
            logging.info('Connection busy. Retrying in 3 seconds...')
            time.sleep(3)
    return server

def client_connection(host_client, port_client):
    global actual_time
    global connecting

    clientsocket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while connecting:
        try:
            logging.info('Connecting...')
            clientsocket.connect((host_client, port_client))
            connecting = False
            logging.info('Connection successful!')
            actual_time = time.time()
        except:
            print('Couldnt connect. Retrying in 3 seconds...')
            time.sleep(3)
    return clientsocket

def send_frame(cs, frame):
    global fps
    global actual_time

    data = pickle.dumps(frame)

    message_size = struct.pack("L", len(data))

    cs.sendall(message_size + data)

    fps += 1
    late_time = time.time()

    if (late_time - actual_time) >= 1:
        print(fps)
        fps = 0
        actual_time = time.time()

if __name__ == '__main__':
    initialise_data()
    initialise_server(HOST_SERVER, PORT_SERVER, HOST_CLIENT, PORT_CLIENT)


