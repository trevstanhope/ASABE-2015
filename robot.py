#!/usr/bin/env python
"""
"""

__author__ = "Trevor Stanhope"
__version__ = "0.1"

# Libraries
import zmq
import ast
import json
import os
import sys
import numpy as np
from datetime import datetime
from serial import Serial, SerialException
import cv2

# Constants
try:
    CONFIG_PATH = sys.argv[1]
except Exception as err:
    exit()

# Robot
class Robot:

    ## Initialize
    def __init__(self, config_path):
        
        # Configuration
        self.load_config(config_path)

        # Initializers
        self.init_zmq()
        self.init_arduino()
        self.init_cam()
    
    ## Pretty Print
    def pretty_print(self, task, msg):
        date = datetime.strftime(datetime.now(), '%d/%b/%Y:%H:%M:%S')
        print('[%s] %s\t%s' % (date, task, msg))

    ## Load Config File
    def load_config(self, config_path):
        with open(config_path) as config_file:
            settings = json.loads(config_file.read())
            for key in settings:
                try:
                    getattr(self, key)
                except AttributeError as e:
                    setattr(self, key, settings[key])
                        
    ## Initialize ZMQ messenger
    def init_zmq(self):
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(self.ZMQ_ADDR)
            self.poller = zmq.Poller()
            self.poller.register(self.socket, zmq.POLLIN)
        except Exception as e:
            self.pretty_print('ZMQ', 'Error: %s' % str(e))
            exit(1)
    
    ## Initialize Arduino
    def init_arduino(self):
        try:
            self.arduino = Serial(self.ARDUINO_DEV, self.ARDUINO_BAUD, timeout=self.ARDUINO_TIMEOUT)
        except Exception as e:
            self.pretty_print('CTRL', 'Error: %s' % str(e))
            exit(1)
    
    ## Initialize camera
    def init_cam(self):
        try:
            self.camera = cv2.VideoCapture(self.CAMERA_INDEX)
        except Exception as e:
            self.pretty_print('CAM', 'Error: %s' % str(e))
            exit(1)

    ## Capture image
    def capture_image(self, n_flush=30):
        for i in range(n_flush):
            (s, bgr) = self.camera.read()
        return bgr
 
   ## Send request to server
    def request_action(self):
        self.pretty_print('ZMQ', 'Pushing request to server')
        try:
            request = {
                'type' : 'request',
                'last_action' : self.last_action
            }
            dump = json.dumps(request)
            self.socket.send(dump)
            socks = dict(self.poller.poll(self.ZMQ_TIMEOUT))
            if socks:
                if socks.get(self.socket) == zmq.POLLIN:
                    dump = self.socket.recv(zmq.NOBLOCK)
                    response = json.loads(dump)
                    self.pretty_print('ZMQ', str(response))
                    action = request['action']
                    return action
                else:
                    self.pretty_print('ZMQ', 'Error: Poll Timeout')
            else:
                self.pretty_print('ZMQ', 'Error: Socket Timeout')
        except Exception as e:
            raise e

    ## Exectute robotic action
    def execute_action(self, command):
        self.pretty_print('CTRL', 'Interacting with controller ...')
        try:
            self.arduino.write(command + '\n') # send command
            while self.arduino.readline() == '': 
                pass # wait for completion
            string = self.arduino.readline()
            status = ast.literal_eval(string) # parse status response
            return status
        except Exception as e:           
            self.pretty_print('CTRL', 'Error: %s' % str(e))

    ## Run
    def run(self):
        self.last_action = None
        self.at_plant = False
        self.at_end = False
        while True:
            try:
                action = self.request_action()
                if action:
                    status = self.execute_action(action) #!TODO need to handle different responses
                    bgr = self.capture_image()
            except Exception as e:
                self.pretty_print('RUN', 'Error: %s' % str(e))
                break

if __name__ == '__main__':
    robot = Robot(CONFIG_PATH)
    robot.run()
