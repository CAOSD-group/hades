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
import numpy as np
import requests

logging.basicConfig(level=logging.DEBUG)

actual_time = 0
frame_senders = []

# CENTRAL_HOST = '127.0.0.1'
CENTRAL_HOST = '192.168.1.21'
CENTRAL_PORT = 8000

DEPLOYMENT = 'Nautic'
TASK = 'Feature Communicator'
SERVER_HOST = '192.168.1.21'
SERVER = '0.0.0.0'
FRAME_PORT = 8090
REQUEST_PORT = 8091

PLANET_FEATURE = "included"
GALAXY_FEATURE = ""
STAR_FEATURE = ""

planet_location = False
galaxy_location = False
star_location = False
PL_NAME = 'Planet Tracker'
GL_NAME = 'Galaxy Tracker'
ST_NAME = 'Star Tracker'

connection_attempts = 0

pageData = "<!DOCTYPE>" + \
            "<html>" + \
            "  <head>" + \
            "    <title>Feature Communicator Main Page</title>" + \
            "  </head>" + \
            "  <body>" + \
            "  </body>" + \
            "</html>"


class MyHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()


    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes(pageData, "utf8"))
        else:
            self.send_response(404)


    def do_POST(self):
        if self.path == '/open':
            self.send_response(200)
            self.send_header('Content-type', 'json/html')
            self.end_headers()
            print('Headers enviados')

            length = int(self.headers.get('content-length'))
            post_body = self.rfile.read(length)
            print('Datos extraidos')

            data = json.loads(post_body.decode("utf-8"))
            logging.info('Restarting connection with socket...')
            open_connection(data)

        if self.path == '/stop':
            self.send_response(200)
            self.send_header('Content-type', 'json/html')
            self.end_headers()

            length = int(self.headers.get('content-length'))
            post_body = self.rfile.read(length)

            data = json.loads(post_body.decode("utf-8"))
            logging.info('Stopping connection with socket...')
            stop_connection(data)


def open_connection(data):
    global frame_senders
    name = data['name']
    for i in range(len(frame_senders)):
        if frame_senders[i].name == name:
            frame_senders[i].status = 'opened'
            logging.info(frame_senders[i].name + ' open.')

def stop_connection(data):
    global frame_senders
    name = data['name']
    for i in range(len(frame_senders)):
        if frame_senders[i].name == name:
            frame_senders[i].status = 'closed'
            logging.info(frame_senders[i].name + ' close.')


class ComplexSocket:
    def __init__(self, name, client_socket, host, port):
        self.name = name
        self.status = 'opened'
        self.client_socket = client_socket
        self.host = host
        self.port = port


def initialiseData():
    global CENTRAL_HOST, CENTRAL_PORT, DEPLOYMENT, SERVER_HOST, FRAME_PORT, REQUEST_PORT, PLANET_FEATURE, GALAXY_FEATURE, STAR_FEATURE
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
    if os.environ.get('PLANET_FEATURE'):
        PLANET_FEATURE = os.environ.get('PLANET_FEATURE')
    if os.environ.get('GALAXY_FEATURE'):
        GALAXY_FEATURE = os.environ.get('GALAXY_FEATURE')
    if os.environ.get('STAR_FEATURE'):
        STAR_FEATURE = os.environ.get('STAR_FEATURE')


def initialiseRequestServer():
    requestsThread = threading.Thread(target=startRequestServer)
    requestsThread.start()


def startRequestServer():
    with socketserver.TCPServer((SERVER, REQUEST_PORT), MyHandler) as httpd:
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
    while not fulfilledRequiredLocations():
        try:
            fulfillRequiredLocations()
            
            if not fulfilledRequiredLocations():
                logging.info('Tasks not deployed yet. Asking again in 5 seconds...')
                time.sleep(5)
        except requests.exceptions.ConnectionError:
            logging.info('Connection with Central Node not available. Asking again in 5 seconds...')
            time.sleep(5)


def resetLocations():
    global planet_location, galaxy_location, star_location, connection_attempts

    planet_location = False
    galaxy_location = False
    star_location = False
    connection_attempts = 0


def fulfilledRequiredLocations():
    result = True
    if PLANET_FEATURE and not planet_location:
        result = False
    if GALAXY_FEATURE and not galaxy_location:
        result = False
    if STAR_FEATURE and not star_location:
        result = False
    return result


def fulfillRequiredLocations():
    global planet_location, galaxy_location, star_location
    if PLANET_FEATURE:
        data_planet = {'deployment': DEPLOYMENT, 'name': TASK, 'ip': SERVER_HOST, 'port': FRAME_PORT, 'request_port': REQUEST_PORT, 'task_requested': PL_NAME}
        planet_request = requests.post('http://' + CENTRAL_HOST + ':' + str(CENTRAL_PORT) + '/api/location/', json=data_planet)
        planet_location = planet_request.json()['data']
    if GALAXY_FEATURE:
        data_galaxy = {'deployment': DEPLOYMENT, 'name': TASK, 'ip': SERVER_HOST, 'port': FRAME_PORT, 'request_port': REQUEST_PORT, 'task_requested': GL_NAME}
        galaxy_request = requests.post('http://' + CENTRAL_HOST + ':' + str(CENTRAL_PORT) + '/api/location/', json=data_galaxy)
        galaxy_location = galaxy_request.json()['data']
    if STAR_FEATURE:
        data_star = {'deployment': DEPLOYMENT, 'name': TASK, 'ip': SERVER_HOST, 'port': FRAME_PORT, 'request_port': REQUEST_PORT, 'task_requested': ST_NAME}
        star_request = requests.post('http://' + CENTRAL_HOST + ':' + str(CENTRAL_PORT) + '/api/location/', json=data_star)
        star_location = star_request.json()['data']
    pass


def startCommunication():
    frame_receiver = createFrameReceiver()
    frame_senders = createFrameSenders()
    receiveAndSendVideo(frame_receiver, frame_senders)


def createFrameReceiver():
    connecting = True
    while connecting:
        try:
            logging.info(SERVER_HOST)
            frame_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            frame_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            frame_server.bind((SERVER, FRAME_PORT))
            frame_server.listen(10)
            logging.info('Socket now listening')
            connecting = False
        except OSError:
            logging.info('Connection busy. Retrying in 3 seconds...')
            time.sleep(3)
    return frame_server


def createFrameSenders():
    global frame_senders
    frame_senders = []
    feature_list = getFeatureConnectionList()
    for feature_name in feature_list:
        print('Iniciando comunicacion con {task}...'.format(task=feature_name))
        frame_sender = createFrameSender(feature_name)
        frame_senders.append(frame_sender)
        logging.info('Connection added successfully')
    return frame_senders


def createFrameSender(feature_name):
    global actual_time, connection_attempts
    connecting = True

    client_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    frame_sender = False

    while connecting:
        try:
            logging.info('Connecting...')
            location = getFeatureLocationByName(feature_name)
            client_socket.connect((location['ip'], location['port']))
            connecting = False
            logging.info('Connection successful!')
            frame_sender = ComplexSocket(feature_name, client_socket, location['ip'], location['port'])
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
    return frame_sender


def getFeatureLocationByName(name):
    location = False
    if name == ST_NAME:
        location = star_location
    elif name == GL_NAME:
        location = galaxy_location
    else:
        location = planet_location
    return location


def getFeatureConnectionList():
    result = []
    if planet_location:
        result.append(PL_NAME)
    if galaxy_location:
        result.append(GL_NAME)
    if star_location:
        result.append(ST_NAME)
    return result


def receiveAndSendVideo(frame_receiver, frame_senders):
    conn, addr = frame_receiver.accept()    
    data = b''                              
    payload_size = struct.calcsize("L")     

    global actual_time
    fps = 0

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

            frame = pickle.loads(frame_data)
            frame = processFrame(frame)

            for complex_socket in frame_senders:
                if complex_socket.status == 'opened':
                    sendFrame(complex_socket.client_socket, frame)
            fps += 1
            late_time = time.time()
            if (late_time - actual_time) >= 1:
                print(fps)
                fps = 0
                for complex_socket in frame_senders:
                    if complex_socket.status == 'opened':
                        logging.info('Sending frames to ' + complex_socket.name)
                actual_time = time.time()
        except (BrokenPipeError, ConnectionResetError):
            logging.info('Disconnected. retrying to connect...')
            for i in range(len(frame_senders)):
                logging.info('Connecting with ' + frame_senders[i].name)
                frame_senders[i].client_socket.close()
                time.sleep(3)
                frame_senders[i] = createFrameSender(frame_senders[i].name)
        except RuntimeError:
            logging.info('Error in the back server. Restarting connections...')
            connecting = True
            frame_receiver.shutdown(2)
            frame_receiver.close()
            for i in range(len(frame_senders)):
                logging.info('Connecting with ' + frame_senders[i].name)
                frame_senders[i].client_socket.close()
                time.sleep(3)
            
            initialiseTask()


def processFrame(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return frame


def sendFrame(client_socket, frame):
    data = pickle.dumps(frame)
    message_size = struct.pack("L", len(data))
    client_socket.sendall(message_size + data)


if __name__ == '__main__':
    initialiseData()
    initialiseRequestServer()
    initialiseTask()

