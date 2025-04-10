import time
import os
import psutil
import requests
import zipfile
import shutil
import random
import subprocess
from tqdm import tqdm
import datetime
import pyautogui

import cv2
from ultralytics import YOLO


def killProcessByName():
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            name = proc.info['name']
            pid = proc.info['pid']
            if name == "msedge.exe":
                print(f"process found with pid: {pid}!")
                val = os.system(f"taskkill /pid {pid}")
                print("process killed!") if val == 0 else print("")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


cur_date = datetime.datetime.today().strftime("%d-%m-%Y")
print("cur date: ", cur_date)
previous_date = open('date_txt.txt', 'r').readline()
print("date from txt: ", previous_date)

# Configurations
ZIP_URL = "https://meghavi-kiosk-api.onrender.com/api/videos/download-all" 
DOWNLOAD_PATH = "videos.zip"
EXTRACT_FOLDER = "extracted"
VIDEOS_FOLDER = "videos"
TARGET_FOLDER = "selected_video"
TARGET_VIDEO_NAME = "screensaver_vid.mp4"

# Download the ZIP file
def download_zip(url, save_path):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get("content-length", 0))
    with open(save_path, "wb") as file, tqdm(
            desc="Downloading", total=total_size, unit="B", unit_scale=True
    ) as progress_bar:
        for chunk in response.iter_content(chunk_size=1024):
            file.write(chunk)
            progress_bar.update(len(chunk))
    print("Download complete.")

# Extract ZIP and delete it
def extract_and_cleanup(zip_path, extract_to, videos_folder):
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)
    os.remove(zip_path)

    # Ensure videos folder exists
    if not os.path.exists(videos_folder):
        os.makedirs(videos_folder)

    # Move video files to the videos folder
    for root, _, files in os.walk(extract_to):
        for file in files:
            if file.endswith((".mp4", ".mkv", ".avi", ".mov")):
                shutil.move(os.path.join(root, file), os.path.join(videos_folder, file))

    # Delete extracted folder after moving files
    shutil.rmtree(extract_to)
    print("Videos extracted and organized.")

# Step 3: Select a random video and copy it to target folder
def select_random_video(videos_folder, target_folder, target_video_name):
    video_files = [f for f in os.listdir(videos_folder) if f.endswith((".mp4", ".mkv", ".avi", ".mov"))]

    if not video_files:
        print("No video files found.")
        return

    selected_video = random.choice(video_files)

    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    target_path = os.path.join(target_folder, target_video_name)
    if os.path.exists(target_path):
        try:
            os.remove(target_path)
        except PermissionError:
            print("Cannot delete old video, it's in use.")
            return

    shutil.copy(os.path.join(videos_folder, selected_video), target_path)
    print(f"Selected video: {selected_video} copied as {target_video_name}")


if cur_date != previous_date:
    date_var = open('date_txt.txt', 'w')
    date_var.write(datetime.datetime.today().strftime('%d-%m-%Y'))
    date_var.close()
    
download_zip(ZIP_URL, DOWNLOAD_PATH)
extract_and_cleanup(DOWNLOAD_PATH, EXTRACT_FOLDER, VIDEOS_FOLDER)
select_random_video(VIDEOS_FOLDER, TARGET_FOLDER, TARGET_VIDEO_NAME)


# Initialization for face detection
model_path = "models/model.pt"
model = YOLO(model_path)

# Open a connection to the webcam.
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

print("Starting live detection. Press 'q' to quit.")

# Initialize timing variables.
face_last_seen_time = time.time()
alerted = False
count = 0
face_flag = False  # Indicates whether a face is detected in the current frame
screensaver_running = False  # Tracks whether the screensaver subprocess is open

while True:
    # Read frame and run inference for face detection
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to grab frame.")
        break

    # Run YOLO inference with a confidence threshold of 0.4 and suppress verbose output.
    results = model(frame, conf=0.4, verbose=False)
    current_time = time.time()

    # Process detections from the first (and only) result.
    detections = results[0].boxes
    face_found = False

    if detections is not None:
        for box in detections:
            conf = float(box.conf[0])
            if conf >= 0.4:
                face_found = True
                break

    if face_found:
        face_flag = True
        face_last_seen_time = current_time
        count += 1
        print(f"Face detected {count} times... Its time is {datetime.datetime.now().strftime('%d-%m-%Y -- %H-%M-%S')}")
        alerted = False  # reset the alert flag if a face is detected

        # If the screensaver is running and a face is detected, then kill it.
        if screensaver_running:
            print("Face detected while screensaver is open! Killing the process.")
            killProcessByName()
            screensaver_running = False

    else:
        face_flag = False
        # Check if no face has been seen for at least 10 seconds.
        if (current_time - face_last_seen_time) >= 10 and not alerted:
            print("No face detected for 10 seconds!")
            alerted = True  # Prevent further printing until a new face is found
            
            # If the screensaver is not already running, open it.
            if not screensaver_running:
                print("Opening screensaver (Edge in kiosk mode).")
                subprocess.Popen([
                    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
                    "--kiosk",
                    "http://localhost:5000"
                ])
                time.sleep(1)
                pyautogui.press('f11')
                screensaver_running = True

    # Annotate and show the frame.
    annotated_frame = results[0].plot()
    cv2.imshow("Live Face Detection", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

print("Live detection stopped.")
