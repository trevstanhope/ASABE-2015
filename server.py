#!/usr/bin/env python
"""
McGill University
ASABE 2015
"""

__author__ = 'Trevor Stanhope'
__version__ = '0.2b'

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
import pygtk
pygtk.require('2.0')
import gtk
import matplotlib.pyplot as mpl

# Configuration
try:
    CONFIG_PATH = sys.argv[1]
except Exception as err:
    print "NO CONFIGURATION FILE GIVEN"
    exit(1)

# CherryPy3 server
class Server:
    
    ## Initialize
    def __init__(self, config_path):
        
        # Configuration
        self.load_config(config_path)
        
        # Initializers
        self.__init_zmq__()
        self.__init_tasks__()
        self.__init_mongo__()
        self.__init_statemachine__()
        self.__init_gui__()

    ## Useful Functions
    def pretty_print(self, task, msg):
        """ Pretty Print """ 
        date = datetime.strftime(datetime.now(), '%d/%b/%Y:%H:%M:%S')
        print('[%s] %s\t%s' % (date, task, msg))
    def load_config(self, config_path):
        """ Load Configuration """
        self.pretty_print('CONFIG', 'Loading Config File')
        with open(config_path) as config:
            settings = json.loads(config.read())
            for key in settings:
                try:
                    getattr(self, key)
                except AttributeError as error:
                    setattr(self, key, settings[key])
         
    ## Mongo Functions
    def __init_mongo__(self):
        if self.VERBOSE: self.pretty_print('MONGO', 'Initializing Mongo')
        try:
            self.mongo_client = MongoClient(self.MONGO_ADDR, self.MONGO_PORT)
        except Exception as error:
            self.pretty_print('MONGO', 'Error: %s' % str(error))
    def store_event(self, request, response, collection_name=''):
        if self.VERBOSE: self.pretty_print('MONGO', 'Storing Sample')
        try:
            timestamp = datetime.strftime(datetime.now(), self.TIME_FORMAT)
            collection_name = datetime.strftime(datetime.now(), self.MONGO_COL) # db to save to
            mongo_db = self.mongo_client[self.MONGO_DB]
            collection = mongo_db[collection_name]
            event = {
                'request' : request,
                'response' : response,
                'time' : timestamp
            } 
            event_id = collection.insert(event)
            self.pretty_print('MONGO', 'Sample ID: %s' % str(event_id))
            return str(event_id)
        except Exception as error:
            self.pretty_print('MONGO', 'Error: %s' % str(error))
       
    ## ZMQ Functions
    def __init_zmq__(self):      
        if self.VERBOSE: self.pretty_print('ZMQ', 'Initializing ZMQ')
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(self.ZMQ_HOST)
        except Exception as error:
            self.pretty_print('ZMQ', str(error))
    def receive_request(self):
        if self.VERBOSE: self.pretty_print('ZMQ', 'Receiving request')
        try:
            packet = self.socket.recv()
            request = json.loads(packet)
            return request
        except Exception as error:
            self.pretty_print('ZMQ', 'Error: %s' % str(error))
    def send_response(self, action):
        """ Send Response """
        if self.VERBOSE: self.pretty_print('ZMQ', 'Sending Response to Robot')
        try:
            response = {
                'type' : 'response',
                'action' : action
                }
            dump = json.dumps(response)
            self.socket.send(dump)
            self.pretty_print('ZMQ', 'Response: %s' % str(response))
            return response
        except Exception as error:
            self.pretty_print('ZMQ', str(error))   
    
    ## Statemachine Functions
    def __init_statemachine__(self):
        self.num_actions = 0
        self.row_num = 0
        self.plant_num = 0
        self.block_num = 0
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
                    if//************** is_new: 
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
        last_action = request['last_action']
        self.pretty_print("DECIDE", "Last Action: %s" % last_action)
        self.pretty_print("DECIDE", "Row: %d" % self.row_num)
        self.pretty_print("DECIDE", "Plants Observed: %d" % self.plant_num)
        self.pretty_print("DECIDE", "Blocks Collected: %d" % self.block_num)
        if self.running == False:
            action = 'wait'       
        elif (self.row_num < self.NUM_ROWS) and (self.plant_num < self.NUM_PLANTS):
            if self.num_actions == 0:
                action = 'begin'           
            if request['last_action'] == 'begin':
                action = 'align'
            if request['last_action'] == 'align':
                action = 'seek'
            if request['last_action'] == 'seek':
                if request['at_end'] == 2:
                    action = 'turn'
                    self.row_num = self.row_num + 1
                if request['at_end'] == 1:
                    action = 'jump'
                elif request['at_plant'] != 0:
                    (color, height, is_new) = self.identify_plant(request['img'])
                    if is_new:
                        action = 'grab'
                    else:
                        action = 'seek'
            if request['last_action'] == 'turn':
                action = 'align'
            if request['last_action'] == 'grab':
                action = 'seek'
            if request['last_action'] == 'jump':
                action = 'align'
            self.num_actions = self.num_actions + 1
        else:
            action = 'finish'
        return action
    def identify_plant(self, bgr):
        """
        color : green, yellow, brown
        height: short, tall
        is_new : true/false
        """
        if self.VERBOSE: self.pretty_print("CV2", "Identifying plant phenotype ...")
        height = 'short'
        color = 'green'
        if self.collected_plants[color][height] == True:
            is_new = False
        else:
            is_new = True
            self.collected_plants[color][height] = True # set to true
        return color, height, is_new
        
    ## CherryPy Functions
    def __init_tasks__(self):
        if self.VERBOSE: self.pretty_print('CHERRYPY', 'Initializing Monitors')
        try:
            Monitor(cherrypy.engine, self.listen, frequency=self.CHERRYPY_LISTEN_INTERVAL).subscribe()
            Monitor(cherrypy.engine, self.refresh, frequency=self.CHERRYPY_REFRESH_INTERVAL).subscribe()
        except Exception as error:
            self.pretty_print('CHERRYPY', str(error))
    def listen(self):
        """ Listen for Next Sample """
        self.gui.update_gui()
        if self.VERBOSE: self.pretty_print('CHERRYPY', 'Listening for nodes ...')
        req = self.receive_request()
        action = self.decide_action(req)
        resp = self.send_response(action)
        event_id = self.store_event(req, resp)
    def refresh(self):
        """ Update the GUI """
        if self.VERBOSE: self.pretty_print('CHERRYPY', 'Updating GUI ...')
        self.gui.update_gui()
        self.gui.show_board()
    @cherrypy.expose
    def index(self):
        """ Render index page """
        html = open('static/index.html').read()
        return html
    @cherrypy.expose
    def default(self, *args, **kwargs):
        """
        Handle Posts -
        This function is basically the RESTful API
        """
        try:

            pass
        except Exception as err:
            self.pretty_print('ERROR', str(err))
        return None

    ## GUI Functions
    def __init_gui__(self):
        if self.VERBOSE: self.pretty_print('GUI', 'Initializing GUI')
        try:
            self.gui = GUI(self)
            self.running= False
        except Exception as error:
            self.pretty_print('GUI', str(error))
    def run(self, object):
        self.pretty_print("GUI", "Running session ...")
        self.running = True
    def stop(self, object):
        self.pretty_print("GUI", "Halting session ...")
        self.running = False
    def reset(self, object):
        self.pretty_print("GUI", "Resetting to start ...")
        pass
    def shutdown(self, object):
        self.pretty_print("GUI", "Executing reboot ...")
        pass
    def close(self, widget, window):
        try:
            gtk.main_quit()
        except Exception as e:
            self.pretty_print('GUI', 'Console server is still up (CTRL-D to exit)')
# Display
class GUI(object):

    ## Initialize Display
    def __init__(self, object):
        """
        Requires super-object to have several handler functions:
            - shutdown()
            - close()
            - reset()
            - run()
        """
        try:
            # Window
            self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.window.set_size_request(object.GUI_WINDOW_X, object.GUI_WINDOW_Y)
            self.window.connect("delete_event", object.close)
            self.window.set_border_width(10)
            self.window.show()
            self.vbox = gtk.HBox(False, 0)
            self.window.add(self.vbox)
            self.hbox = gtk.VBox(False, 0)
            self.hbox.show()
            # Run Button
            self.button_run = gtk.Button("Run")
            self.button_run.connect("clicked", object.run)
            self.hbox.pack_start(self.button_run, True, True, 0)
            self.button_run.show()
            # Stop Button
            self.button_stop = gtk.Button("Stop")
            self.button_stop.connect("clicked", object.stop)
            self.hbox.pack_start(self.button_stop, True, True, 0)
            self.button_stop.show()
            # Reset Button
            self.button_reset = gtk.Button("Reset")
            self.button_reset.connect("clicked", object.reset)
            self.hbox.pack_start(self.button_reset, True, True, 0)
            self.button_reset.show()
            # Shutdown Button
            self.button_shutdown = gtk.Button("Shutdown")
            self.button_shutdown.connect("clicked", object.shutdown)
            self.hbox.pack_start(self.button_shutdown, True, True, 0)
            self.button_shutdown.show()
            self.vbox.add(self.hbox)
            # Board Image
            self.bgr = cv2.imread(object.GUI_IMAGE)
            self.pix = gtk.gdk.pixbuf_new_from_array(self.bgr, gtk.gdk.COLORSPACE_RGB, 8)
            self.image = gtk.Image()
            self.image.set_from_pixbuf(self.pix)
            self.image.show()
            self.vbox.add(self.image)
            self.vbox.show()
        except Exception as e:
            raise e
    
    ## Update GUI
    def update_gui(self):
        while gtk.events_pending():
            gtk.main_iteration_do(False)
    
    ## Show Board
    def show_board(self, img_path='static/board.jpg'):
        try:
            board = cv2.imread(img_path)
            (w,h,d) = board.shape
            #!TODO draw board
        except Exception as e:
            raise e

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
