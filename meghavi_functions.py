import time
import os
import psutil
import requests
import zipfile
import shutil
import subprocess
from tqdm import tqdm
import datetime


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

    if not os.path.exists(videos_folder):
        os.makedirs(videos_folder)

    for root, _, files in os.walk(extract_to):
        for file in files:
            if file.endswith((".mp4", ".mkv", ".avi", ".mov")):
                shutil.move(os.path.join(root, file), os.path.join(videos_folder, file))

    shutil.rmtree(extract_to)
    print("Videos extracted and organized.")

def checkEachDay(cur_date,previous_date,IDS_FILE,IDS_API_URL,ZIP_URL,DOWNLOAD_PATH, EXTRACT_FOLDER, VIDEOS_FOLDER):
    if cur_date != previous_date:
        with open('date_txt.txt', 'w') as date_var:
            date_var.write(cur_date)
        
        # Fetch IDs and compare with previous
        prev_ids = set()
        if os.path.exists(IDS_FILE):
            with open(IDS_FILE, 'r') as f:
                prev_ids = set(line.strip() for line in f if line.strip())
        resp = requests.get(IDS_API_URL)
        print("fetching complete")
        data = resp.json()
        if isinstance(data, dict) and 'ids' in data:
            current_ids = set(str(item['_id']) for item in data['ids'])
        else:
            current_ids = set(str(item['_id']) for item in data)
        with open(IDS_FILE, 'w') as f:
            for _id in current_ids:
                f.write(f"{_id}\n")
        added = current_ids - prev_ids
        removed = prev_ids - current_ids

        if added or removed:
            print("Added IDs:", added)
            print("Removed IDs:", removed)
            #download videos if there is a change in server
            download_zip(ZIP_URL, DOWNLOAD_PATH)
            if os.path.exists(VIDEOS_FOLDER):
                shutil.rmtree(VIDEOS_FOLDER)
                print("old videos deleted!")
            extract_and_cleanup(DOWNLOAD_PATH, EXTRACT_FOLDER, VIDEOS_FOLDER)
            print("new videos added")
        else:
            print("No new videos added")
