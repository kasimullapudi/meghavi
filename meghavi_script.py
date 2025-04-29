#!/usr/bin/env python3
import os
import math
import time
import cv2
import threading
import datetime
import requests
from ultralytics import YOLO
from threading import Thread, Lock, Event
from meghavi_functions import checkEachDay
from webview_scrnsaver import open_screensaver, close_screensaver
import numpy as np
# -----------------------------------------------------------------------------
# Configuration & Constants
# -----------------------------------------------------------------------------
MODEL_PATH = "models/model.pt"
STREAM_URL = "http://192.168.31.116:5000/video"
OUTPUT_DIR = "captured_faces"
MAX_DISTANCE_CM = 150.0
AREA_THRESHOLD = 5000
SHARPNESS_THRESHOLD = 100.0
YAW_THRESHOLD = 10
PITCH_THRESHOLD = 10
# calibration coefficients
a = 9703.20
b = -0.4911842338691967

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Initialize model & face mesh once
model = YOLO(MODEL_PATH)
import mediapipe as mp
face_mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=False)

# Shared capture flag and lock
capture_lock = Lock()
captured = False

# -----------------------------------------------------------------------------
# VideoStream: low-latency camera reader
# -----------------------------------------------------------------------------
class VideoStream:
    def __init__(self, url):
        self.cap = cv2.VideoCapture(url)
        if not self.cap.isOpened():
            raise RuntimeError(f"Unable to open stream: {url}")
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.frame = None
        self.stopped = False
        t = threading.Thread(target=self._reader, daemon=True)
        t.start()

    def _reader(self):
        while not self.stopped:
            ret, frm = self.cap.read()
            if not ret:
                self.stop()
                break
            self.frame = frm

    def read(self):
        return self.frame

    def stop(self):
        self.stopped = True
        self.cap.release()

# -----------------------------------------------------------------------------
# Face capture logic as a reusable function
# -----------------------------------------------------------------------------
def capture_if_face(frame):
    """
    Checks for a valid face in the frame and captures/uploads it once.
    Returns True if capture/upload happened, False otherwise.
    """
    global captured
    with capture_lock:
        if captured:
            return True

        # Run YOLO detection
        results = model(frame, conf=0.4, verbose=False)
        boxes = results[0].boxes
        if not boxes:
            return False

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mesh = face_mesh.process(rgb)
        if not mesh.multi_face_landmarks:
            return False
        lm = [(p.x, p.y) for p in mesh.multi_face_landmarks[0].landmark]

        for box in boxes:
            conf = float(box.conf[0])
            if conf < 0.4:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            area = (x2 - x1) * (y2 - y1)
            # size check
            if area < AREA_THRESHOLD:
                continue

            # distance check
            dist = a * (area ** b)
            if dist > MAX_DISTANCE_CM:
                continue

            # pose estimation
            MODEL_POINTS = mp.solutions.face_mesh.FACEMESH_CONTOURS
            # estimate head pose
            # using nose, chin, eyes, mouth landmarks
            mp_pts = {
                'nose_tip': 1, 'chin': 199,
                'left_eye': 33, 'right_eye': 263,
                'left_mouth': 61, 'right_mouth': 291
            }
            pts_2d = []
            for name, idx in mp_pts.items():
                x = lm[idx][0] * w
                y = lm[idx][1] * h
                pts_2d.append((x, y))
            cam = np.array([[w, 0, w/2], [0, w, h/2], [0, 0, 1]], dtype=np.float64)
            dist_coeffs = np.zeros((4, 1))
            ok, rvec, _ = cv2.solvePnP(
                np.array([ (0.0,0.0,0.0), (0.0,-330.0,-65.0), (-165.0,170.0,-135.0),
                            (165.0,170.0,-135.0), (-150.0,-150.0,-125.0), (150.0,-150.0,-125.0) ], dtype=np.float64),
                np.array(pts_2d, dtype=np.float64), cam, dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )
            if not ok:
                continue
            R, _ = cv2.Rodrigues(rvec)
            sy = math.sqrt(R[0,0]**2 + R[1,0]**2)
            pitch = math.degrees(math.atan2(-R[2,0], sy))
            yaw   = math.degrees(math.atan2(R[1,0], R[0,0]))
            if abs(yaw) > YAW_THRESHOLD or abs(pitch) > PITCH_THRESHOLD:
                continue

            # sharpness check
            roi_gray = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
            var = cv2.Laplacian(roi_gray, cv2.CV_64F).var()
            if var < SHARPNESS_THRESHOLD:
                continue

            # symmetry check
            le_y = lm[mp_pts['left_eye']][1] * h
            re_y = lm[mp_pts['right_eye']][1] * h
            if abs(le_y - re_y) > 0.03 * h:
                continue

            # capture & upload
            path = os.path.join(OUTPUT_DIR, 'face.jpg')
            cv2.imwrite(path, frame)
            def async_upload(p):
                try:
                    res = requests.post(
                        'https://meghavi-kiosk-api.onrender.com/api/faces/upload',
                        files={'image': open(p, 'rb')},
                        data={'deviceId': 'DEV3617'}
                    )
                    print("Upload successful." if res.status_code == 201 else f"Upload failed: {res.status_code}")
                except Exception as e:
                    print(f"Upload exception: {e}")
            Thread(target=async_upload, args=(path,), daemon=True).start()
            captured = True
            print(f"Captured face at {dist:.1f}cm")
            return True

        return False

# -----------------------------------------------------------------------------
# Main application
# -----------------------------------------------------------------------------
def main():
    # Launch kiosk app in parallel
    Thread(target=lambda: os.system("python app.py"), daemon=True).start()

    # Daily data check
    today = datetime.datetime.today().strftime("%d-%m-%Y")
    prev = open('textFiles/date_txt.txt').read().strip()
    checkEachDay(
        today, prev,
        "textFiles/ids.txt",
        "https://meghavi-kiosk-api.onrender.com/api/videos/get-all",
        "https://meghavi-kiosk-api.onrender.com/api/videos/download-all",
        "videos.zip", "extracted", "videos"
    )

    stream = VideoStream(STREAM_URL)
    face_last_seen = time.time()
    alerted = False
    screensaver_running = False

    print("Starting live detection. Press 'q' to quit.")
    while True:
        frame = stream.read()
        if frame is None:
            time.sleep(0.01)
            continue
        rotated = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

        # Annotate detections
        results = model(rotated, conf=0.4, verbose=False)
        detections = results[0].boxes
        annotated = rotated.copy()
        face_found = False
        if detections:
            for box in detections:
                conf = float(box.conf[0])
                if conf < 0.4:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                area_px = (x2 - x1) * (y2 - y1)
                dist = a * (area_px ** b)
                if dist < MAX_DISTANCE_CM:
                    face_found = True
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0,255,0), 2)
                    cv2.putText(annotated, f"Dist: {dist:.1f}cm", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)

        # Attempt face capture (once)
        # capture_if_face(annotated)

        # Screensaver logic
        now = time.time()
        if face_found:
            face_last_seen = now
            alerted = False
            if screensaver_running:
                print("Face detected — closing screensaver.")
                close_screensaver()
                screensaver_running = False
        else:
            if (now - face_last_seen) >= 10 and not alerted:
                alerted = True
                if not screensaver_running:
                    print("No face for 10s — opening screensaver.")
                    open_screensaver()
                    screensaver_running = True

        cv2.imshow("Live Face Detection", annotated)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    stream.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
