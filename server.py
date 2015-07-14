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
import time

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
        self.running = False
        self.num_actions = 0
        self.row_num = 0
        self.plant_num = 0
        self.pass_num = 0
        self.samples_num = 0
        self.at_plant = 0
        self.at_end = 0
        self.start_time = time.time()
        self.end_time = self.start_time + 5 * 60
        self.clock = self.end_time - self.start_time
        self.observed_plants = [] #TODO can add dummy vals here
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
        self.pretty_print("DECIDE", "Last Action: %s" % request['last_action'])
        self.pretty_print("DECIDE", "Result: %s" % request['result'])
        self.pretty_print("DECIDE", "Row: %d" % self.row_num)
        self.pretty_print("DECIDE", "Plants Observed: %d" % self.plant_num)
        self.pretty_print("DECIDE", "Blocks Collected: %d" % self.block_num)
        self.at_end = request['at_end']
        self.at_plant = request['at_plant']
        if self.running == False:
            action = 'wait'       
        elif (self.row_num < self.NUM_ROWS) and (self.plant_num < self.NUM_PLANTS):
            if self.num_actions == 0:
                action = 'begin'
            if request['last_action'] == 'begin':
                action = 'align'
                self.row_num = 1
            if request['last_action'] == 'align':
                action = 'seek'
            if request['last_action'] == 'seek':
                if request['at_end'] == 2:
                    action = 'turn'
                    self.row_num = self.row_num + 1
                if request['at_end'] == 1:
                    action = 'jump'
                elif request['at_plant'] != 0:
                    (color, height) = self.identify_plant(request['img'])
                    self.observed_plants.append((row, plant, color, height))
                    if self.collected_plants[color][height] == True: # check if plant type has been seen yet
                        action = 'seek'
                    else:
                        self.collected_plants[color][height] = True # if not, set to true and grab
                        action = 'grab'
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
        Returns:
            color : green, yellow, brown
            height: short, tall
            is_new : true/false
        """
        if self.VERBOSE: self.pretty_print("CV2", "Identifying plant phenotype ...")
        height = 'short'
        color = 'green'
        return color, height
        
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
        if self.VERBOSE: self.pretty_print('CHERRYPY', 'Listening for nodes ...')
        req = self.receive_request()
        action = self.decide_action(req)
        resp = self.send_response(action)
        event_id = self.store_event(req, resp)
    def refresh(self):
        """ Update the GUI """
        if self.VERBOSE: self.pretty_print('CHERRYPY', 'Updating GUI ...')
        robot_position = (self.row_num, self.at_plant, self.pass_num, self.at_end)
        self.gui.draw_board(self.observed_plants, robot_position)
        if self.running:
            self.clock = self.end_time - time.time()
        else:
            self.end_time = time.time() + self.clock         
        self.gui.update_gui(self.pass_num, self.row_num, self.plant_num, self.samples_num, self.clock)
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
        self.__init_statemachine__() # reset values
    def close(self, widget, window):
        try:
            gtk.main_quit()
        except Exception as e:
            self.pretty_print('GUI', 'Console server is still up (CTRL-C to exit)')
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
            # CONSTANTS
            self.GUI_LABEL_PASS = object.GUI_LABEL_PASS
            self.GUI_LABEL_PLANTS = object.GUI_LABEL_PLANTS
            self.GUI_LABEL_ROW = object.GUI_LABEL_ROW
            self.GUI_LABEL_SAMPLES = object.GUI_LABEL_SAMPLES
            self.GUI_LABEL_CLOCK = object.GUI_LABEL_CLOCK
            # Window
            self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.window.set_size_request(object.GUI_WINDOW_X, object.GUI_WINDOW_Y)
            self.window.connect("delete_event", object.close)
            self.window.set_border_width(10)
            self.window.show()
            self.hbox = gtk.HBox(False, 0)
            self.window.add(self.hbox)
            # Buttons
            self.hbox2 = gtk.HBox(False, 0)
            self.vbox = gtk.VBox(False, 0)
            self.vbox2 = gtk.VBox(False, 0)
            self.hbox.add(self.vbox)
            self.hbox2.show()
            self.vbox2.show()
            self.hbox3 = gtk.HBox(False, 0)
            self.vbox3 = gtk.VBox(False, 0)
            self.button_run = gtk.Button("Run") # Run Button
            self.button_run.connect("clicked", object.run)
            self.vbox3.pack_start(self.button_run, True, True, 0)
            self.button_run.show()
            self.button_stop = gtk.Button("Stop") # Stop Button
            self.button_stop.connect("clicked", object.stop)
            self.vbox3.pack_start(self.button_stop, True, True, 0)
            self.button_stop.show()
            self.button_reset = gtk.Button("Reset") # Reset Button
            self.button_reset.connect("clicked", object.reset)
            self.hbox3.pack_start(self.button_reset, True, True, 0)
            self.hbox3.add(self.vbox3)
            self.vbox2.add(self.hbox3)
            self.hbox3.show()
            self.vbox3.show()
            self.button_reset.show()
            self.vbox.add(self.vbox2)
            self.label_plants = gtk.Label()
            self.label_plants.set(object.GUI_LABEL_PLANTS)
            self.label_plants.show()		
            self.vbox2.add(self.label_plants)
            self.label_samples = gtk.Label()
            self.label_samples.set(object.GUI_LABEL_SAMPLES)
            self.label_samples.show()		
            self.vbox2.add(self.label_samples)
            self.label_row = gtk.Label()
            self.label_row.set(object.GUI_LABEL_ROW)
            self.label_row.show()
            self.vbox2.add(self.label_row)
            self.label_pass = gtk.Label()
            self.label_pass.set(object.GUI_LABEL_PASS)
            self.label_pass.show()		
            self.vbox2.add(self.label_pass)
            self.label_clock = gtk.Label()
            self.label_clock.set(object.GUI_LABEL_CLOCK)
            self.label_clock.show()		
            self.vbox2.add(self.label_clock)
            self.camera_bgr = cv2.imread('static/camera.jpg')
            self.camera_pix = gtk.gdk.pixbuf_new_from_array(self.camera_bgr, gtk.gdk.COLORSPACE_RGB, 8)
            self.camera_img = gtk.Image()
            self.camera_img.set_from_pixbuf(self.camera_pix)
            self.camera_img.show()
            self.vbox2.add(self.camera_img)
            self.vbox.show()
            # Board Image
            self.board_bgr = cv2.imread(object.GUI_IMAGE)
            self.board_pix = gtk.gdk.pixbuf_new_from_array(self.board_bgr, gtk.gdk.COLORSPACE_RGB, 8)
            self.board_img = gtk.Image()
            self.board_img.set_from_pixbuf(self.board_pix)
            self.board_img.show()
            self.hbox.add(self.board_img)
            self.hbox.show()
        except Exception as e:
            raise e
    
    ## Update GUI
    def update_gui(self, ps, r, pl, s, t):
        self.label_pass.set(self.GUI_LABEL_PASS % ps)
        self.label_row.set(self.GUI_LABEL_ROW % r)
        self.label_plants.set(self.GUI_LABEL_PLANTS % pl)
        self.label_samples.set(self.GUI_LABEL_SAMPLES % s)
        self.label_clock.set(self.GUI_LABEL_CLOCK % t)
        while gtk.events_pending():
            gtk.main_iteration_do(False)
    
    ## Draw Board
    def draw_board(self, observed_plants, robot_position, x=75, y=132, x_pad=154, y_pad=40, brown=(116,60,12), yellow=(219,199,6), green=(0,255,0), tall=7, short=2):
        try:
            (W,H,D) = self.board_bgr.shape
            (row_num, at_plant, pass_num, at_end) = robot_position

            # Robot
            if at_end == 0:
                if row_num == 0: # if at beginning
                    (center_x, center_y) = (W - 55, H - 55) ## 55, 55 is best
                elif at_plant != 0:  # if at plant
                    (center_x, center_y) = (W - (at_plant) * x - 77, H - (row_num - 1) * y - 110) ## 55, 55 is best
                elif pass_num == 2: # unaligned post-turn
                    (center_x, center_y) = (W - 470, H - (row_num - 1) * y - 110) ## 55, 55 is best
                elif row_num >= 1: # unaligned post-jump
                    (center_x, center_y) = (W - 130, H - (row_num - 1) * y - 110) ## 55, 55 is best
                else: # somewher after plant
                    (center_x, center_y) = (W - 470, H - (row_num - 1) * y - 110) ## 55, 55 is best
            elif at_end == 1:
                (center_x, center_y) = (W - 110, H - (row_num-1) * y - 110) # right side at row
            elif at_end == 2:
                (center_x, center_y) = (W - 500, H - (row_num-1) * y - 110) # left side at some row  
            else:
                (center_x, center_y) = (W - 55, H - 55)          
            top_left = ((center_x - 20), (center_y - 20))
            bottom_right = ((center_x + 20), (center_y + 20 ))
            cv2.rectangle(self.board_bgr, top_left, bottom_right, (255,0,0), thickness=5)

            # Plants
            if observed_plants == []: # at start
                pass
            else:
                for (r,p,c,h) in observed_plants:
                    if h == 'tall':
                        radius = tall
                    if h == 'short':
                        radius = short
                    if c == 'green':
                        color = green
                    if c == 'yellow':
                        color = yellow
                    if c == 'brown':
                        color = brown
                    center = ((W - (((p-1) * x) + x_pad)), (H - (((r-1) * y) + y_pad)))
                    cv2.circle(self.board_bgr, center, radius, color, thickness=15)
            self.board_pix = gtk.gdk.pixbuf_new_from_array(self.board_bgr, gtk.gdk.COLORSPACE_RGB, 8)
            self.board_img.set_from_pixbuf(self.board_pix)
        except Exception as e:
            print str(e)

    ## Draw Camera
    def draw_camera(self):
        try:
            (W,H,D) = self.camera_bgr.shape
        except Exception as e:
            print str(e)
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
