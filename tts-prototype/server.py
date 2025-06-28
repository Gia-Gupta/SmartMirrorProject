import asyncio
import websockets
import base64
import cv2
import numpy as np
import mediapipe as mp
import json
import logging

# Set up MediaPipe pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_drawing = mp.solutions.drawing_utils

# Feedback function
def generate_feedback(landmarks):
    feedback = []
    try:
        left_elbow_y = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y
        left_wrist_y = landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y
        left_shoulder_y = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y

        if left_elbow_y < left_shoulder_y - 0.05:
            feedback.append("Raise your elbow slightly.")
        elif left_elbow_y > left_shoulder_y + 0.05:
            feedback.append("Lower your elbow slightly.")

        if left_wrist_y > left_elbow_y + 0.05:
            feedback.append("Lower your wrist.")
        elif left_wrist_y < left_elbow_y - 0.05:
            feedback.append("Raise your wrist.")

        if not feedback:
            return "Good alignment."
        return " ".join(feedback)
    except:
        return "No pose detected."

# Decode image
def decode_frame(base64_data):
    jpg_original = base64.b64decode(base64_data)
    jpg_as_np = np.frombuffer(jpg_original, dtype=np.uint8)
    return cv2.imdecode(jpg_as_np, flags=1)

# Process image frame
def process_frame(image):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = pose.process(image_rgb)
    feedback = "No pose detected."
    if results.pose_landmarks:
        mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        feedback = generate_feedback(results.pose_landmarks.landmark)
    return image, feedback

# WebSocket handler
async def handler(websocket):
    async for message in websocket:
        data = json.loads(message)
        if "image" in data:
            frame = decode_frame(data["image"])
            processed_frame, feedback = process_frame(frame)
            _, buffer = cv2.imencode(".jpg", processed_frame)
            jpg_as_text = base64.b64encode(buffer).decode("utf-8")
            await websocket.send(json.dumps({"image": jpg_as_text, "feedback": feedback}))

# Main loop
async def main():
    print("WebSocket server running on ws://0.0.0.0:8765")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())


