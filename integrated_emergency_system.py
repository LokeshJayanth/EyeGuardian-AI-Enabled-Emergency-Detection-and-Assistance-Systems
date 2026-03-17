"""
Integrated Emergency Detection System
Combines fire detection model with main AI Emergency Voice Assistance system
"""

import sys
import os
import cv2
from ultralytics import YOLO

# Add the fire model directory to path
sys.path.append(r'C:\Projects\fire_model')

# Import existing emergency components
from yolov8_emergency_detector import YOLOv8EmergencyDetector
from email_sender import EmailSender
from database_manager import DatabaseManager

class IntegratedEmergencySystem:
    def __init__(self):
        """Initialize integrated emergency detection system"""
        self.fire_detector = None
        self.main_detector = YOLOv8EmergencyDetector()
        self.email_sender = EmailSender()
        self.db_manager = DatabaseManager()
        
        # Load working fire detection model
        self.load_fire_model()
        
    def load_fire_model(self):
        """Load the working fire detection model from C:\Projects\fire_model"""
        try:
            fire_model_path = r'C:\Projects\fire_model\yolov8n.pt'
            if os.path.exists(fire_model_path):
                print("🔥 Loading fire detection model...")
                self.fire_detector = YOLO(fire_model_path)
                print("✅ Fire detection model loaded successfully!")
                return True
            else:
                print("⚠️ Fire model not found, using main detector only")
                return False
        except Exception as e:
            print(f"❌ Fire model loading failed: {e}")
            return False
    
    def detect_emergencies(self, frame):
        """Combined emergency detection using both models"""
        all_detections = []
        emergency_score = 0
        emergency_types = []
        
        try:
            # Use fire detector if available
            if self.fire_detector:
                fire_results = self.fire_detector(frame, verbose=False)
                
                for result in fire_results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            conf = box.conf[0].cpu().numpy()
                            cls = int(box.cls[0].cpu().numpy())
                            class_name = self.fire_detector.names[cls]
                            
                            if conf > 0.4:  # Lower threshold for emergency detection
                                detection = {
                                    'class': class_name,
                                    'confidence': conf,
                                    'bbox': [x1, y1, x2, y2],
                                    'source': 'fire_model'
                                }
                                all_detections.append(detection)
                                
                                # Emergency scoring
                                if 'fire' in class_name.lower() or 'smoke' in class_name.lower():
                                    emergency_score += 10
                                    emergency_types.append('fire')
                                elif class_name.lower() == 'person':
                                    emergency_score += 1
                                    if conf > 0.7:
                                        emergency_types.append('person_distress')
            
            # Use main detector for additional detection
            main_results = self.main_detector.detect_frame(frame)
            if main_results:
                for detection in main_results:
                    detection['source'] = 'main_model'
                    all_detections.append(detection)
                    
                    # Add to emergency scoring
                    class_name = detection['class'].lower()
                    if 'weapon' in class_name:
                        emergency_score += 8
                        emergency_types.append('weapon')
                    elif 'explosion' in class_name:
                        emergency_score += 10
                        emergency_types.append('explosion')
            
        except Exception as e:
            print(f"Detection error: {e}")
        
        return all_detections, emergency_score, emergency_types
    
    def draw_detections(self, frame, detections):
        """Draw detection boxes on frame"""
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            conf = det['confidence']
            class_name = det['class']
            source = det.get('source', 'unknown')
            
            # Color coding by emergency type
            if 'fire' in class_name.lower() or 'smoke' in class_name.lower():
                color = (0, 0, 255)  # Red for fire/smoke
            elif 'weapon' in class_name.lower():
                color = (0, 165, 255)  # Orange for weapons
            elif source == 'fire_model':
                color = (0, 255, 255)  # Yellow for fire model detections
            else:
                color = (0, 255, 0)  # Green for normal detections
            
            # Draw bounding box
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            
            # Add label with source
            label = f"{class_name}: {conf:.2f} ({source})"
            cv2.putText(frame, label, (int(x1), int(y1-10)), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return frame
    
    def handle_emergency_alert(self, emergency_types, emergency_score, frame):
        """Handle emergency alerts - send emails, save to database"""
        try:
            # Save emergency screenshot
            timestamp = cv2.getTickCount()
            filename = f"emergency_alert_{timestamp}.jpg"
            cv2.imwrite(filename, frame)
            
            # Prepare alert message
            alert_message = f"""
🚨 EMERGENCY DETECTED! 🚨

Emergency Types: {', '.join(emergency_types)}
Emergency Score: {emergency_score}
Timestamp: {timestamp}
Screenshot: {filename}

Immediate action required!
"""
            
            print(alert_message)
            
            # Send email alert (if configured)
            try:
                self.email_sender.send_emergency_alert(
                    subject="🚨 EMERGENCY DETECTED",
                    message=alert_message,
                    attachment_path=filename
                )
                print("📧 Emergency email sent!")
            except Exception as e:
                print(f"Email sending failed: {e}")
            
            # Save to database
            try:
                self.db_manager.log_emergency(
                    emergency_types=emergency_types,
                    confidence_score=emergency_score,
                    image_path=filename
                )
                print("💾 Emergency logged to database!")
            except Exception as e:
                print(f"Database logging failed: {e}")
                
        except Exception as e:
            print(f"Emergency handling error: {e}")
    
    def run_integrated_system(self):
        """Run the complete integrated emergency detection system"""
        print("🚨 Starting Integrated Emergency Detection System...")
        print("🔥 Fire Detection + 🎯 General Emergency Detection + 📧 Alerts")
        print("Controls: 'q' to quit, 's' to save screenshot, 'a' to trigger manual alert")
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot access camera")
            return
        
        frame_count = 0
        total_alerts = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Run detection every 3 frames for performance
            if frame_count % 3 == 0:
                detections, emergency_score, emergency_types = self.detect_emergencies(frame)
                
                # Draw all detections
                frame = self.draw_detections(frame, detections)
                
                # Check for emergency
                is_emergency = emergency_score >= 5
                
                if is_emergency:
                    total_alerts += 1
                    status = "🚨 EMERGENCY DETECTED!"
                    color = (0, 0, 255)
                    
                    # Handle emergency alert
                    self.handle_emergency_alert(emergency_types, emergency_score, frame)
                    
                else:
                    status = "✅ MONITORING"
                    color = (0, 255, 0)
                
                # Add status overlay
                cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                cv2.putText(frame, f"Emergency Score: {emergency_score}", (10, 70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                cv2.putText(frame, f"Total Alerts: {total_alerts}", (10, frame.shape[0] - 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow('Integrated Emergency Detection System', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                filename = f'manual_screenshot_{frame_count}.jpg'
                cv2.imwrite(filename, frame)
                print(f"📸 Screenshot saved: {filename}")
            elif key == ord('a'):
                print("🚨 MANUAL ALERT TRIGGERED!")
                self.handle_emergency_alert(['manual'], 10, frame)
                total_alerts += 1
            
            frame_count += 1
        
        cap.release()
        cv2.destroyAllWindows()
        print(f"🔚 Integrated system stopped. Total alerts: {total_alerts}")

if __name__ == "__main__":
    try:
        system = IntegratedEmergencySystem()
        system.run_integrated_system()
    except KeyboardInterrupt:
        print("\n🔚 System stopped by user")
    except Exception as e:
        print(f"❌ System error: {e}")
        print("💡 Make sure all dependencies are installed and configured")
