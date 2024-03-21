import json
import logging
import os
import pickle
import socket
import struct
import sys
import time

import cv2
import cv2.aruco as aruco
import numpy as np
import requests
import socketio

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

actual_time = 0

# ------- Detection Parameters -------
aruco_dict = aruco.Dictionary_get(aruco.DICT_5X5_1000)
parameters = aruco.DetectorParameters_create()
parameters.minDistanceToBorder = 0
parameters.adaptiveThreshWinSizeMax = 400
marker = aruco.drawMarker(aruco_dict, 200, 200)
marker = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
# ------- Detection Parameters -------

CENTRAL_HOST = '192.168.1.21'
CENTRAL_PORT = 8000

DEPLOYMENT = 'Nautic'
TASK = 'Planet Tracker'
SERVER_HOST = '192.168.1.21'
# SERVER_HOST = '150.214.108.92'
FRAME_PORT = 8096
VS_NAME = 'Visualizer'
CAMERA_WIDTH = 320
CAMERA_HEIGHT = 240

vs_location = False

connection_attempts = 0

initialization_time = 0
start_receiving_and_processing_frames = 0
total_time = 0

MAX_FRAMES = 100


def calculateTimes():
    print('Initialization time: ' + str(start_receiving_and_processing_frames - initialization_time))
    print('Send 100 frames time: ' + str(total_time - start_receiving_and_processing_frames))
    print('Total time: ' + str(total_time - initialization_time))
    # time.sleep(1) # Dejar tiempo para cerrar conexiones y camara


def initialiseData():
    global CENTRAL_HOST, CENTRAL_PORT, DEPLOYMENT, SERVER_HOST, FRAME_PORT, CAMERA_WIDTH, CAMERA_HEIGHT
    if os.environ.get('CENTRAL_HOST'):
        CENTRAL_HOST = os.environ.get('CENTRAL_HOST')
    if os.environ.get('CENTRAL_PORT'):
        CENTRAL_PORT = int(os.environ.get('CENTRAL_PORT'))
    if os.environ.get('DEPLOYMENT'):
        DEPLOYMENT = os.environ.get('DEPLOYMENT')
    if os.environ.get('SERVER_HOST'):
        SERVER_HOST = os.environ.get('SERVER_HOST')
    if os.environ.get('FRAME_PORT'):
        FRAME_PORT = int(os.environ.get('FRAME_PORT'))
    if os.environ.get('CAMERA_WIDTH'):
        CAMERA_WIDTH = int(os.environ.get('CAMERA_WIDTH'))
    if os.environ.get('CAMERA_HEIGHT'):
        CAMERA_HEIGHT = int(os.environ.get('CAMERA_HEIGHT'))


def initialiseTask():
    getLocations()
    startCommunication()


def getLocations():
    global vs_location

    while not vs_location:
        try:
            data_vs = {'deployment': DEPLOYMENT, 'name': TASK, 'ip': SERVER_HOST, 'port': FRAME_PORT, 'task_requested': VS_NAME}
            vs_request = requests.post('http://' + CENTRAL_HOST + ':' + str(CENTRAL_PORT) + '/api/location/', json=data_vs)
            vs_location = vs_request.json()['data']

            if not vs_location:
                logging.info('Tasks not deployed yet. Asking again in 5 seconds...')
                time.sleep(5)
        except requests.exceptions.ConnectionError:
            logging.info('Connection with Central Node not available. Asking again in 5 seconds...')
            time.sleep(5)


def resetLocations():
    global vs_location, connection_attempts

    vs_location = False
    connection_attempts = 0


def startCommunication():
    global start_receiving_and_processing_frames
    frame_receiver = createFrameReceiver()
    position_sender = createPositionSender()
    start_receiving_and_processing_frames = time.time()
    receiveVideoAndSendPositions(frame_receiver, position_sender)


def createFrameReceiver():
    connecting = True
    while connecting:
        try:
            logging.info(SERVER_HOST)
            frame_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            frame_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            frame_server.bind((SERVER_HOST, FRAME_PORT))
            frame_server.listen(10)
            logging.info('Socket now listening')
            connecting = False
        except OSError:
            logging.info('Connection busy. Retrying in 3 seconds...')
            time.sleep(3)
    return frame_server


def createPositionSender():
    global actual_time, connection_attempts
    connecting = True

    frame_sender = socketio.Client()
    
    while connecting:
        try:
            direction = 'http://' + vs_location['ip'] + ':' + str(vs_location['port'])
            logging.info('Connecting to {ip}...'.format(ip=vs_location['ip']))
            frame_sender.connect(direction)
            connecting = False
            logging.info('Connection successful!')
            actual_time = time.time()
        except:
            connection_attempts +=1
            if connection_attempts > 3:
                logging.info('3 attempts of connection failing, asking for locations again and retrying...')
                resetLocations()
                getLocations()
            else:
                print('Couldnt connect. Retrying in 3 seconds...')
            time.sleep(3)

    return frame_sender


def receiveVideoAndSendPositions(frame_receiver, position_sender):
    conn, addr = frame_receiver.accept()    # Start socket to receive video
    data = b''                              # Create buffer to store data
    payload_size = struct.calcsize("L")     # Set Payload Size

    global total_time
    global configuration
    fps = 0
    empty_sended = False
    last_sended = 0

    while fps < MAX_FRAMES:
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

            # Process
            corners, ids, rejected = aruco.detectMarkers(
            frame, aruco_dict, parameters=parameters)

            coordinates_list = []
            for (i, b) in enumerate(corners):
                c1 = (b[0][0][0], b[0][0][1])
                c2 = (b[0][1][0], b[0][1][1])
                c3 = (b[0][2][0], b[0][2][1])
                c4 = (b[0][3][0], b[0][3][1])

                aruco_id = int(ids[i])
                x = int((c1[0]+c2[0]+c3[0]+c4[0])/4)
                y = int((c1[1]+c2[1]+c3[1]+c4[1])/4)
                x_converted = convert(x, CAMERA_WIDTH)
                y_converted = convert(y, CAMERA_HEIGHT) * (-1)
                radius = pow((pow(c1[0] - c3[0], 2) + pow(c1[1] - c3[1], 2)), 0.5)
                resized_radius = int(radius / 5)

                element = [aruco_id, x_converted, y_converted, resized_radius]
                #print(element)
                coordinates_list.append(element)

            if len(coordinates_list) >= 1:
                # print(coordinates_list)
                # print('-------------------------')
                json_data = {'coord': coordinates_list}
                position_sender.emit('aruco', json_data)
                print('Tamaño de la peticion: {a}'.format(a=len(json.dumps(json_data))))
                last_sended = time.time()
                empty_sended = False
            elif len(coordinates_list) < 1 and (not empty_sended):
                actual_time = time.time()
                if (actual_time - last_sended) > 1:
                    json_data = {'coord': []}
                    position_sender.emit('aruco', json_data)
                    empty_sended = True
            fps += 1
        except RuntimeError:
            logging.info('Error in the back server. Restarting connection...')
            # frame_receiver.shutdown(2)
            frame_receiver.close()
            position_sender.disconnect()
            # initialiseTask()
    total_time = time.time()
    calculateTimes()
    position_sender.disconnect()





def convert(value, max):
    res = value * 150 / max
    res -= 75
    return res


if __name__ == '__main__':
    initialization_time = time.time()
    initialiseData()
    initialiseTask()
