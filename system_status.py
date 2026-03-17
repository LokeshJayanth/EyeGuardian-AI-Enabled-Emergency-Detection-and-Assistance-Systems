#!/usr/bin/env python3
"""
🚨 Emergency Detection System - Status Checker
==============================================

This script checks the status of all system components:
- Database connectivity
- Flask application
- YOLO model
- Firebase integration
- Voice recognition
- Camera access
- File permissions
"""

import os
import sys
import sqlite3
import requests
import json
import time
from pathlib import Path
import subprocess

class SystemStatusChecker:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.status = {
            'database': False,
            'flask_app': False,
            'yolo_model': False,
            'firebase': False,
            'voice_recognition': False,
            'camera': False,
            'file_permissions': False,
            'templates': False,
            'static_files': False
        }
    
    def check_database(self):
        """Check database connectivity and tables"""
        print("🔍 Checking database...")
        try:
            db_path = self.project_root / 'emergency_system.db'
            if not db_path.exists():
                print("❌ Database file not found")
                return False
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check required tables
            tables = ['users', 'emergency_history', 'emergency_contacts', 'contact_submissions']
            for table in tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if not cursor.fetchone():
                    print(f"❌ Table '{table}' not found")
                    conn.close()
                    return False
            
            # Check for data
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM emergency_history")
            history_count = cursor.fetchone()[0]
            
            print(f"✅ Database OK - Users: {user_count}, History: {history_count}")
            conn.close()
            self.status['database'] = True
            return True
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            return False
    
    def check_flask_app(self):
        """Check if Flask application is running"""
        print("🔍 Checking Flask application...")
        try:
            response = requests.get('http://localhost:5000/api/stats', timeout=5)
            if response.status_code == 200:
                print("✅ Flask application is running")
                self.status['flask_app'] = True
                return True
            else:
                print(f"❌ Flask app responded with status {response.status_code}")
                return False
        except requests.exceptions.RequestException:
            print("❌ Flask application is not running")
            return False
    
    def check_yolo_model(self):
        """Check YOLO model availability"""
        print("🔍 Checking YOLO model...")
        try:
            yolo_dir = self.project_root / 'yolov5'
            if yolo_dir.exists():
                print("✅ YOLO directory exists")
                self.status['yolo_model'] = True
                return True
            else:
                print("⚠️ YOLO directory not found (optional)")
                return True  # Not critical
        except Exception as e:
            print(f"❌ YOLO check error: {e}")
            return False
    
    def check_firebase(self):
        """Check Firebase configuration"""
        print("🔍 Checking Firebase configuration...")
        try:
            firebase_config = self.project_root / 'firebase_config.json'
            if firebase_config.exists():
                print("✅ Firebase config file exists")
                self.status['firebase'] = True
                return True
            else:
                print("⚠️ Firebase config not found (optional)")
                return True  # Not critical
        except Exception as e:
            print(f"❌ Firebase check error: {e}")
            return False
    
    def check_voice_recognition(self):
        """Check voice recognition dependencies"""
        print("🔍 Checking voice recognition...")
        try:
            import speech_recognition
            print("✅ SpeechRecognition module available")
            self.status['voice_recognition'] = True
            return True
        except ImportError:
            print("❌ SpeechRecognition module not available")
            return False
    
    def check_camera(self):
        """Check camera access"""
        print("🔍 Checking camera access...")
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                print("✅ Camera access available")
                cap.release()
                self.status['camera'] = True
                return True
            else:
                print("⚠️ Camera not accessible (may be in use)")
                return True  # Not critical
        except Exception as e:
            print(f"⚠️ Camera check error: {e} (optional)")
            return True  # Not critical
    
    def check_file_permissions(self):
        """Check file permissions"""
        print("🔍 Checking file permissions...")
        try:
            # Check if we can write to logs directory
            logs_dir = self.project_root / 'logs'
            logs_dir.mkdir(exist_ok=True)
            
            test_file = logs_dir / 'test_permissions.txt'
            test_file.write_text('test')
            test_file.unlink()
            
            print("✅ File permissions OK")
            self.status['file_permissions'] = True
            return True
        except Exception as e:
            print(f"❌ File permissions error: {e}")
            return False
    
    def check_templates(self):
        """Check template files"""
        print("🔍 Checking template files...")
        try:
            templates_dir = self.project_root / 'templates'
            required_templates = ['home.html', 'admin_dashboard.html', 'login.html']
            
            for template in required_templates:
                if not (templates_dir / template).exists():
                    print(f"❌ Template {template} not found")
                    return False
            
            print("✅ All required templates found")
            self.status['templates'] = True
            return True
        except Exception as e:
            print(f"❌ Template check error: {e}")
            return False
    
    def check_static_files(self):
        """Check static files"""
        print("🔍 Checking static files...")
        try:
            static_dir = self.project_root / 'static'
            if static_dir.exists():
                print("✅ Static files directory exists")
                self.status['static_files'] = True
                return True
            else:
                print("❌ Static files directory not found")
                return False
        except Exception as e:
            print(f"❌ Static files check error: {e}")
            return False
    
    def run_all_checks(self):
        """Run all system checks"""
        print("🚨 Emergency Detection System - Status Check")
        print("=" * 50)
        
        checks = [
            self.check_database,
            self.check_templates,
            self.check_static_files,
            self.check_file_permissions,
            self.check_yolo_model,
            self.check_firebase,
            self.check_voice_recognition,
            self.check_camera,
            self.check_flask_app
        ]
        
        for check in checks:
            check()
            time.sleep(0.5)  # Small delay between checks
        
        self.print_summary()
    
    def print_summary(self):
        """Print system status summary"""
        print("\n" + "=" * 50)
        print("📊 SYSTEM STATUS SUMMARY")
        print("=" * 50)
        
        total_checks = len(self.status)
        passed_checks = sum(self.status.values())
        
        for component, status in self.status.items():
            icon = "✅" if status else "❌"
            print(f"{icon} {component.replace('_', ' ').title()}")
        
        print(f"\n📈 Overall Status: {passed_checks}/{total_checks} components working")
        
        if passed_checks == total_checks:
            print("🎉 All systems operational!")
        elif passed_checks >= total_checks * 0.8:
            print("⚠️ Most systems working (minor issues)")
        else:
            print("🚨 Multiple system issues detected")
        
        print("\n🔧 Next Steps:")
        if not self.status['flask_app']:
            print("   - Start the Flask application: python emergency_api_simple.py")
        if not self.status['database']:
            print("   - Run system setup: python setup_system.py")
        if not self.status['voice_recognition']:
            print("   - Install voice recognition: pip install SpeechRecognition pyaudio")

def main():
    """Main function"""
    checker = SystemStatusChecker()
    checker.run_all_checks()

if __name__ == "__main__":
    main() 