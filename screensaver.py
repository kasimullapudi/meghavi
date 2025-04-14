# screensaver.py
import webview

if __name__ == '__main__':
    webview.create_window(
        'Screensaver',
        'http://localhost:5000',
        frameless=True,
        fullscreen=True
    )
    webview.start()
