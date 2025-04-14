import subprocess
import datetime
import time
import cv2
from ultralytics import YOLO
from meghavi_functions import killProcessByName,checkEachDay
import pyautogui
from webview_scrnsaver import open_screensaver,close_screensaver

cur_date = datetime.datetime.today().strftime("%d-%m-%Y")
print("cur date: ", cur_date)
previous_date = open('textFiles/date_txt.txt', 'r').readline().strip()
print("date from txt: ", previous_date)

# Configurations
ZIP_URL = "https://meghavi-kiosk-api.onrender.com/api/videos/download-all"
DOWNLOAD_PATH = "videos.zip"
EXTRACT_FOLDER = "extracted"
VIDEOS_FOLDER = "videos"
IDS_API_URL = "https://meghavi-kiosk-api.onrender.com/api/videos/get-all"
IDS_FILE = "textFiles/ids.txt"


checkEachDay(cur_date,previous_date,IDS_FILE,IDS_API_URL,ZIP_URL,DOWNLOAD_PATH,EXTRACT_FOLDER,VIDEOS_FOLDER)

# Initialization for face detection
model_path = "models/model.pt"
model = YOLO(model_path)

# Calibration for area in cm^2
cm_per_pixel = 0.05  # adjust based on your calibration
min_area_cm2 = 20.0  # minimum face area to trigger detection

# Open a connection to the webcam.
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

print("Starting live detection. Press 'q' to quit.")

face_last_seen_time = time.time()
alerted = False
count = 0
face_flag = False
screensaver_running = False

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to grab frame.")
        break

    results = model(frame, conf=0.4, verbose=False)
    current_time = time.time()
    detections = results[0].boxes
    face_found = False
    annotated_frame = frame.copy()

    if detections is not None:
        for box in detections:
            conf = float(box.conf[0])
            if conf >= 0.4:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                width_px = x2 - x1
                height_px = y2 - y1
                area_px = width_px * height_px
                area_cm2 = area_px * (cm_per_pixel ** 2)
                if area_cm2 > min_area_cm2:
                    face_found = True
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        annotated_frame,
                        f"Area: {area_cm2:.2f} cm^2",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )

    if face_found:
        face_flag = True
        face_last_seen_time = current_time
        alerted = False
        if screensaver_running:
            print("Face detected while screensaver is open! Killing the process.")
            # killProcessByName()
            close_screensaver()

            screensaver_running = False
    else:
        face_flag = False
        if (current_time - face_last_seen_time) >= 10 and not alerted:
            print("No face detected for 10 seconds!")
            alerted = True
            if not screensaver_running:
                print("Opening screensaver in a window.")
                open_screensaver()
                screensaver_running = True

    cv2.imshow("Live Face Detection", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

print("Live detection stopped.")
