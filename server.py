#!/usr/bin/env python
"""

"""

# Libraries
import json
import ast
import cherrypy
import os
import sys
import numpy as np
from datetime import datetime, timedelta
from cherrypy.process.plugins import Monitor
from cherrypy import tools
from pymongo import MongoClient
from bson import json_util
import zmq
import cv2, cv

# Constants
try:
    CONFIG_PATH = sys.argv[1]
except Exception as err:
    print "NO CONFIGURATION FILE GIVEN"
    exit(1)

# CherryPy server
class Server:
    
    ## Initialize
    def __init__(self, config_path):
        
        # Configuration
        self.load_config(config_path)
        
        # Initializers
        self.init_zmq()
        self.init_tasks()
        self.init_mongo()

    ## Pretty Print
    def pretty_print(self, task, msg):
        date = datetime.strftime(datetime.now(), '%d/%b/%Y:%H:%M:%S')
        print('[%s] %s %s' % (date, task, msg))

    ## Load Configuration
    def load_config(self, config_path):
        self.pretty_print('CONFIG', 'Loading Config File')
        with open(config_path) as config:
            settings = json.loads(config.read())
            for key in settings:
                try:
                    getattr(self, key)
                except AttributeError as error:
                    setattr(self, key, settings[key])
    
    ## Initialize ZMQ
    def init_zmq(self):      
        self.pretty_print('ZMQ', 'Initializing ZMQ')
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(self.ZMQ_ADDR)
        except Exception as error:
            self.pretty_print('ZMQ', str(error))
    
    ## Initialize Tasks
    def init_tasks(self):
        self.pretty_print('CHERRYPY', 'Initializing Monitors')
        try:
            Monitor(cherrypy.engine, self.listen, frequency=self.CHERRYPY_LISTEN_INTERVAL).subscribe()
        except Exception as error:
            self.pretty_print('CHERRYPY', str(error))
    
    ## Initialize MongoDB
    def init_mongo(self):
        self.pretty_print('MONGO', 'Initializing Mongo')
        try:
            self.mongo_client = MongoClient(self.MONGO_ADDR, self.MONGO_PORT)
        except Exception as error:
            self.pretty_print('MONGO', 'Error: %s' % str(error))
       
    ## Receive Sample
    def receive_request(self):
        self.pretty_print('ZMQ', 'Receiving request')
        try:
            packet = self.socket.recv()
            request = json.loads(packet)
            return request
        except Exception as error:
            self.pretty_print('ZMQ', 'Error: %s' % str(error))
            
    ## Store Sample
    def store_event(self, request, response, collection_name=''):
        self.pretty_print('MONGO', 'Storing Sample')
        try:
            event['time'] = datetime.now()
            db_name = datetime.strftime(datetime.now(), self.MONGO_DB) # this is the mongo db it saves to
            mongo_db = self.mongo_client[db_name]
            collection = mongo_db[collection_name]
            event = {
                'request' : request,
                'response' : response
            } 
            event_id = collection.insert(event)
            self.pretty_print('MONGO', 'Sample ID: %s' % str(event_id))
            return str(event_id)
        except Exception as error:
            self.pretty_print('MONGO', 'Error: %s' % str(error))

    ## Send Response
    def send_response(self, action):
        self.pretty_print('ZMQ', 'Sending Response to Hive')
        try:
            response = {
                'type' : 'response',
                'action' : action
                }
            dump = json.dumps(response)
            self.socket.send(dump)
            self.pretty_print('ZMQ', str(response))
        except Exception as error:
            self.pretty_print('ZMQ', str(error))   
    
    def decide_action(self, request):
        """
        Below is the Pseudocode for how the decisions are made:

        start()
        for row in range(4):
            align()
            while not at_end:
                (at_end, at_plant, img) = seek
                if at_plant: 
                    (color, height, is_new) = identify_plant()
                    if is_new: 
                        grab()
            turn()
            align()
            while not at_end:
                (at_end, at_plant, img) = seek
                if at_plant: 
                    (color, height, is_new) = identify_plant()
                    if is_new: 
                        grab()
            jump()
        """
        
        if request['last_action'] == None:
            action = 'start'
            self.row = 0
            self.plant = 0
            self.collected_plants = {
                'green' : {
                    'short' : False,
                    'tall' : False                
                },
                'brown' : {
                    'short' : False,
                    'tall' : False                
                },
                'yellow' : {
                    'short' : False,
                    'tall' : False
                }
            }
        elif (self.row < self.NUM_ROWS) and (self.plant < self.NUM_PLANTS):
            if request['last_action'] == 'start':
                action = 'align'
            if request['last_action'] == 'align':
                action = 'seek'
            if request['last_action'] == 'seek':
                if request['at_end']:
                    self.row = self.row + 1
                    if np.mod(self.row, 2) == 1: 
                        action = 'turn' # if the row count is odd --> turn
                    else:
                        action = 'jump' # if the row count is even --> jump
                elif request['at_plant']:
                    (color, height, is_new) = self.identify_plant(request['img'])
                    if is_new:
                        action = 'grab'
                    else:
                        action = 'seek'
            if request['last_action'] == 'grab':
                action = 'seek'
            if request['last_action'] == 'jump':
                action = 'align'
        else:
            action = 'stop'
        return action
        

    ## Identify Plant
    def identify_plant(self, bgr):
        """
        color : green, yellow, brown
        height: short, tall
        is_new : true/false
        """
        height = 'short'
        color = 'green'
        if self.collected_plants[color][height] == True:
            is_new = False
        else:
            is_new = True
            self.collected_plants[color][height] = True # set to true
        return color, height, is_new
        
    ## Listen for Next Sample
    def listen(self):
        self.pretty_print('CHERRYPY', 'Listening for nodes')
        req = self.receive_request()
        resp = self.decide_action(req)
        event_id = self.store_event(req, resp)
        self.send_response(event_id)
    
    """
    Handler Functions
    """
    ## Render Index
    @cherrypy.expose
    def index(self):
        html = open('static/index.html').read()
        return html
    
    ## Handle Posts
    """
    This function is basically the API
    """
    @cherrypy.expose
    def default(self, *args, **kwargs):
        try:
            pass
        except Exception as err:
            self.pretty_print('ERROR', str(err))
        return None

# Main
if __name__ == '__main__':
    server = Server(CONFIG_PATH)
    cherrypy.server.socket_host = server.CHERRYPY_ADDR
    cherrypy.server.socket_port = server.CHERRYPY_PORT
    currdir = os.path.dirname(os.path.abspath(__file__))
    conf = {
        '/': {'tools.staticdir.on':True, 'tools.staticdir.dir':os.path.join(currdir,server.CHERRYPY_STATIC_DIR)},
        '/data': {'tools.staticdir.on':True, 'tools.staticdir.dir':os.path.join(currdir,server.CHERRYPY_DATA_DIR)}, # NEED the '/' before the folder name
    }
    cherrypy.quickstart(server, '/', config=conf)
