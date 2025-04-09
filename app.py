from flask import Flask, render_template, jsonify, send_from_directory
import os

app = Flask(__name__)

# Absolute path to the videos directory
VIDEO_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'videos')
# Supported video file extensions
SUPPORTED_EXTENSIONS = ('.mp4', '.webm', '.ogg', '.mov')

@app.route('/')
def index():
    # Serve the index.html file located in the templates folder
    return render_template('index.html')

@app.route('/videos/list')
def list_videos():
    try:
        # List video files with supported extensions from the videos folder
        files = [f for f in os.listdir(VIDEO_FOLDER) if f.lower().endswith(SUPPORTED_EXTENSIONS)]
        return jsonify(files)
    except Exception as e:
        # Return error in JSON with HTTP status 500 if something goes wrong
        return jsonify({"error": str(e)}), 500

@app.route('/videos/<path:filename>')
def serve_video(filename):
    # Serve the requested video file from the videos directory
    return send_from_directory(VIDEO_FOLDER, filename)

if __name__ == '__main__':
    # Run the Flask app on the desired host and port
    app.run(host="0.0.0.0", port=5000, debug=True)
