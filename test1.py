import cv2
import numpy as np
import mediapipe as mp

cam = cv2.VideoCapture(0)

if not cam.isOpened():
    print("Cannot open camera")
    exit()

while True:
    ret, frame = cam.read()
    cv2.imshow('window name', frame)

    if cv2.waitkey(1) == orq('q'):
        break
        
cam.release()
cv2.destroyAllWindows()