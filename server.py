import asyncio
import websockets
import logging
import base64
import numpy as np
import mediapipe as mp
import cv2 # Import OpenCV
import time
import json

# pose duration tracking
pose_start_time = None
POSE_HOLD_DURATION = 3  # seconds
pose_held = False

# configure mediapipe for pose detection
mp_pose = mp.solutions.pose # load model (Pose solution)
pose = mp_pose.Pose() # Initialize the pose model with default parameters
points = mp_pose.PoseLandmark  # provides constants for each of the 33 landmarks
mp_drawing = mp.solutions.drawing_utils # enable drawing utilities for visualization

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger(__name__)

connected_clients = set()

        # Simplified pose check function
def is_arms_outstretched(pose_landmarks):
    if not pose_landmarks:
        return False

    # Example check: left shoulder, elbow, wrist roughly same y-level
    left_shoulder = pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER]
    left_elbow = pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_ELBOW]
    left_wrist = pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST]
    # right_shoulder = pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER]
    # right_elbow = pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_ELBOW]
    # right_wrist = pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST]
    # logger.info(f"Left Shoulder: {left_shoulder}, Left Elbow: {left_elbow}, Left Wrist: {left_wrist}")
    # logger.info(f"Right Shoulder: {right_shoulder}, Right Elbow: {right_elbow}, Right Wrist: {right_wrist}")
    y1, y2, y3 = left_shoulder.y, left_elbow.y, left_wrist.y
    # y4, y5, y6 = right_shoulder.y, right_elbow.y, right_wrist.y
    tolerance = 0.2
    logger.info(f"Y values: {y1}, {y2}, {y3}")
    return (abs(y1 - y2) < tolerance and abs(y2 - y3) < tolerance)
    # return (abs(y1 - y2) < tolerance and abs(y2 - y3) < tolerance) and (abs(y4 - y5) < tolerance and abs(y5 - y6) < tolerance)


def data_url_to_cv2_img(data_url_string):
    """
    Converts a data URL string (expected to be jpeg base64) to an OpenCV image.
    Returns None if conversion fails.
    """
    try:
        # 1. Check if it's a data URL and find the base64 part
        if not data_url_string.startswith('data:image/jpeg;base64,'):
            logger.warning("Received data is not a JPEG data URL.")
            return None
        
        img_data_base64 = data_url_string.split(',', 1)[1]
        
        # 2. Decode Base64 to binary data
        img_data_binary = base64.b64decode(img_data_base64)
        
        # 3. Convert binary data to NumPy array
        np_arr = np.frombuffer(img_data_binary, np.uint8)
        
        # 4. Decode image data with OpenCV
        img_cv2 = cv2.imdecode(np_arr, cv2.IMREAD_COLOR) # Or cv2.IMREAD_UNCHANGED
        
        if img_cv2 is None:
            logger.error("cv2.imdecode failed. The image data might be corrupt or not a valid JPEG.")
            return None
            
        return img_cv2
    except Exception as e:
        logger.error(f"Error converting data URL to OpenCV image: {e}", exc_info=True)
        return None

def cv2_img_to_data_url(cv2_img, image_format='.jpg', quality=70):
    """
    Converts an OpenCV image to a JPEG data URL string.
    Returns None if conversion fails.
    """
    try:
        # Encode image to JPEG format in memory
        # For JPEG, quality is an int from 0 to 100 (higher is better quality, larger file)
        is_success, im_buf_arr = cv2.imencode(image_format, cv2_img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        
        if not is_success:
            logger.error("cv2.imencode failed.")
            return None
            
        # Convert buffer to base64
        byte_im = im_buf_arr.tobytes()
        img_data_base64 = base64.b64encode(byte_im).decode('utf-8')
        
        # Construct data URL
        mime_type = "image/jpeg" if image_format.lower() in ['.jpg', '.jpeg'] else f"image/{image_format.lower().lstrip('.')}"
        data_url_string = f"data:{mime_type};base64,{img_data_base64}"
        
        return data_url_string
    except Exception as e:
        logger.error(f"Error converting OpenCV image to data URL: {e}", exc_info=True)
        return None


async def video_echo_handler(websocket):
    global pose_held, pose_start_time
    client_address = websocket.remote_address
    
    connected_clients.add(websocket)

    try:
        async for message in websocket:
            if isinstance(message, str): # Data URLs are strings
                # 1. Convert received data URL to OpenCV image
                opencv_image = data_url_to_cv2_img(message)

                if opencv_image is not None:
                    # logger.info(f"Successfully converted received frame to OpenCV image. Shape: {opencv_image.shape}")
                    
                    # --- OPENCV PROCESSING ---
                    
                    img = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB if needed
                    results = pose.process(img)
                    mp_drawing.draw_landmarks(img, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                    processed_image = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)  # Convert back to BGR for OpenCV
                    if is_arms_outstretched(results.pose_landmarks):
                        if pose_start_time is None:
                            pose_start_time = time.time()
                        elif time.time() - pose_start_time >= POSE_HOLD_DURATION:
                            # Pose held long enough
                            pose_held = True
                            logger.info("Pose held for 3 seconds. Proceeding...")
                            # Trigger next phase, maybe set a flag
                    else:
                        pose_start_time = None
                        pose_held = False

                    # --- END OPENCV PROCESSING ---

                    # 2. Convert the (processed) OpenCV image back to a data URL
                    response_data_url = cv2_img_to_data_url(processed_image, image_format='.jpg', quality=70)

                    response = {
                        "type": "frame",
                        "image": response_data_url,
                        "status": pose_held
                    }

                    if response_data_url:
                        await websocket.send(json.dumps(response))
                        # logger.info(f"Echoed processed frame (size: {len(response_data_url)} bytes) back to {client_address}")
                    else:
                        logger.error(f"Failed to convert processed OpenCV image back to data URL for client {client_address}")
                else:
                    logger.warning(f"Could not convert message from {client_address} to OpenCV image. Original message size: {len(message)}")
                    # Optionally, send an error message back or just skip
                    # await websocket.send("Error: Could not process frame.")

            else:
                logger.warning(f"Received non-string message from {client_address}. Type: {type(message)}. Size: {len(message) if hasattr(message, '__len__') else 'N/A'}. Ignoring.")

    except websockets.exceptions.ConnectionClosedOK:
        logger.info(f"Client {client_address} disconnected gracefully.")
    except websockets.exceptions.ConnectionClosedError as e:
        logger.warning(f"Client {client_address} connection closed with error: {e}")
    except Exception as e:
        logger.error(f"An error occurred with client {client_address}: {e}", exc_info=True)
    finally:
        logger.info(f"Connection closed for client {client_address}.")
        if websocket in connected_clients:
            connected_clients.remove(websocket)

async def main():
    # host = "localhost"
    host = "0.0.0.0"
    port = 8765
    logger.info(f"Starting WebSocket server on ws://{host}:{port}")
    async with websockets.serve(video_echo_handler, host, port, max_size=2**20 * 5): # 5MB limit
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server failed to start or run: {e}", exc_info=True)


