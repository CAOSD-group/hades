import http.server
import json
import logging
import os
import pickle
import socket
import socketserver
import struct
import sys
import threading
import time

import cv2
from django.db import connection
import numpy as np
import requests
import socketio
import socketio.exceptions as IOException

logging.basicConfig(level=logging.DEBUG)

actual_time = 0
configuration= 'galactic'

CENTRAL_HOST = '192.168.1.21'
CENTRAL_PORT = 8000

DEPLOYMENT = 'Nautic'
TASK = 'Filter Selector'
SERVER_HOST = '192.168.1.21'
# SERVER_HOST = '150.214.108.92'
FRAME_PORT = 8092
REQUEST_PORT = 8093
VS_NAME = 'Visualizer'

vs_location = False

connection_attempts = 0

initialization_time = 0
start_receiving_and_processing_frames = 0
total_time = 0

MAX_FRAMES = 1


def calculateTimes():
    print('Initialization time: ' + str(start_receiving_and_processing_frames - initialization_time))
    print('Send 1 frame time: ' + str(total_time - start_receiving_and_processing_frames))
    print('Total time: ' + str(total_time - initialization_time))
    # time.sleep(3) # Dejar tiempo para cerrar conexiones y camara


# ------ Request Server to change Filters in real time ------ #

pageData = "<!DOCTYPE>" + \
            "<html>" + \
            "  <head>" + \
            "    <title>Filter Selector Main Page</title>" + \
            "  </head>" + \
            "  <body>" + \
            "  </body>" + \
            "</html>"


class MyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes(pageData, "utf8"))
        else:
            self.send_response(404)

    def do_POST(self):
        if self.path == '/filter':
            self.send_response(200)
            self.send_header('Content-type', 'json/html')
            self.end_headers()

            length = int(self.headers.get('Content-Length'))
            post_body = self.rfile.read(length)

            data = json.loads(post_body.decode("utf-8"))
            logging.info('Changing parameters...')
            change_parameters(data)
            logging.info('Parameters configurated!')

# ------ Request Server to change Filters in real time ------ #


def initialiseData():
    global CENTRAL_HOST, CENTRAL_PORT, DEPLOYMENT, SERVER_HOST, FRAME_PORT, REQUEST_PORT
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
    if os.environ.get('REQUEST_PORT'):
        REQUEST_PORT = int(os.environ.get('REQUEST_PORT'))


def initialiseRequestServer():
    requestsThread = threading.Thread(target=startRequestServer)
    requestsThread.start()


def startRequestServer():
    with socketserver.TCPServer((SERVER_HOST, REQUEST_PORT), MyHandler) as httpd:
        logging.info("Receiving requests at port: {port}".format(port=REQUEST_PORT))
        try:
            httpd.serve_forever()
        except:
            httpd.server_close()
            logging.info('Server closed.')


def initialiseTask():
    getLocations()
    startCommunication()


def getLocations():
    global vs_location

    while not vs_location:
        try:
            data_vs = {'deployment': DEPLOYMENT, 'name': TASK, 'ip': SERVER_HOST, 'port': FRAME_PORT, 'request_port': REQUEST_PORT, 'task_requested': VS_NAME}
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
    frame_sender = createFrameSender()
    start_receiving_and_processing_frames = time.time()
    receiveAndSendVideo(frame_receiver, frame_sender)


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


def createFrameSender():
    global actual_time, connection_attempts
    connecting = True

    frame_sender = socketio.Client()

    while connecting:
        try:
            logging.info('Connecting...')
            direction = 'http://' + vs_location['ip'] + ':' + str(vs_location['port'])
            frame_sender.connect(direction)
            connecting = False
            logging.info('Connection successful!')
            actual_time = time.time()
        except:
            connection_attempts += 1
            if connection_attempts > 3:
                logging.info('3 attempts of connection failing, asking for locations again and retrying...')
                resetLocations()
                getLocations()
            else:
                print('Couldnt connect. Retrying in 3 seconds...')
            time.sleep(3)

    connection_attempts = 0
    return frame_sender


def receiveAndSendVideo(frame_receiver, frame_sender):
    conn, addr = frame_receiver.accept()    # Start socket to receive video
    data = b''                              # Create buffer to store data
    payload_size = struct.calcsize("L")     # Set Payload Size

    global total_time
    global configuration
    fps = 0

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
            
            # Retrieve all data based on message size
            while len(data) < msg_size:
                data += conn.recv(4096)
            
            frame_data = data[:msg_size]
            data = data[msg_size:]
            
            frame = pickle.loads(frame_data)
            frame = processFrame(frame)

            data = pickle.dumps(frame)
            message_size = struct.pack("L", len(data))
            print('Message size: {a}'.format(a = len(data)))

            encode_param=[int(cv2.IMWRITE_JPEG_QUALITY),90]
            result, imgencode = cv2.imencode('.jpg', frame, encode_param)
            send_data = np.array(imgencode)
            # stringData = send_data.tostring()
            stringData = send_data.tobytes()


            frame_sender.emit('frame', stringData)
            
            fps += 1
            # late_time = time.time()
            # if (late_time - actual_time) >= 1:
            #     print(fps)
            #     fps = 0
            #     actual_time = time.time()
        except (BrokenPipeError, ConnectionResetError, OSError, socketio.exceptions.BadNamespaceError):
        # except (NameError):
            logging.info(' ------------ Disconnected. retrying to connect... ----------------- ')
            frame_sender.disconnect()
            #frame_sender = createFrameSender()
        except RuntimeError:
            logging.info(' ---------------- Error in the back server. Restarting connections... ------------------------ ')
            frame_sender.disconnect()
            # frame_receiver.shutdown(2)
            frame_receiver.close()
            initialiseTask()
            
    total_time = time.time()
    calculateTimes()
    frame_sender.disconnect()



def processFrame(frame):
    global configuration

    if configuration == 'none':
        pass
    if configuration == 'galactic':
        frame = modify_brightness(frame, -150)
        frame = cv2.medianBlur(frame, 9)
    if configuration == 'sky':
        frame = modify_brightness(frame, 100)
        frame = cv2.medianBlur(frame, 9)

    return frame

def change_parameters(data):
    global configuration
    posible_filters = ['none', 'galactic', 'sky']
    name = data['name']
    if name in posible_filters:
        configuration = name


def modify_brightness(img, value=30):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    v = cv2.add(v,value)
    v[v > 255] = 255
    v[v < 0] = 0
    final_hsv = cv2.merge((h, s, v))
    img = cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)
    return img


if __name__ == '__main__':
    initialization_time = time.time()
    initialiseData()
    # initialiseRequestServer()
    initialiseTask()
