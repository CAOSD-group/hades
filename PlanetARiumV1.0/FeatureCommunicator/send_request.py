import socket
import sys
import pickle
import struct
import time
import logging
import requests
import json

import os

logging.basicConfig(level=logging.DEBUG)

HOST_CLIENT = '150.214.108.92'
PORT_CLIENT = int('8089')

PORT_CLIENT_2 = int('8104')

def send_request(data):
    #data = {'coord': [200,300,20]}
    r = requests.post('http://' + HOST_CLIENT + ':' + str(PORT_CLIENT) + '/connection', json=data)

def send_open_request(data):
    r = requests.post('http://' + HOST_CLIENT + ':' + str(PORT_CLIENT) + '/open', json=data)

def send_stop_request(data):
    r = requests.post('http://' + HOST_CLIENT + ':' + str(PORT_CLIENT) + '/stop', json=data)

def send_close_request(data):
    r = requests.post('http://' + HOST_CLIENT + ':' + str(PORT_CLIENT) + '/close', json=data)

def send_filter_request(data):
    r = requests.post('http://' + HOST_CLIENT + ':' + str(PORT_CLIENT_2) + '/filter', json=data)


if __name__ == '__main__':
    time.sleep(1)
    connection1 = {
        'name': 'aruco',
        'host': '150.214.108.92',
        'port': '8090'
    }

    connection2 = {
        'name': 'qr',
        'host': '150.214.108.92',
        'port': '8091'
    }

    task1 = {
        'name': 'aruco'
    }

    task2 = {
        'name': 'qr'
    }

    filter1 = {
        'name': 'none'
    }

    filter2 = {
        'name': 'galactic'
    }

    filter3 = {
        'name': 'sky'
    }

    filter4 = {
        'name': 'starry'
    }

    filter5 = {
        'name': 'darken'
    }

    send_request(connection1)
    #send_request(connection2)

    #send_open_request(task1)
    #send_open_request(task2)

    #send_stop_request(task1)
    #send_stop_request(task2)

    #send_close_request(task1)
    #send_close_request(task2)

    #send_filter_request(filter2)

    logging.info('Request sended.')