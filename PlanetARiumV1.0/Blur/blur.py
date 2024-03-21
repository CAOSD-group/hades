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

blur = None

HOST_SERVER = '192.168.1.21'
PORT_SERVER = int('8089')

HOST_CLIENT = '192.168.1.21'
PORT_CLIENT = int('8099')

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

def initialise_client(host_client, port_client):
    connecting = True

    clientsocket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    while connecting:
        try:
            logging.info('Conectando...')
            clientsocket.connect((host_client,port_client))
            connecting = False
            logging.info('Conectado con exito!')
        except:
            print('No ha sido posible conectarse. Reintentando en 3 segundos...')
            time.sleep(3)

    while True:
        # Serialize frame
        data = pickle.dumps(blur)
        # Send message length first
        message_size = struct.pack("L", len(data)) ### CHANGED
        # Then data
        clientsocket.sendall(message_size + data)

def initialise_server(host_server, port_server):
    logging.info(host_server)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    logging.info('Socket created')

    s.bind((host_server, port_server))
    logging.info('Socket bind complete')
    s.listen(10)
    logging.info('Socket now listening')

    conn, addr = s.accept()

    data = b'' ### CHANGED
    payload_size = struct.calcsize("L") ### CHANGED

    while True:

        # Retrieve message size
        while len(data) < payload_size:
            data += conn.recv(4096)

        packed_msg_size = data[:payload_size]
        data = data[payload_size:]
        msg_size = struct.unpack("L", packed_msg_size)[0] ### CHANGED

        # Retrieve all data based on message size
        while len(data) < msg_size:
            data += conn.recv(4096)

        frame_data = data[:msg_size]
        data = data[msg_size:]

        # Extract frame
        frame = pickle.loads(frame_data)

        # Process
        global blur
        blur = cv2.medianBlur(frame, 15)

        # Show
        #cv2.imshow('frame', grey)
        #cv2.waitKey(1)

if __name__ == '__main__':
    initialise_data()

    t1 = threading.Thread(target=initialise_server, args=(HOST_SERVER, PORT_SERVER))
    t1.start()

    t2 = threading.Thread(target=initialise_client, args=(HOST_CLIENT, PORT_CLIENT))
    t2.start()
