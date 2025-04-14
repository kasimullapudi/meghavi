# webview_scrnsaver.py
import sys
import os
import subprocess

# global handle
_screensaver_proc = None

def open_screensaver():
    global _screensaver_proc
    if _screensaver_proc is None:
        # locate your screensaver.py in the same folder
        script = os.path.join(os.path.dirname(__file__), 'screensaver.py')
        _screensaver_proc = subprocess.Popen([sys.executable, script])

def close_screensaver():
    global _screensaver_proc
    if _screensaver_proc:
        _screensaver_proc.terminate()
        _screensaver_proc.wait()
        _screensaver_proc = None
