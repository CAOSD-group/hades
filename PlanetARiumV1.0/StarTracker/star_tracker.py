import cv2
import numpy as np
import json
import requests

import pickle
import struct
import os
import sys
import logging
import time

import socket
import socketio

logging.basicConfig(level=logging.DEBUG)

HOST_SERVER = '192.168.1.21'
PORT_SERVER = int('8090')

HOST_CLIENT = '192.168.1.21'
PORT_CLIENT = int('8100')

def initialise_data():
    global HOST_CLIENT, PORT_CLIENT, HOST_SERVER, PORT_SERVER
    if os.environ.get('HOST_CLIENT'):
        HOST_CLIENT = os.environ.get('HOST_CLIENT')
    if os.environ.get('PORT_CLIENT'):
        PORT_CLIENT = int(os.environ.get('PORT_CLIENT'))
    if os.environ.get('HOST_SERVER'):
        HOST_SERVER = os.environ.get('HOST_SERVER')
    if os.environ.get('PORT_SERVER'):
        PORT_SERVER = int(os.environ.get('PORT_SERVER'))

def initialise_server(host_server, port_server, host_client, port_client):
    connecting = True
    global actual_time
    empty_sended = False
    last_sended = 0
    camera_width = 320
    camera_height = 240

    # Blob Detection Parameters
    detector = create_detector()

    # Server Socket Initialization
    server = server_connection(host_server, port_server)
    
    # Connection variables and Data Format
    conn, addr = server.accept()
    data = b''
    payload_size = struct.calcsize("L")

    # Client Socket Initialization
    clientsocket = socketio.Client()

    # Connection Phase
    while(connecting):
        try:
            logging.info('Connecting...')
            direction = 'http://' + host_client + ':' + str(port_client)
            clientsocket.connect(direction)
            connecting = False
            logging.info('Connection successful!')

        except:
            logging.info('Couldnt connect. Retrying in 3 seconds...')
            time.sleep(3)

    # Receive and Process Frames
    while True:
        try:
            timeout = time.time()

            while len(data) < payload_size:
                time_now = time.time()
                if(time_now - timeout > 1):
                    raise RuntimeError
                data += conn.recv(4096)

            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("L", packed_msg_size)[0]

            while len(data) < msg_size:
                data += conn.recv(4096)

            frame_data = data[:msg_size]
            data = data[msg_size:]

            # Extract frame
            frame = pickle.loads(frame_data)

            # Get Keypoints and Send
            keypoints = detector.detect(frame)
            coordinates_list = []
            for kp in keypoints:
                x = int(kp.pt[0])
                y = int(kp.pt[1])
                radius = int(kp.size)
                #Transformar a +-150 las coordinales
                x_converted = convert(x, camera_width)
                y_converted = convert(y, camera_height) * (-1)
                element = [x_converted, y_converted, kp.size]
                coordinates_list.append(element)
            if len(coordinates_list) > 2:
                print(coordinates_list)
                print('-------------------------')
                json_data = {'coord': coordinates_list}
                clientsocket.emit('blobs', json_data)
                last_sended = time.time()
                empty_sended = False
            elif len(coordinates_list) <= 2 and (not empty_sended):
                actual_time = time.time()
                if (actual_time - last_sended) > 1:
                    json_data = {'coord': []}
                    clientsocket.emit('blobs', json_data)
                    empty_sended = True
        except RuntimeError:
            logging.info('Error in the back server. Restarting connection...')
            server.shutdown(2)
            server.close()
            clientsocket.disconnect()
            initialise_server(HOST_SERVER, PORT_SERVER, HOST_CLIENT, PORT_CLIENT)

def create_detector():
    params = cv2.SimpleBlobDetector_Params()

    params.minThreshold = 10
    params.maxThreshold = 200

    # Set Area filtering parameters
    params.filterByArea = True
    params.minArea = 30

    # Set Circularity filtering parameters
    params.filterByCircularity = True
    #params.minCircularity = 0.9
    params.minCircularity = 0.85

    # Set Convexity filtering parameters
    params.filterByConvexity = True
    #params.minConvexity = 0.2
    params.minConvexity = 0.4

    params.filterByInertia = True
    params.minInertiaRatio = 0.1

    detector = cv2.SimpleBlobDetector_create(params)
    return detector

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

def convert(value, max):
    res = value * 150 / max
    res -= 75
    return res

if __name__ == '__main__':
    initialise_data()
    initialise_server(HOST_SERVER, PORT_SERVER, HOST_CLIENT, PORT_CLIENT)