# -*- coding: utf-8 -*-
import os
import cv2
import numpy as np
import requests
import time
from threading import Thread, Lock, Event
from picamera2 import Picamera2

# --- Configuration ---
OUTPUT_DIR = "captured_faces"
MAX_DISTANCE_CM = 150.0
AREA_THRESHOLD = 4000
SHARPNESS_THRESHOLD = 80.0
EYE_SYMM_THRESH = 0.15  # Percentage of face height
BRIGHTNESS_RANGE = (50, 200)

# Calibration
a = 9703.20
b = -0.4911842338691967

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load cascades
BASE_DIR = os.path.dirname(__file__)
CASCADE_DIR = os.path.join(BASE_DIR, 'cascades')

# Use more specialized cascades
FACE_CASCADE_PATH = os.path.join(CASCADE_DIR, 'haarcascade_frontalface_alt2.xml')
EYE_CASCADE_PATH = os.path.join(CASCADE_DIR, 'haarcascade_eye_tree_eyeglasses.xml')

face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)
eye_cascade = cv2.CascadeClassifier(EYE_CASCADE_PATH)

# Shared resources
frame_buffer = None
buffer_lock = Lock()
stop_event = Event()

def frame_reader():
    global frame_buffer
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"size": (640, 480)})
    picam2.configure(config)
    picam2.start()
    while not stop_event.is_set():
        img = picam2.capture_array("main")
        with buffer_lock:
            frame_buffer = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        time.sleep(0.01)
    picam2.stop()

t = Thread(target=frame_reader, daemon=True)
t.start()

def improved_eye_detection(face_roi):
    """Improved eye detection with preprocessing"""
    gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    
    # Preprocessing
    gray = cv2.equalizeHist(gray)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Detect eyes only in upper half of face
    height, width = gray.shape
    upper_roi = gray[0:int(height/2), 0:width]
    
    # Detect with optimized parameters
    eyes = eye_cascade.detectMultiScale(
        upper_roi,
        scaleFactor=1.05,
        minNeighbors=5,
        minSize=(30, 15),  # Adjusted minimum eye size
        flags=cv2.CASCADE_SCALE_IMAGE
    )
    
    # Convert coordinates back to original face ROI
    eyes = [(x, y, w, h) for (x, y, w, h) in eyes]
    return eyes

def validate_eyes(eyes, face_height):
    """Validate eye position and alignment"""
    if len(eyes) < 2:
        return False, "Not enough eyes detected"
        
    # Sort eyes by X coordinate
    eyes = sorted(eyes, key=lambda e: e[0])
    
    # Calculate eye centers
    eye1 = (eyes[0][0] + eyes[0][2]/2, eyes[0][1] + eyes[0][3]/2)
    eye2 = (eyes[1][0] + eyes[1][2]/2, eyes[1][1] + eyes[1][3]/2)
    
    # Check vertical alignment
    vertical_diff = abs(eye1[1] - eye2[1])
    if vertical_diff > (face_height * EYE_SYMM_THRESH):
        return False, f"Poor vertical alignment: {vertical_diff:.1f}px"
    
    # Check horizontal distance
    horizontal_dist = abs(eye1[0] - eye2[0])
    if not (0.15 * face_height < horizontal_dist < 0.6 * face_height):
        return False, f"Abnormal eye spacing: {horizontal_dist:.1f}px"
    
    return True, "Eyes validated"

try:
    while not stop_event.is_set():
        with buffer_lock:
            frame = frame_buffer.copy() if frame_buffer is not None else None
        
        if frame is None:
            time.sleep(0.1)
            continue

        # Convert to grayscale and equalize histogram
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        
        # Detect faces with optimized parameters
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.05,
            minNeighbors=6,
            minSize=(150, 150),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        for (x, y, w, h) in faces:
            # Distance check
            area = w * h
            dist = a * (area ** b)
            if dist > MAX_DISTANCE_CM:
                print(f"Face too far: {dist:.1f}cm")
                continue
                
            # Face ROI processing
            face_roi = frame[y:y+h, x:x+w]
            
            # Eye detection
            eyes = improved_eye_detection(face_roi)
            valid, message = validate_eyes(eyes, h)
            
            if not valid:
                print(f"Eye validation failed: {message}")
                continue
                
            # Sharpness check
            sharpness = cv2.Laplacian(cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
            if sharpness < SHARPNESS_THRESHOLD:
                print(f"Low sharpness: {sharpness:.1f}")
                continue
                
            # Save and upload
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"face_{timestamp}.jpg"
            path = os.path.join(OUTPUT_DIR, filename)
            cv2.imwrite(path, frame)
            print(f"✅ Capture successful! Distance: {dist:.1f}cm")
            Thread(target=async_upload, args=(path,), daemon=True).start()
            break

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nExiting...")

stop_event.set()
t.join()