import logging
import os
import pickle
import socket
import struct
import time
from tracemalloc import start

import cv2
import numpy as np
import requests

logging.basicConfig(level=logging.DEBUG)

actual_time = 0

CENTRAL_HOST = '192.168.1.21'
CENTRAL_PORT = 8000

DEPLOYMENT = 'Nautic'
TASK = 'Video Capturer'
SERVER_HOST = '192.168.1.21'
# SERVER_HOST = '150.214.108.92'
SERVER_PORT = 0
FC_NAME = 'Feature Communicator'
FS_NAME = 'Filter Selector'

fc_location = False
fs_location = False
connection_attempts = 0

MAX_FRAMES = 1
initialization_time = 0
start_send_frames_time = 0
total_time = 0


def calculateTimes():
    print('Initialization time: ' + str(start_send_frames_time - initialization_time))
    print('Send 1 frames time: ' + str(total_time - start_send_frames_time))
    print('Total time: ' + str(total_time - initialization_time))
    # time.sleep(5)


def initialiseData():
    global CENTRAL_HOST, CENTRAL_PORT, DEPLOYMENT, TASK, SERVER_HOST, SERVER_PORT
    if os.environ.get('CENTRAL_HOST'):
        CENTRAL_HOST = os.environ.get('CENTRAL_HOST')
    if os.environ.get('CENTRAL_PORT'):
        CENTRAL_PORT = int(os.environ.get('CENTRAL_PORT'))
    if os.environ.get('DEPLOYMENT'):
        DEPLOYMENT = os.environ.get('DEPLOYMENT')
    if os.environ.get('SERVER_HOST'):
        SERVER_HOST = os.environ.get('SERVER_HOST')


def initialiseTask():
    getLocations()
    startComunication()


def getLocations():
    global fc_location, fs_location, connection_attempts

    while (not fc_location or not fs_location):
        try:
            data_fc = {'deployment': DEPLOYMENT, 'name': TASK, 'ip': SERVER_HOST, 'port': SERVER_PORT, 'task_requested': FC_NAME}
            data_fs = {'deployment': DEPLOYMENT, 'name': TASK, 'ip': SERVER_HOST, 'port': SERVER_PORT, 'task_requested': FS_NAME}
            
            fc_request = requests.post('http://' + CENTRAL_HOST + ':' + str(CENTRAL_PORT) + '/api/location/', json=data_fc)
            fs_request = requests.post('http://' + CENTRAL_HOST + ':' + str(CENTRAL_PORT) + '/api/location/', json=data_fs)
            
            fc_location = fc_request.json()['data']
            fs_location = fs_request.json()['data']

            if not fc_location or not fs_location:
                logging.info('Tasks not deployed yet. Asking again in 5 seconds...')
                time.sleep(5)
        except requests.exceptions.ConnectionError:
            logging.info('Connection with Central Node not available. Asking again in 5 seconds...')
            time.sleep(5)


def resetLocations():
    global fc_location, fs_location, connection_attempts

    fc_location = False
    fs_location = False
    connection_attempts = 0


def startComunication():
    global start_send_frames_time
    capturer = createCameraCapturer()

    detection_socket = clientConnection(FC_NAME)
    visualize_socket = clientConnection(FS_NAME)
    
    start_send_frames_time = time.time()
    sendVideo(capturer, detection_socket, visualize_socket)


def createCameraCapturer():
    logging.info('Initialising camera...')
    cap = cv2.VideoCapture(0)
    width = 320
    height = 240
    # width = 640
    # height = 480
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    return cap


def clientConnection(location_name):
    global actual_time, connection_attempts
    connecting = True

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while connecting:
        try:
            location = getLocationByName(location_name)
            print(location)
            logging.info('Connecting to {a}...'.format(a=location['name']))
            client_socket.connect((location['ip'], int(location['port'])))
            connecting = False
            logging.info('Connection with {a} succesfull!'.format(a=location['name']))
            actual_time = time.time()
        except:
            connection_attempts += 1
            if connection_attempts > 3:
                logging.info('3 attempts of connection failing, asking for locations again and retrying...')
                resetLocations()
                getLocations()
            else:
                logging.info('Couldnt connect. Retrying in 3 seconds...')
            time.sleep(3)

    connection_attempts = 0
    return client_socket


def getLocationByName(name):
    if name == FC_NAME:
        return fc_location
    else:
        return fs_location


def sendVideo(capturer, detection_socket, visualize_socket):
    global actual_time, total_time
    fps = 0
    while fps < MAX_FRAMES:
        if capturer.isOpened():
            # width  = capturer.get(3)
            # length  = capturer.get(4)
            # print('Ancho: {a}, Alto: {b}'.format(a= width, b= length))
            try:
                ret,frame=capturer.read()

                sendFrame(detection_socket, frame)
                sendFrame(visualize_socket, frame)

                fps += 1
                # late_time = time.time()

                # if (late_time - actual_time) >= 1:
                #     logging.info(fps)
                #     fps = 0
                #     actual_time = time.time()
            except (BrokenPipeError, ConnectionResetError, OSError):
                logging.info('Disconnected. Retrying to connect...')
                capturer.release()
                detection_socket.close()
                visualize_socket.close()
                initialiseTask()
        else:
            logging.info('Camara no abierta')
            capturer.release()
            time.sleep(5)
    total_time = time.time()
    calculateTimes()


def sendFrame(socket, frame):
    data = pickle.dumps(frame)
    message_size = struct.pack("L", len(data))
    # print('Message size: {a}'.format(a = len(data)))
    socket.sendall(message_size + data)




if __name__ == '__main__':
    initialization_time = time.time()
    initialiseData()
    initialiseTask()