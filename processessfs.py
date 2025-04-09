""" import psutil

# Iterate through all running processes
for proc in psutil.process_iter(['pid', 'name']):
    try:
        name = proc.info['name']
        pid = proc.info['pid']
        if name.startswith('E'):
            print(f"{name} - PID: {pid}")
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass
 """

import psutil
import time

# Get the initial list of running processes
existing_pids = {proc.pid for proc in psutil.process_iter(['pid'])}

print("Monitoring new processes...")

while True:
    current_pids = {proc.pid for proc in psutil.process_iter(['pid', 'name'])}
    
    # Find new processes by checking which PIDs were not in the initial list
    new_pids = current_pids - existing_pids
    
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.pid in new_pids:
            try:
                print(f"New Process: {proc.info['name']} - PID: {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    
    # Update the existing process list
    existing_pids = current_pids
    
    time.sleep(1)  # Check every second
