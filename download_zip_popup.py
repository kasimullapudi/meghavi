import requests
import tkinter as tk
from tkinter import ttk
from threading import Thread
import time
import tqdm
import json

def format_size(byte_count):
    """Convert a byte count into a human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if byte_count < 1024:
            return f"{byte_count:.2f} {unit}"
        byte_count /= 1024
    return f"{byte_count:.2f} PB"

def _download_zip(root, url, save_path, progress_var, progress_bar, progress_text, task_label, speed_label, popup):
    response = requests.get(url, stream=True)
    
    # Get metadata from header
    metadata = response.headers.get('X-zip-metadata')
    if metadata:
        try:
            total_size = int(json.loads(metadata).get('totalSize'))
            total_size/=2
        except Exception as e:
            print("Error parsing metadata:", e)
            total_size = None
    else:
        total_size = None

    # Fallback to Content-Length if metadata is not available/valid
    if not total_size:
        try:
            total_size = int(response.headers.get("content-length", 0))
        except Exception:
            total_size = 0

    print(f"Total Size: {total_size} bytes")  # Debug print

    downloaded = 0
    start_time = time.time()

    if total_size > 0:
        console_bar = tqdm.tqdm(desc="Downloading", total=total_size, unit="B", unit_scale=True)
    else:
        console_bar = None
        popup.after(0, lambda: progress_bar.config(mode="indeterminate"))
        popup.after(0, progress_bar.start)

    with open(save_path, "wb") as file:
        if console_bar:
            for chunk in response.iter_content(chunk_size=1024):
                if not chunk:
                    continue
                file.write(chunk)
                downloaded += len(chunk)
                percent_value = downloaded / total_size * 100
                elapsed = time.time() - start_time
                speed = downloaded / elapsed if elapsed > 0 else 0
                speed_str = format_size(speed) + "/s"
                
                # Update progress bar and overlay percentage
                popup.after(0, progress_var.set, percent_value)
                popup.after(0, progress_text.config, {'text': f"{int(percent_value)}%"})
                popup.after(0, task_label.config, {'text': f"{format_size(downloaded)} / {format_size(total_size)} completed"})
                popup.after(0, speed_label.config, {'text': f"Speed: {speed_str}"})
                console_bar.update(len(chunk))
        else:
            for chunk in response.iter_content(chunk_size=1024):
                if not chunk:
                    continue
                file.write(chunk)
                downloaded += len(chunk)
                elapsed = time.time() - start_time
                speed = downloaded / elapsed if elapsed > 0 else 0
                speed_str = format_size(speed) + "/s"
                
                popup.after(0, progress_text.config, {'text': "..."})
                popup.after(0, task_label.config, {'text': f"{format_size(downloaded)} downloaded"})
                popup.after(0, speed_label.config, {'text': f"Speed: {speed_str}"})
    if console_bar is None:
        popup.after(0, progress_bar.stop)

    def finish():
        print("Download complete.")
        popup.after(0, progress_text.config, {'text': "100%"})
        popup.after(0, task_label.config, {'text': "Download complete."})
        popup.after(0, speed_label.config, {'text': "Speed: 0 B/s"})
        popup.destroy()
        root.quit()

    popup.after(0, finish)

def run_download_popup_window(url, save_path):
    root = tk.Tk()
    root.withdraw()
    popup = tk.Toplevel(root)
    popup.title("Downloading")
    popup.resizable(False, False)

    # Ensure the popup appears as the main window and comes forward
    popup.attributes("-topmost", True)

    # Header label with black text
    header_label = tk.Label(
        popup,
        text="Found New Videos on Server",
        font=("Helvetica", 16, "bold"),
        fg="black",  # Changed to black
        bg=popup["bg"]
    )
    header_label.pack(pady=(10, 0))

    style = ttk.Style(popup)
    style.theme_use('default')
    style.configure(
        "Custom.Horizontal.TProgressbar",
        troughcolor='white',
        background='#4CAF50',
        thickness=20,
        bordercolor='black',
        lightcolor='#4CAF50',
        darkcolor='#4CAF50'
    )

    # Remove external percent label; only use overlay text on the progress bar.
    task_label = tk.Label(popup, text="0.00 B / ? completed", font=("Segoe UI", 10))
    task_label.pack(pady=(10, 5))

    speed_label = tk.Label(popup, text="Speed: 0 B/s", font=("Segoe UI", 10))
    speed_label.pack(pady=(0, 10))

    progress_var = tk.DoubleVar()

    # Container to hold the progress bar and the overlay text.
    progress_container = tk.Frame(popup)
    progress_container.pack(padx=20, pady=(0, 20))

    progress_bar = ttk.Progressbar(
        progress_container,
        orient="horizontal",
        mode="determinate",
        variable=progress_var,
        maximum=100,
        length=500,
        style="Custom.Horizontal.TProgressbar"
    )
    progress_bar.pack()

    # Overlay label (inside the progress bar) with a smaller font.
    progress_text = tk.Label(progress_container, text="0%", font=("Segoe UI", 9, "bold"))
    progress_text.place(relx=0.5, rely=0.5, anchor="center")
    # Center the popup window on screen with reduced height
    popup.update_idletasks()
    w, h = 550, 250  # Reduced height
    x = (popup.winfo_screenwidth() - w) // 2
    y = (popup.winfo_screenheight() - h) // 2
    popup.geometry(f"{w}x{h}+{x}+{y}")

    Thread(
        target=_download_zip,
        args=(root, url, save_path, progress_var, progress_bar, progress_text, task_label, speed_label, popup),
        daemon=True
    ).start()

    root.mainloop()