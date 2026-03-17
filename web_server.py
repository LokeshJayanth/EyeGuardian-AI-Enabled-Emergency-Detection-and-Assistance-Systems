"""
Web Server for AI Emergency Detection System
Serves the camera.html interface and connects to the YOLOv8 detection API
"""

from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__, template_folder='templates', static_folder='static')

@app.route('/')
def index():
    """Serve the main camera detection interface"""
    return render_template('camera.html')

@app.route('/camera')
def camera():
    """Serve the camera detection page"""
    return render_template('camera.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

if __name__ == '__main__':
    print("🌐 Starting AI Emergency Detection Web Server...")
    print("📹 Camera Interface: http://localhost:5000")
    print("🔥 YOLOv8 Detection API: http://localhost:5001")
    print("\n📋 Instructions:")
    print("1. Start the detection API first: python camera_detection_api.py")
    print("2. Open http://localhost:5000 in your browser")
    print("3. Click 'Start Detection' to begin real-time fire detection")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
