import os
import cv2
import numpy as np
import time


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FACE_CASCADE_PATH = os.path.join(
    BASE_DIR,
    "haarcascade_frontalface_default.xml"
)

EYE_CASCADE_PATH = os.path.join(
    BASE_DIR,
    "haarcascade_eye_tree_eyeglasses.xml"
)

face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)
eye_cascade = cv2.CascadeClassifier(EYE_CASCADE_PATH)

closed_eye_frames = 0
DROWSY_THRESHOLD = 8


def detect_drowsiness(image_bytes):
    global closed_eye_frames

    try:
        # Convert browser image into OpenCV image
        image_array = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if frame is None:
            return {
                "status": "ERROR",
                "message": "Could not read camera image"
            }

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect face
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )

        if len(faces) == 0:
            closed_eye_frames = 0

            return {
                "status": "AWAKE",
                "message": "Face not detected"
            }

        # Use first detected face
        x, y, w, h = faces[0]

        face_gray = gray[y:y+h, x:x+w]

        # Detect eyes
        eyes = eye_cascade.detectMultiScale(
            face_gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(20, 20)
        )

        # No eyes detected = possible closed eyes
        if len(eyes) == 0:

            closed_eye_frames += 1

            print(
                "Eyes closed frames:",
                closed_eye_frames
            )

            if closed_eye_frames >= DROWSY_THRESHOLD:

                return {
                    "status": "DROWSY",
                    "message": "Eyes closed - Drowsiness detected"
                }

            return {
                "status": "AWAKE",
                "message": "Eyes possibly closed",
                "closed_frames": closed_eye_frames
            }

        # Eyes detected = awake
        closed_eye_frames = 0

        return {
            "status": "AWAKE",
            "message": "Eyes open"
        }

    except Exception as e:

        print("Detector error:", e)

        return {
            "status": "ERROR",
            "message": str(e)
        }