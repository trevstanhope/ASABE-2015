import cv2, cv
import numpy as np


FRAME_WIDTH = 320
FRAME_HEIGHT = 240
SATURATION = 1.0
BRIGHTNESS = 0.5
CONTRAST = 0.5
NUM_FLUSH = 30
FILENAME = 'testmask.jpg'

#cam = cv2.VideoCapture(0)
#cam.set(cv.CV_CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
#cam.set(cv.CV_CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
#cam.set(cv.CV_CAP_PROP_SATURATION, SATURATION)
#cam.set(cv.CV_CAP_PROP_BRIGHTNESS, BRIGHTNESS)
#cam.set(cv.CV_CAP_PROP_CONTRAST, CONTRAST)

#for i in range(NUM_FLUSH):
#    (s, bgr) = cam.read()
#if s:
#    bgr = np.rot90(bgr, 3)
#    cv2.imshow('', bgr)
#    cv2.waitKey(0)
#    cv2.imwrite(FILENAME, bgr)

# Load image
bgr=cv2.imread('test5.jpg')
bgr=cv2.medianBlur(bgr,5)

## green
greenlow=np.array([45,0,0])
greenhigh=np.array([75,255,255])

hsv = cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)
mask = cv2.inRange(hsv,greenlow,greenhigh)
kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3))
kernel2=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2,2))


opening = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)

ret,thresh = cv2.threshold(closing,127,255,0)
contours, hierarchy = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)

# Find the index of the largest contour
areas = [cv2.contourArea(c) for c in contours]
max_index = np.argmax(areas)
cnt=contours[max_index]

x,y,w,h = cv2.boundingRect(cnt)
cv2.rectangle(bgr,(x,y),(x+w,y+h),(0,255,0),2)
cv2.imshow("Show",bgr)
cv2.waitKey()
cv2.destroyAllWindows()

##yellow
yellowlow=np.array([15,0,0])
yellowhigh=np.array([45,255,255])

hsv = cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)
mask = cv2.inRange(hsv,yellowlow,yellowhigh)
kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3))
kernel2=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2,2))


opening = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)

ret,thresh = cv2.threshold(closing,127,255,0)
contours, hierarchy = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)

# Find the index of the largest contour
areas = [cv2.contourArea(c) for c in contours]
max_index = np.argmax(areas)
cnt=contours[max_index]

x,y,w,h = cv2.boundingRect(cnt)
cv2.rectangle(bgr,(x,y),(x+w,y+h),(0,255,255),2)
cv2.imshow("Show",bgr)
cv2.waitKey()
cv2.destroyAllWindows()

## brown
brownlow=np.array([0,0,0])
brownhigh=np.array([20,255,102])

brownlow1=np.array([150,0,0])
brownhigh1=np.array([180,255,102])

hsv = cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)
mask1 = cv2.inRange(hsv,brownlow,brownhigh)
mask2 = cv2.inRange(hsv,brownlow1,brownhigh1)
mask3= mask1+mask2
kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3))
kernel2=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2,2))


opening = cv2.morphologyEx(mask3, cv2.MORPH_OPEN, kernel)
closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)

ret,thresh = cv2.threshold(closing,127,255,0)
contours, hierarchy = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)

# Find the index of the largest contour
areas = [cv2.contourArea(c) for c in contours]
max_index = np.argmax(areas)
cnt=contours[max_index]

x,y,w,h = cv2.boundingRect(cnt)
cv2.rectangle(bgr,(x,y),(x+w,y+h),(0,87,115),2)
cv2.imshow("Show",bgr)
cv2.waitKey()
cv2.destroyAllWindows()

