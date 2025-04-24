#!/usr/bin/env python3
import datetime
import time
import cv2
import threading
import subprocess
from ultralytics import YOLO
from meghavi_functions import checkEachDay
from webview_scrnsaver import open_screensaver, close_screensaver

# -----------------------------------------------------------------------------
# Background video reader to always hold the latest frame
# -----------------------------------------------------------------------------
class VideoStream:
    def __init__(self, url):
        self.cap = cv2.VideoCapture(url)
        if not self.cap.isOpened():
            raise RuntimeError(f"Unable to open stream: {url}")
        # make buffer as small as possible
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.frame = None
        self.stopped = False

        t = threading.Thread(target=self._reader, daemon=True)
        t.start()

    def _reader(self):
        while not self.stopped:
            ret, frm = self.cap.read()
            if not ret:
                # stream ended or error
                self.stop()
                break
            self.frame = frm

    def read(self):
        return self.frame

    def stop(self):
        self.stopped = True
        self.cap.release()

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    # 1) Kick off your kiosk app in parallel
    subprocess.Popen(["python", "app.py"])

    # 2) Date-check & video update
    cur_date = datetime.datetime.today().strftime("%d-%m-%Y")
    prev_date = open('textFiles/date_txt.txt', 'r').read().strip()

    # Define parameters in correct order for checkEachDay
    IDS_FILE = "textFiles/ids.txt"
    IDS_API_URL = "https://meghavi-kiosk-api.onrender.com/api/videos/get-all"
    ZIP_URL = "https://meghavi-kiosk-api.onrender.com/api/videos/download-all"
    DOWNLOAD_PATH = "videos.zip"
    EXTRACT_FOLDER = "extracted"
    VIDEOS_FOLDER = "videos"

    # Call positional arguments only
    checkEachDay(
        cur_date,
        prev_date,
        IDS_FILE,
        IDS_API_URL,
        ZIP_URL,
        DOWNLOAD_PATH,
        EXTRACT_FOLDER,
        VIDEOS_FOLDER
    )

    # 3) Load your YOLO model
    model = YOLO("models/model.pt")

    # 4) Calibration parameters
    cm_per_pixel = 0.05
    max_distance = 500
    a = 9703.20
    b = -0.4911842338691967

    # 5) Start the low-latency stream
    STREAM_URL = "http://192.168.31.116:5000/video"
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

        # Rotate the frame 90 degrees clockwise
        rotated = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

        # Run YOLO inference on the rotated frame
        results = model(rotated, conf=0.4, verbose=False)
        detections = results[0].boxes

        face_found = False
        annotated = rotated.copy()
        now = time.time()

        if detections is not None:
            for box in detections:
                conf = float(box.conf[0])
                if conf < 0.4:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                area_px = (x2 - x1) * (y2 - y1)
                distance = a * (area_px ** b)

                if distance < max_distance:
                    face_found = True
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        annotated,
                        f"Dist: {distance:.1f}cm",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 0, 255),
                        2
                    )

        # Handle screensaver logic
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


if __name__ == "__main__":
    main()
