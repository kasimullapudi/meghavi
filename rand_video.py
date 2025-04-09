import subprocess
import time
import psutil

# Set your condition
var = True

# Open Edge with the URL
edge_process = subprocess.Popen([
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe","--start-fullscreen",
    "http://localhost:5000"
])

# Wait a bit to allow page to load (optional)
time.sleep(5)

# Check your condition and close Edge if true
if var:
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == "msedge.exe":
            proc.kill()
