# -*- coding: utf-8 -*-
import os
import cv2
import math
import numpy as np
import mediapipe as mp
from ultralytics import YOLO
import requests
import time

# --- Configuration ---
MODEL_PATH        = "models/model.pt"
OUTPUT_DIR        = "captured_faces"
STREAM_URL        = "http://192.168.31.116:5000/video"
MAX_DISTANCE_CM   = 100.0    # only capture if under 1 meter

# quality thresholds
AREA_THRESHOLD       = 5000     # px²
SHARPNESS_THRESHOLD  = 100.0    # Laplacian variance threshold
YAW_THRESHOLD        = 10       # degrees
PITCH_THRESHOLD      = 10       # degrees

# power-law coefficients from calibration
a = 9703.20
b = -0.4911842338691967

# head-pose 3D model points
MODEL_POINTS = np.array([
    (0.0,   0.0,    0.0),
    (0.0,  -330.0, -65.0),
    (-165.0,170.0, -135.0),
    (165.0, 170.0, -135.0),
    (-150.0,-150.0,-125.0),
    (150.0, -150.0,-125.0)
], dtype=np.float64)

# landmark indices
LANDMARK_IDS = {
    "nose_tip":    1,
    "chin":        199,
    "left_eye":    33,
    "right_eye":   263,
    "left_mouth":  61,
    "right_mouth": 291
}

# Load models
model     = YOLO(MODEL_PATH)
mp_face   = mp.solutions.face_mesh
face_mesh = mp_face.FaceMesh(static_image_mode=False)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Pose estimation helper
def estimate_head_pose(landmarks, img_size):
    h, w = img_size
    img_pts = np.array([
        (landmarks[LANDMARK_IDS['nose_tip']][0]*w,
         landmarks[LANDMARK_IDS['nose_tip']][1]*h),
        (landmarks[LANDMARK_IDS['chin']][0]*w,
         landmarks[LANDMARK_IDS['chin']][1]*h),
        (landmarks[LANDMARK_IDS['left_eye']][0]*w,
         landmarks[LANDMARK_IDS['left_eye']][1]*h),
        (landmarks[LANDMARK_IDS['right_eye']][0]*w,
         landmarks[LANDMARK_IDS['right_eye']][1]*h),
        (landmarks[LANDMARK_IDS['left_mouth']][0]*w,
         landmarks[LANDMARK_IDS['left_mouth']][1]*h),
        (landmarks[LANDMARK_IDS['right_mouth']][0]*w,
         landmarks[LANDMARK_IDS['right_mouth']][1]*h)
    ], dtype=np.float64)
    cam = np.array([[w, 0, w/2], [0, w, h/2], [0,0,1]], dtype=np.float64)
    dist = np.zeros((4,1))
    ok, rvec, _ = cv2.solvePnP(MODEL_POINTS, img_pts, cam, dist, flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        return None, None
    R, _ = cv2.Rodrigues(rvec)
    sy = math.sqrt(R[0,0]**2 + R[1,0]**2)
    pitch = math.degrees(math.atan2(-R[2,0], sy))
    yaw   = math.degrees(math.atan2(R[1,0], R[0,0]))
    return yaw, pitch

# Sharpness helper
def laplacian_var(gray):
    return cv2.Laplacian(gray, cv2.CV_64F).var()

# Start video capture
cv2.namedWindow("Video Preview")
cap = cv2.VideoCapture(STREAM_URL)
captured = False
print("Starting preview. Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        time.sleep(0.1)
        continue
    # Rotate frame 90° clockwise
    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    cv2.imshow("Video Preview", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

    if captured:
        continue

    # Run detection
    results = model(frame, conf=0.4, verbose=False)
    boxes = results[0].boxes
    if not boxes or len(boxes) == 0:
        continue

    # For each detected box
    for box in boxes:
        conf = float(box.conf[0])
        if conf < 0.4:
            continue
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        area = (x2 - x1) * (y2 - y1)
        if area < AREA_THRESHOLD:
            continue

        # Try landmarks only when a candidate box found
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mesh = face_mesh.process(rgb)
        if not mesh.multi_face_landmarks:
            print("Box detected but landmarks missing.")
            continue
        lm = [(p.x, p.y) for p in mesh.multi_face_landmarks[0].landmark]

        # Distance check
        dist = a * (area ** b)
        if dist > MAX_DISTANCE_CM:
            print(f"Face detected but too far: {dist:.1f}cm")
            continue

        # Pose check
        yaw, pitch = estimate_head_pose(lm, frame.shape[:2])
        if yaw is None or abs(yaw) > YAW_THRESHOLD or abs(pitch) > PITCH_THRESHOLD:
            continue

        # Sharpness check
        roi_gray = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
        if laplacian_var(roi_gray) < SHARPNESS_THRESHOLD:
            continue

        # Eye symmetry check
        h, w = frame.shape[:2]
        le_y = lm[LANDMARK_IDS['left_eye']][1] * h
        re_y = lm[LANDMARK_IDS['right_eye']][1] * h
        if abs(le_y - re_y) > 0.03 * h:
            print("Face detected but not front-on (eye symmetry fail).")
            continue

        # Capture and upload
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        path = os.path.join(OUTPUT_DIR, 'face.jpg')
        cv2.imwrite(path, frame)
        print(f"Captured at {dist:.1f}cm, uploading...")
        try:
            with open(path, 'rb') as f:
                res = requests.post(
                    'https://meghavi-kiosk-api.onrender.com/api/faces/upload',
                    files={'image': f}
                )
            print("Upload status:", res.status_code)
        except Exception as e:
            print("Upload failed:", e)
        captured = True
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
