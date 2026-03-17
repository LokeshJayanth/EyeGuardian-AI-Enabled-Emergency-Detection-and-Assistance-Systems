"""
Real-time Fire/Smoke Detection and Image Upload Script
-----------------------------------------------------
Uses YOLOv8 to detect fire/smoke in camera frames, saves and uploads detected images.
"""

import cv2
import os
from yolov8_emergency_detector import YOLOv8EmergencyDetector
from firebase_admin import credentials, initialize_app, storage
from datetime import datetime
import base64
from PIL import Image
from io import BytesIO

# --- CONFIG ---
MODEL_PATHS = [
    'models/fire_smoke_yolov8s.pt',
    'models/yolov8s.pt',
    'yolov8s.pt'
]
FIREBASE_CRED_PATH = 'ai-emergency-assistant-firebase-adminsdk-fbsvc-a58bb9ed04.json'
FIREBASE_BUCKET = 'ai-emergency-assistant.appspot.com'
UPLOAD_DIR = 'logs/emergency/detected_images'
CONFIDENCE_THRESHOLD = 0.5

os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Initialize YOLOv8 Detector ---
def get_detector():
    for path in MODEL_PATHS:
        if os.path.exists(path):
            print(f"Using model: {path}")
            return YOLOv8EmergencyDetector(model_path=path, confidence_threshold=CONFIDENCE_THRESHOLD)
    print("No custom model found, using default YOLOv8.")
    return YOLOv8EmergencyDetector(confidence_threshold=CONFIDENCE_THRESHOLD)

detector = get_detector()

# --- Initialize Firebase ---
def init_firebase():
    if not os.path.exists(FIREBASE_CRED_PATH):
        print("Firebase credentials not found, skipping upload.")
        return None, None
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    app = initialize_app(cred, {'storageBucket': FIREBASE_BUCKET})
    bucket = storage.bucket()
    print("Firebase initialized.")
    return app, bucket

firebase_app, firebase_bucket = init_firebase()

# --- Helper: Upload image to Firebase ---
def upload_to_firebase(image_path, bucket):
    if not bucket:
        print("No Firebase bucket, skipping upload.")
        return None
    blob_name = f"detected_images/{os.path.basename(image_path)}"
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(image_path)
    print(f"Uploaded to Firebase: {blob.public_url}")
    return blob.public_url

# --- Main Detection Loop ---
def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Camera not accessible.")
        return
    print("Starting fire/smoke detection. Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame.")
            break
        detections = detector.detect_objects(frame)
        for det in detections:
            if det['is_emergency'] and det['emergency_type'] in ['fire', 'smoke'] and det['confidence'] >= CONFIDENCE_THRESHOLD:
                # Save image
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"fire_smoke_{timestamp}.jpg"
                save_path = os.path.join(UPLOAD_DIR, filename)
                cv2.imwrite(save_path, frame)
                print(f"Fire/Smoke detected! Image saved: {save_path}")
                # Upload to Firebase
                upload_to_firebase(save_path, firebase_bucket)
        # Show frame
        cv2.imshow('Fire/Smoke Detection', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
