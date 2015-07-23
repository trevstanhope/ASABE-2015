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
from random import randint

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
            db_name = datetime.strftime(datetime.now(), self.MONGO_DB) # db to save to
            mongo_db = self.mongo_client[db_name]
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
        self.bgr = cv2.imread(self.GUI_CAMERA_IMAGE)
        self.running = False
        self.row_num = 0
        self.plant_num = 0
        self.pass_num = 0
        self.samples_num = 0
        self.at_plant = 0
        self.at_end = 0
        self.start_time = time.time()
        self.end_time = self.start_time + self.RUN_TIME
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
        self.pretty_print("DECIDE", "Last Action: %s" % request['last_action'])
        self.pretty_print("DECIDE", "Result: %s" % request['result'])
        self.pretty_print("DECIDE", "Row: %d" % self.row_num)
        self.pretty_print("DECIDE", "Plants Observed: %d" % self.plant_num)
        self.pretty_print("DECIDE", "Blocks Collected: %d" % self.samples_num)
        self.at_end = request['at_end']
        self.pass_num = request['pass_num']
        self.at_plant = request['at_plant']
        self.pretty_print("DECIDE", "At End: %d" % self.at_end)
        self.pretty_print("DECIDE", "At Plant: %d" % self.at_plant)
        self.pretty_print("DECIDE", "Pass Num: %d" % self.pass_num)
        self.bgr = np.array(request['bgr'], np.uint8)
        ## If paused
        if self.running == False:
            if request['last_action'] == 'clear':
                action = 'wait'
            else:
                action = 'clear'
        ## If clock running out
        elif self.clock <= self.GIVE_UP_TIME: # if too little time
            action = 'finish'
        ## If searching for plants 
        elif (self.row_num < self.NUM_ROWS) or (self.plant_num < self.NUM_PLANTS):
            if self.row_num == 0:
                action = 'begin' # begin if first action
                self.row_num = 1
            elif request['last_action'] == 'begin':
                action = 'align' # align if jumped to beginning
            elif request['last_action'] == 'align':
                if True:
                    action = 'seek' # seek to end/plant if aligned at end of row to search
                else: 
                    action = 'end' # seek blindly if aligned at end of doubled row
            elif request['last_action'] == 'seek':
                if request['at_end'] == 2:
                    action = 'turn' # turn if at far end
                if request['at_end'] == 1:
                    action = 'jump' # jump if at near end
                    self.row_num = self.row_num + 1
                elif request['at_plant'] != 0:
                    (color, height, bgr2) = self.identify_plant(bgr)
                    self.pretty_print('DECIDE', 'Color: %s' % color)
                    self.pretty_print('DECIDE', 'Height: %s' % height)
                    self.bgr = bgr2
                    if self.pass_num == 1:
                        row = self.row_num
                        plant = self.at_plant
                    elif self.pass_num == 2:
                        row = self.row_num + 1
                        plant = 6 - self.at_plant # run plants backward
                    s = self.add_plant(row, plant, color, height)
                    if s: self.plant_num += 1
                    if self.collected_plants[color][height] == True: # check if plant type has been seen yet
                        action = 'seek'
                    else:
                        self.collected_plants[color][height] = True # if not, set to true and grab
                        action = 'grab'
                        self.samples_num += 1
            elif request['last_action'] == 'turn':
                action = 'align'
            elif request['last_action'] == 'grab':
                action = 'seek'
            elif request['last_action'] == 'jump':
                action = 'align'
            else:
                action = 'wait'
        ## If at last row or reached 20 plants
        else:
            if (request['last_action'] == 'seek') and (self.at_end != 1) and (self.pass_num == 2):
                action = 'end' # if part-way along final row (i.e. not at end #1)
            elif (request['last_action'] == 'seek') and (self.at_end == 1) and (self.pass_num == 2):
                action = 'finish' # if part-way along final row (i.e. not at end #1)
            elif request['last_action'] == 'end':
                action = 'finish' # if at end of final row
            else:
                action = 'finish' # if last plant was row 4, plant 5 (i.e. 20 plants in 20 positions)
        return action
    def identify_plant(self, bgr):
        """
        Returns:
            color : green, yellow, brown
            height: short, tall
            is_new : true/false
        """
        if self.VERBOSE: self.pretty_print("CV2", "Identifying plant phenotype ...")
        try:
            detected_areas = [(0,0,0,0,0)] * 3
            bgr = cv2.medianBlur(bgr, 5)
            hsv = cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)
            greenlow = np.array([30,30,0]) 
            greenhigh = np.array([100,255,255])
            yellowlow = np.array([0,128,0])
            yellowhigh = np.array([45, 255, 255])
            brownlow = np.array([0,0,0])
            brownhigh = np.array([20,255,102])
            brownlow1 = np.array([150,0,0])
            brownhigh1 = np.array([180,255,102])
            green_mask = cv2.inRange(hsv, greenlow, greenhigh)
            yellow_mask = cv2.inRange(hsv, yellowlow, yellowhigh)
            brown_mask1 = cv2.inRange(hsv, brownlow, brownhigh)
            brown_mask2 = cv2.inRange(hsv, brownlow1, brownhigh1)
            brown_mask = brown_mask1 + brown_mask2
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3))
            masks = [green_mask, yellow_mask, brown_mask]
            for i in range(len(masks)):
                m = masks[i]
                opening = cv2.morphologyEx(m, cv2.MORPH_OPEN, kernel)
                closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
                ret,thresh = cv2.threshold(closing,127,255,0)
                contours, hierarchy = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
                areas = [cv2.contourArea(c) for c in contours]
                max_index = np.argmax(areas) # Find the index of the largest contour
                cnt = contours[max_index]
                x,y,w,h = cv2.boundingRect(cnt)
                detected_areas[i] = (x, y, w, h)
            areas = [w*h for (x, y, w, h) in detected_areas]
            max_area = max(areas)
            i = np.argmax(areas)
            (x, y, w, h) = detected_areas[i]
            if i == 0:
                c = (0,255,0)
                color = 'green'
            elif i == 1:
                c = (0,255,255)
                color = 'yellow'
            elif i == 2:
                c = (0,87,115)
                color = 'brown'
            else:
                exit(1)
            if h > self.CAMERA_TALL_THRESHOLD:
                height = 'tall'
            else:
                height = 'short'
            cv2.rectangle(bgr,(x,y),(x+w,y+h), c, 2) # Draw the rectangle
        except Exception as e:
            self.pretty_print("CV", "Error: %s" % str(e))
            colors = ['green', 'yellow', 'brown']
            heights = ['tall', 'short']
            i = randint(0,2)
            j = randint(0,1)
            color = colors[i]
            height = heights[j]
        return color, height, bgr
    def add_plant(self, row, plant, color, height):
        for p in self.observed_plants:
            if p == (row, plant, color, height):
                return False
        self.observed_plants.append((row, plant, color, height))
        return True
 
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
        self.bgr = np.array(req['bgr'], np.uint8)
        action = self.decide_action(req)
        resp = self.send_response(action)
        if self.MONGO_ENABLED: event_id = self.store_event(req, resp)
    def refresh(self):
        """ Update the GUI """
        if self.VERBOSE: self.pretty_print('CHERRYPY', 'Updating GUI ...')
        robot_position = (self.row_num, self.at_plant, self.pass_num, self.at_end)
        self.gui.draw_camera(self.bgr)
        self.gui.draw_board(self.observed_plants, robot_position)
        if self.running:
            self.clock = self.end_time - time.time()
            if self.clock <= 0:
                self.running = False
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
            self.GUI_BOARD_IMAGE = object.GUI_BOARD_IMAGE
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
            self.camera_bgr = cv2.imread(object.GUI_CAMERA_IMAGE)
            self.camera_pix = gtk.gdk.pixbuf_new_from_array(self.camera_bgr, gtk.gdk.COLORSPACE_RGB, 8)
            self.camera_img = gtk.Image()
            self.camera_img.set_from_pixbuf(self.camera_pix)
            self.camera_img.show()
            self.vbox2.add(self.camera_img)
            self.vbox.show()
            # Board Image
            self.board_bgr = cv2.imread(object.GUI_BOARD_IMAGE)
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
            board_bgr = cv2.imread(self.GUI_BOARD_IMAGE)
            (W,H,D) = board_bgr.shape
            (row_num, at_plant, pass_num, at_end) = robot_position

            # Robot
            if at_end == 0:
                if row_num == 0: # if at beginning
                    (center_x, center_y) = (W - 55, H - 55) ## 55, 55 is best
                elif at_plant != 0:  # if at plant
                    if pass_num == 1:
                        (center_x, center_y) = (W - (at_plant) * x - 77, H - (row_num - 1) * y - 110)
                    elif pass_num == 2:
                        (center_x, center_y) = (W - (6 - at_plant) * x - 77, H - (row_num - 1) * y - 110)
                elif pass_num == 2: # unaligned post-turn
                    (center_x, center_y) = (W - 470, H - (row_num - 1) * y - 110) 
                elif row_num >= 1: # unaligned post-jump
                    (center_x, center_y) = (W - 130, H - (row_num - 1) * y - 110) 
                elif row_num > 4: # to finish
                    (center_x, center_y) = (W - 130, H - (row_num - 1) * y - 110)
                else: # somewhere after plant
                    (center_x, center_y) = (W - 470, H - (row_num - 1) * y - 110)
            elif at_end == 1:
                (center_x, center_y) = (W - 110, H - (row_num-1) * y - 110) # right side at row
            elif at_end == 2:
                (center_x, center_y) = (W - 500, H - (row_num-1) * y - 110) # left side at some row  
            else:
                (center_x, center_y) = (W - 55, H - 55)          
            top_left = ((center_x - 20), (center_y - 20))
            bottom_right = ((center_x + 20), (center_y + 20 ))
            cv2.rectangle(board_bgr, top_left, bottom_right, (255,0,0), thickness=5)

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
                    cv2.circle(board_bgr, center, radius, color, thickness=15)
            self.board_pix = gtk.gdk.pixbuf_new_from_array(board_bgr, gtk.gdk.COLORSPACE_RGB, 8)
            self.board_img.set_from_pixbuf(self.board_pix)
        except Exception as e:
            print str(e)

    ## Draw Camera
    def draw_camera(self, bgr):
        try:
            self.camera_bgr = bgr
            rgb = cv2.cvtColor(self.camera_bgr, cv2.COLOR_BGR2RGB)
            self.camera_pix = gtk.gdk.pixbuf_new_from_array(rgb, gtk.gdk.COLORSPACE_RGB, 8)
            self.camera_img.set_from_pixbuf(self.camera_pix)
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
