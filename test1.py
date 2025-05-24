import cv2
import numpy as np
import mediapipe as mp

mp_pose = mp.solutions.pose # loading the model (Pose)
pose = mp_pose.Pose() # initializes it
points = mp_pose.PoseLandmark # provides constants 
mp_drawing = mp.solutions.drawing_utils


cam = cv2.VideoCapture(0)

if not cam.isOpened():
    print("Cannot open camera")
    exit()

while True:
    ret, frame = cam.read()

    results = pose.process(frame)
    # print(results.pose_landmarks)
    mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

    cv2.imshow('window name', frame)

    if cv2.waitKey(1) == ord('q'):
        break
        
cam.release()
cv2.destroyAllWindows()