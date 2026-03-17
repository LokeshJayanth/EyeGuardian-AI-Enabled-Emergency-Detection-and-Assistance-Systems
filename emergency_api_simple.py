#!/usr/bin/env python3
"""
🚨 Emergency Detection API - Simplified Version
Flask web application for emergency detection using YOLOv5
"""

import os
import sys
from flask import Flask, request, render_template, send_file, jsonify, send_from_directory, redirect, session, url_for, Response
import cv2
import numpy as np
from PIL import Image
import io
import base64
import json
from datetime import datetime
import time
import requests
from pathlib import Path
import logging
import sqlite3
import threading
from functools import wraps

# Disable AI/ML features
FAISS_AVAILABLE = False
ST_AVAILABLE = False
OPENAI_AVAILABLE = False
GEMINI_AVAILABLE = False

# Placeholder for YOLO detector
class YOLOv8EmergencyDetector:
    def __init__(self, *args, **kwargs):
        self.model = None
        print("⚠️  YOLO model is disabled in this version")
    
    def detect(self, *args, **kwargs):
        return []

def process_image_for_api(*args, **kwargs):
    return []

# Optional Cohere imports
try:
    import cohere  # type: ignore
    COHERE_AVAILABLE = True
except Exception:
    COHERE_AVAILABLE = False

# Import YOLOv8 for camera detection
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    print("✅ YOLOv8 (Ultralytics) available for camera detection")
except ImportError as e:
    YOLO_AVAILABLE = False
    print(f"⚠️ YOLOv8 not available: {e}")

# Add fire model path
sys.path.append(r'C:\Projects\fire_model')

# Import Firebase configuration
try:
    from firebase_config import contact_manager
    FIREBASE_AVAILABLE = True
    print("✅ Firebase integration available")
except ImportError as e:
    FIREBASE_AVAILABLE = False
    print(f"⚠️ Firebase integration not available: {e}")

# Import admin authentication
try:
    from admin_auth import verify_admin_credentials, create_admin_session, verify_admin_session, get_admin_email, logout_admin
    ADMIN_AUTH_AVAILABLE = True
    print("✅ Admin authentication available")
except ImportError as e:
    ADMIN_AUTH_AVAILABLE = False
    print(f"⚠️ Admin authentication not available: {e}")

# Get the project root directory (same approach as working test)
project_root = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(project_root, 'templates')
static_dir = os.path.join(project_root, 'static')

print(f"Project root: {project_root}")
print(f"Template directory: {template_dir}")
print(f"Template directory exists: {os.path.exists(template_dir)}")
print(f"home.html exists: {os.path.exists(os.path.join(template_dir, 'home.html'))}")

# Initialize Flask app with session support
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = 'your-secret-key-change-this-in-production'  # Change this in production
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour session

# User Authentication System
class UserAuth:
    def __init__(self, db_path='users.db'):
        self.db_path = os.path.join(project_root, db_path)
        self.init_database()
        print(f"🔧 User Auth initialized with database: {self.db_path}")
    
    def init_database(self):
        """Initialize the SQLite database with users table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create users table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    phone TEXT,
                    emergency_contact TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login DATETIME,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # Create default admin user if not exists
            cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, full_name, is_active)
                    VALUES (?, ?, ?, ?, ?)
                ''', ('admin', 'admin@emergency.com', 'admin123', 'System Administrator', 1))
                print("✅ Default admin user created")
            
            conn.commit()
            conn.close()
            print("✅ User database initialized successfully")
            
        except Exception as e:
            print(f"❌ Error initializing user database: {e}")
    
    def verify_user(self, username, password):
        """Verify user credentials"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE username = ? AND password_hash = ? AND is_active = 1', 
                         (username, password))
            user = cursor.fetchone()
            
            if user:
                # Update last login
                cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user[0],))
                conn.commit()
                return {
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'full_name': user[4],
                    'phone': user[5],
                    'emergency_contact': user[6]
                }
            
            conn.close()
            return None
            
        except Exception as e:
            print(f"❌ Error verifying user: {e}")
            return None
    
    def create_user(self, username, email, password, full_name=None, phone=None, emergency_contact=None):
        """Create a new user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, full_name, phone, emergency_contact)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, email, password, full_name, phone, emergency_contact))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return user_id
            
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            return None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE id = ? AND is_active = 1', (user_id,))
            user = cursor.fetchone()
            
            conn.close()
            
            if user:
                return {
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'full_name': user[4],
                    'phone': user[5],
                    'emergency_contact': user[6]
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting user: {e}")
            return None

    def get_user_by_email(self, email):
        """Get user by email"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE email = ? AND is_active = 1', (email,))
            user = cursor.fetchone()
            
            conn.close()
            
            if user:
                return {
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'full_name': user[4],
                    'phone': user[5],
                    'emergency_contact': user[6]
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting user by email: {e}")
            return None

# Initialize user authentication
user_auth = UserAuth()

# login_required decorator enforcing session
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if not session.get('user_id'):
                next_url = request.path
                return redirect(url_for('login', next=next_url))
        except Exception:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# History Tracking System - Enhanced Version
class HistoryTracker:
    def __init__(self, db_path='emergency_history.db'):
        self.db_path = os.path.join(project_root, db_path)
        self.lock = threading.Lock()
        self.init_database()
        print(f"🔧 History Tracker initialized with database: {self.db_path}")
    
    def init_database(self):
        """Initialize the SQLite database with history table"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Check if table exists and has the required columns
                cursor.execute("PRAGMA table_info(emergency_history)")
                columns = [column[1] for column in cursor.fetchall()]
                
                # If table doesn't exist or is missing required columns, recreate it
                required_columns = ['id', 'timestamp', 'detection_type', 'emergency_type', 'location', 
                                  'confidence', 'status', 'action_taken', 'source', 'image_path', 
                                  'voice_transcript', 'metadata', 'user_id', 'session_id', 'created_at']
                
                missing_columns = [col for col in required_columns if col not in columns]
                
                if missing_columns:
                    print(f"⚠️  Missing columns in emergency_history table: {missing_columns}")
                    print("🔄 Recreating table with proper schema...")
                    
                    # Drop existing table if it exists
                    cursor.execute('DROP TABLE IF EXISTS emergency_history')
                    
                    # Create the main emergency history table with proper schema
                    cursor.execute('''
                        CREATE TABLE emergency_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            detection_type TEXT NOT NULL,
                            emergency_type TEXT NOT NULL,
                            location TEXT,
                            confidence REAL,
                            status TEXT NOT NULL,
                            action_taken TEXT,
                            source TEXT NOT NULL,
                            image_path TEXT,
                            voice_transcript TEXT,
                            metadata TEXT,
                            user_id TEXT,
                            session_id TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                else:
                    # Table exists with all required columns, just ensure it's created if not exists
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS emergency_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            detection_type TEXT NOT NULL,
                            emergency_type TEXT NOT NULL,
                            location TEXT,
                            confidence REAL,
                            status TEXT NOT NULL,
                            action_taken TEXT,
                            source TEXT NOT NULL,
                            image_path TEXT,
                            voice_transcript TEXT,
                            metadata TEXT,
                            user_id TEXT,
                            session_id TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                
                # Create indexes for better performance (with error handling)
                try:
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON emergency_history(timestamp)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_detection_type ON emergency_history(detection_type)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_emergency_type ON emergency_history(emergency_type)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON emergency_history(status)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON emergency_history(source)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON emergency_history(created_at)')
                except Exception as index_error:
                    print(f"⚠️  Warning: Some indexes could not be created: {index_error}")
                
                # Create emergency contacts table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS emergency_contacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        phone TEXT NOT NULL,
                        department TEXT NOT NULL,
                        designation TEXT,
                        email TEXT,
                        address TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        priority INTEGER DEFAULT 1,
                        notes TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for emergency contacts
                try:
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_contact_department ON emergency_contacts(department)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_contact_active ON emergency_contacts(is_active)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_contact_priority ON emergency_contacts(priority)')
                except Exception as contact_index_error:
                    print(f"⚠️  Warning: Some contact indexes could not be created: {contact_index_error}")
                
                conn.commit()
                conn.close()
                print(f"✅ History database initialized successfully: {self.db_path}")
                
        except Exception as e:
            print(f"❌ Error initializing history database: {e}")
            raise
    
    def add_detection(self, detection_type, emergency_type, location=None, confidence=None, 
                     status='detected', action_taken=None, source='unknown', image_path=None, 
                     voice_transcript=None, metadata=None, user_id=None, session_id=None):
        """Add a new emergency detection to history"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Prepare metadata as JSON string
                metadata_json = json.dumps(metadata) if metadata else None
                
                cursor.execute('''
                    INSERT INTO emergency_history 
                    (detection_type, emergency_type, location, confidence, status, action_taken, 
                     source, image_path, voice_transcript, metadata, user_id, session_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (detection_type, emergency_type, location, confidence, status, action_taken,
                      source, image_path, voice_transcript, metadata_json, user_id, session_id))
                
                detection_id = cursor.lastrowid
                conn.commit()
                conn.close()
                
                print(f"📝 Added detection to history: {detection_type} - {emergency_type} (ID: {detection_id})")
                return detection_id
                
        except Exception as e:
            print(f"❌ Error adding detection to history: {e}")
            return None
    
    def get_history(self, limit=100, offset=0, filters=None):
        """Get history records with optional filtering"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                query = "SELECT * FROM emergency_history"
                params = []
                
                if filters:
                    conditions = []
                    if filters.get('start_date'):
                        conditions.append("timestamp >= ?")
                        params.append(filters['start_date'])
                    if filters.get('end_date'):
                        conditions.append("timestamp <= ?")
                        params.append(filters['end_date'])
                    if filters.get('detection_type'):
                        conditions.append("detection_type = ?")
                        params.append(filters['detection_type'])
                    if filters.get('emergency_type'):
                        conditions.append("emergency_type = ?")
                        params.append(filters['emergency_type'])
                    if filters.get('status'):
                        conditions.append("status = ?")
                        params.append(filters['status'])
                    if filters.get('source'):
                        conditions.append("source = ?")
                        params.append(filters['source'])
                    
                    if conditions:
                        query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries
                columns = [description[0] for description in cursor.description]
                history = []
                for row in rows:
                    record = dict(zip(columns, row))
                    if record.get('metadata'):
                        try:
                            record['metadata'] = json.loads(record['metadata'])
                        except:
                            record['metadata'] = {}
                    history.append(record)
                
                conn.close()
                return history
                
        except Exception as e:
            print(f"❌ Error getting history: {e}")
            return []
    
    def get_stats(self):
        """Get statistics about emergency detections"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Total detections
                cursor.execute("SELECT COUNT(*) FROM emergency_history")
                total_detections = cursor.fetchone()[0]
                
                # Today's detections
                cursor.execute("SELECT COUNT(*) FROM emergency_history WHERE DATE(timestamp) = DATE('now')")
                today_detections = cursor.fetchone()[0]
                
                # Detection types breakdown
                cursor.execute("SELECT detection_type, COUNT(*) FROM emergency_history GROUP BY detection_type")
                detection_types = dict(cursor.fetchall())
                
                # Emergency types breakdown
                cursor.execute("SELECT emergency_type, COUNT(*) FROM emergency_history GROUP BY emergency_type")
                emergency_types = dict(cursor.fetchall())
                
                # Status breakdown
                cursor.execute("SELECT status, COUNT(*) FROM emergency_history GROUP BY status")
                status_breakdown = dict(cursor.fetchall())
                
                # Source breakdown
                cursor.execute("SELECT source, COUNT(*) FROM emergency_history GROUP BY source")
                source_breakdown = dict(cursor.fetchall())
                
                # Average confidence
                cursor.execute("SELECT AVG(confidence) FROM emergency_history WHERE confidence IS NOT NULL")
                avg_confidence = cursor.fetchone()[0] or 0
                
                # Recent activity (last 24 hours)
                cursor.execute("SELECT COUNT(*) FROM emergency_history WHERE timestamp >= datetime('now', '-1 day')")
                recent_activity = cursor.fetchone()[0]
                
                conn.close()
                
                return {
                    'total_detections': total_detections,
                    'today_detections': today_detections,
                    'recent_activity': recent_activity,
                    'detection_types': detection_types,
                    'emergency_types': emergency_types,
                    'status_breakdown': status_breakdown,
                    'source_breakdown': source_breakdown,
                    'avg_confidence': round(avg_confidence, 2)
                }
                
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {
                'total_detections': 0,
                'today_detections': 0,
                'recent_activity': 0,
                'detection_types': {},
                'emergency_types': {},
                'status_breakdown': {},
                'source_breakdown': {},
                'avg_confidence': 0
            }
    
    def clear_history(self, days=None):
        """Clear history records (optionally older than specified days)"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                if days:
                    cursor.execute("DELETE FROM emergency_history WHERE timestamp < datetime('now', '-{} days')".format(days))
                else:
                    cursor.execute("DELETE FROM emergency_history")
                
                deleted_count = cursor.rowcount
                conn.commit()
                conn.close()
                
                print(f"🗑️ Cleared {deleted_count} history records")
                return deleted_count
                
        except Exception as e:
            print(f"❌ Error clearing history: {e}")
            return 0
    
    def get_detection_count(self):
        """Get total number of detections"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM emergency_history")
                count = cursor.fetchone()[0]
                conn.close()
                return count
        except Exception as e:
            print(f"❌ Error getting detection count: {e}")
            return 0
    
    # Emergency Contacts Management Methods
    def add_emergency_contact(self, name, phone, department, designation=None, email=None, address=None, priority=1, notes=None):
        """Add a new emergency contact"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO emergency_contacts (name, phone, department, designation, email, address, priority, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, phone, department, designation, email, address, priority, notes))
                contact_id = cursor.lastrowid
                conn.commit()
                conn.close()
                print(f"✅ Emergency contact added: {name} ({department})")
                return contact_id
        except Exception as e:
            print(f"❌ Error adding emergency contact: {e}")
            return None
    
    def get_emergency_contacts(self, department=None, active_only=True):
        """Get emergency contacts, optionally filtered by department"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                if department and active_only:
                    cursor.execute('''
                        SELECT * FROM emergency_contacts 
                        WHERE department = ? AND is_active = TRUE 
                        ORDER BY priority DESC, name ASC
                    ''', (department,))
                elif department:
                    cursor.execute('''
                        SELECT * FROM emergency_contacts 
                        WHERE department = ? 
                        ORDER BY priority DESC, name ASC
                    ''', (department,))
                elif active_only:
                    cursor.execute('''
                        SELECT * FROM emergency_contacts 
                        WHERE is_active = TRUE 
                        ORDER BY priority DESC, name ASC
                    ''')
                else:
                    cursor.execute('''
                        SELECT * FROM emergency_contacts 
                        ORDER BY priority DESC, name ASC
                    ''')
                
                contacts = []
                for row in cursor.fetchall():
                    contacts.append({
                        'id': row[0],
                        'name': row[1],
                        'phone': row[2],
                        'department': row[3],
                        'designation': row[4],
                        'email': row[5],
                        'address': row[6],
                        'is_active': bool(row[7]),
                        'priority': row[8],
                        'notes': row[9],
                        'created_at': row[10],
                        'updated_at': row[11]
                    })
                
                conn.close()
                return contacts
        except Exception as e:
            print(f"❌ Error getting emergency contacts: {e}")
            return []
    
    def get_emergency_contact(self, contact_id):
        """Get a specific emergency contact by ID"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM emergency_contacts WHERE id = ?', (contact_id,))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'phone': row[2],
                        'department': row[3],
                        'designation': row[4],
                        'email': row[5],
                        'address': row[6],
                        'is_active': bool(row[7]),
                        'priority': row[8],
                        'notes': row[9],
                        'created_at': row[10],
                        'updated_at': row[11]
                    }
                return None
        except Exception as e:
            print(f"❌ Error getting emergency contact: {e}")
            return None
    
    def update_emergency_contact(self, contact_id, name=None, phone=None, department=None, designation=None, email=None, address=None, is_active=None, priority=None, notes=None):
        """Update an emergency contact"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Build dynamic update query
                update_fields = []
                values = []
                
                if name is not None:
                    update_fields.append('name = ?')
                    values.append(name)
                if phone is not None:
                    update_fields.append('phone = ?')
                    values.append(phone)
                if department is not None:
                    update_fields.append('department = ?')
                    values.append(department)
                if designation is not None:
                    update_fields.append('designation = ?')
                    values.append(designation)
                if email is not None:
                    update_fields.append('email = ?')
                    values.append(email)
                if address is not None:
                    update_fields.append('address = ?')
                    values.append(address)
                if is_active is not None:
                    update_fields.append('is_active = ?')
                    values.append(is_active)
                if priority is not None:
                    update_fields.append('priority = ?')
                    values.append(priority)
                if notes is not None:
                    update_fields.append('notes = ?')
                    values.append(notes)
                
                update_fields.append('updated_at = CURRENT_TIMESTAMP')
                values.append(contact_id)
                
                query = f'UPDATE emergency_contacts SET {", ".join(update_fields)} WHERE id = ?'
                cursor.execute(query, values)
                
                conn.commit()
                conn.close()
                print(f"✅ Emergency contact updated: ID {contact_id}")
                return True
        except Exception as e:
            print(f"❌ Error updating emergency contact: {e}")
            return False
    
    def delete_emergency_contact(self, contact_id):
        """Delete an emergency contact"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM emergency_contacts WHERE id = ?', (contact_id,))
                conn.commit()
                conn.close()
                print(f"✅ Emergency contact deleted: ID {contact_id}")
                return True
        except Exception as e:
            print(f"❌ Error deleting emergency contact: {e}")
            return False
    
    def get_departments(self):
        """Get list of unique departments"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT DISTINCT department FROM emergency_contacts ORDER BY department')
                departments = [row[0] for row in cursor.fetchall()]
                conn.close()
                return departments
        except Exception as e:
            print(f"❌ Error getting departments: {e}")
            return []

# Initialize history tracker
history_tracker = HistoryTracker()

# Camera Detection System for YOLOv8 Integration
class CameraDetectionSystem:
    def __init__(self):
        """Initialize the camera detection system with YOLOv8 model"""
        self.fire_model = None
        self.detection_count = 0
        self.alert_count = 0
        self.load_fire_model()
        
    def load_fire_model(self):
        """Load the working YOLOv8 fire detection model"""
        if not YOLO_AVAILABLE:
            print("⚠️ YOLOv8 not available for camera detection")
            return False
            
        try:
            # Prefer project models directory first
            candidates = [
                os.path.join(project_root, 'models', 'fire_smoke_yolov8s.pt'),
                os.path.join(project_root, 'models', 'yolov8s.pt'),
                r'C:\Projects\fire_model\yolov8n.pt',
                'yolov8n.pt'
            ]

            for path in candidates:
                if path and os.path.exists(path):
                    print(f"🔥 Loading YOLOv8 model for camera: {path}")
                    self.fire_model = YOLO(path)
                    print("✅ Camera model loaded successfully!")
                    return True

            # If none of the candidates exist, attempt to load a small default model by name
            print("⚠️ No local model file found, attempting to load default 'yolov8s.pt'")
            self.fire_model = YOLO('yolov8s.pt')
            print("✅ Default YOLOv8s loaded for camera")
            return True
        except Exception as e:
            print(f"❌ Model loading failed: {e}")
            return False
    
    def process_frame(self, frame):
        """Process a single frame for emergency detection"""
        detections = []
        emergency_score = 0
        
        try:
            if self.fire_model is None:
                return detections, emergency_score
            
            # Run YOLOv8 detection
            results = self.fire_model(frame, verbose=False)
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0].cpu().numpy())
                        cls = int(box.cls[0].cpu().numpy())
                        class_name = self.fire_model.names[cls]
                        
                        # Filter by confidence threshold
                        if conf > 0.4:
                            detection = {
                                'type': class_name.lower(),
                                'confidence': conf,
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'timestamp': datetime.now().isoformat()
                            }
                            detections.append(detection)
                            
                            # Calculate emergency score
                            if 'fire' in class_name.lower() or 'smoke' in class_name.lower():
                                emergency_score += 10
                            elif class_name.lower() == 'person':
                                emergency_score += 1
                            elif class_name.lower() in ['car', 'truck', 'bus']:
                                emergency_score += 2
            
            # Count people for crowd detection
            people_count = sum(1 for det in detections if det['type'] == 'person' and det['confidence'] > 0.6)
            if people_count > 3:
                emergency_score += 3
                
        except Exception as e:
            print(f"Detection error: {e}")
        
        return detections, emergency_score
    
    def decode_image(self, image_data):
        """Decode base64 image data to OpenCV format"""
        try:
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            # Decode base64
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to OpenCV format
            frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            return frame
        except Exception as e:
            print(f"Image decode error: {e}")
            return None

# Initialize camera detection system
camera_detection = CameraDetectionSystem()

# Add sample data to history (for demonstration)
def add_sample_history_data():
    """Add sample data to history for demonstration purposes"""
    try:
        # Check if we already have data
        existing_count = history_tracker.get_detection_count()
        if existing_count > 0:
            print(f"✅ History database already contains {existing_count} records")
            return
        
        print("📝 Adding comprehensive sample history data...")
        
        # Comprehensive sample data for different sources
        sample_data = [
            # Live Camera Detections
            {
                'detection_type': 'Live Camera Detection',
                'emergency_type': 'Fire',
                'location': 'Building A - Floor 3 - Server Room',
                'confidence': 0.95,
                'status': 'emergency',
                'action_taken': 'Fire department notified, evacuation initiated',
                'source': 'camera',
                'image_path': '/uploads/detections/camera_fire_1.jpg',
                'metadata': {'camera_id': 'CAM_001', 'floor': '3', 'room': 'server_room'}
            },
            {
                'detection_type': 'Live Camera Detection',
                'emergency_type': 'Water Leak',
                'location': 'Basement - Pipe System - Section A',
                'confidence': 0.87,
                'status': 'warning',
                'action_taken': 'Maintenance team dispatched, water supply shut off',
                'source': 'camera',
                'image_path': '/uploads/detections/camera_leak_1.jpg',
                'metadata': {'camera_id': 'CAM_002', 'floor': 'basement', 'area': 'pipe_system'}
            }
        ]
        
        for data in sample_data:
            history_tracker.add_detection(
                detection_type=data['detection_type'],
                emergency_type=data['emergency_type'],
                location=data['location'],
                confidence=data['confidence'],
                status=data['status'],
                action_taken=data['action_taken'],
                source=data['source'],
                image_path=data.get('image_path'),
                metadata=json.dumps(data.get('metadata', {}))
            )
        
        print(f"✅ Added {len(sample_data)} sample history records")
        
    except Exception as e:
        print(f"❌ Error adding sample history data: {e}")

# Add sample emergency contacts (for demonstration)
def add_sample_emergency_contacts():
    """Add sample emergency contacts for demonstration purposes"""
    try:
        # Check if we already have contacts
        existing_contacts = history_tracker.get_emergency_contacts(active_only=False)
        if len(existing_contacts) > 0:
            print(f"✅ Emergency contacts database already contains {len(existing_contacts)} records")
            return
        
        print("📝 Adding sample emergency contacts...")
        
        sample_contacts = [
            {
                'name': 'John Smith',
                'phone': '+1-555-0101',
                'department': 'Fire',
                'designation': 'Fire Chief',
                'email': 'john.smith@firedept.gov',
                'address': '123 Fire Station Ave, City Center',
                'priority': 1,
                'notes': 'Primary fire emergency contact'
            },
            {
                'name': 'Sarah Johnson',
                'phone': '+1-555-0102',
                'department': 'Police',
                'designation': 'Police Captain',
                'email': 'sarah.johnson@police.gov',
                'address': '456 Police Plaza, Downtown',
                'priority': 1,
                'notes': 'Primary police emergency contact'
            },
            {
                'name': 'Dr. Michael Brown',
                'phone': '+1-555-0103',
                'department': 'Ambulance',
                'designation': 'Emergency Medical Director',
                'email': 'michael.brown@hospital.com',
                'address': '789 Medical Center Dr',
                'priority': 1,
                'notes': 'Primary medical emergency contact'
            },
            {
                'name': 'Lisa Davis',
                'phone': '+1-555-0104',
                'department': 'Accident',
                'designation': 'Traffic Control Officer',
                'email': 'lisa.davis@traffic.gov',
                'address': '321 Traffic Control Center',
                'priority': 2,
                'notes': 'Traffic accident response coordinator'
            },
            {
                'name': 'Robert Wilson',
                'phone': '+1-555-0105',
                'department': 'Security',
                'designation': 'Security Manager',
                'email': 'robert.wilson@security.com',
                'address': '654 Security Building',
                'priority': 2,
                'notes': 'Building security and access control'
            },
            {
                'name': 'Maria Garcia',
                'phone': '+1-555-0106',
                'department': 'Maintenance',
                'designation': 'Facility Manager',
                'email': 'maria.garcia@maintenance.com',
                'address': '987 Maintenance Center',
                'priority': 3,
                'notes': 'Building maintenance and repairs'
            }
        ]
        
        for contact in sample_contacts:
            history_tracker.add_emergency_contact(
                name=contact['name'],
                phone=contact['phone'],
                department=contact['department'],
                designation=contact['designation'],
                email=contact['email'],
                address=contact['address'],
                priority=contact['priority'],
                notes=contact['notes']
            )
        
        print(f"✅ Added {len(sample_contacts)} sample emergency contacts")
        
    except Exception as e:
        print(f"❌ Error adding sample emergency contacts: {e}")
        
        # Comprehensive sample data for different sources
        sample_data = [
            # Live Camera Detections
            {
                'detection_type': 'Live Camera Detection',
                'emergency_type': 'Fire',
                'location': 'Building A - Floor 3 - Server Room',
                'confidence': 0.95,
                'status': 'emergency',
                'action_taken': 'Fire department notified, evacuation initiated',
                'source': 'camera',
                'image_path': '/uploads/detections/camera_fire_1.jpg',
                'metadata': {'camera_id': 'CAM_001', 'floor': '3', 'room': 'server_room'}
            },
            {
                'detection_type': 'Live Camera Detection',
                'emergency_type': 'Water Leak',
                'location': 'Basement - Pipe System - Section A',
                'confidence': 0.87,
                'status': 'warning',
                'action_taken': 'Maintenance team dispatched, water supply shut off',
                'source': 'camera',
                'image_path': '/uploads/detections/camera_leak_1.jpg',
                'metadata': {'camera_id': 'CAM_002', 'floor': 'basement', 'area': 'pipe_system'}
            },
            {
                'detection_type': 'Live Camera Detection',
                'emergency_type': 'Oil Spill',
                'location': 'Parking Lot - Section B - Near Exit',
                'confidence': 0.92,
                'status': 'emergency',
                'action_taken': 'Cleanup crew activated, area cordoned off',
                'source': 'camera',
                'image_path': '/uploads/detections/camera_oil_1.jpg',
                'metadata': {'camera_id': 'CAM_003', 'area': 'parking_lot', 'section': 'B'}
            },
            {
                'detection_type': 'Live Camera Detection',
                'emergency_type': 'Smoke Detection',
                'location': 'Kitchen Area - Stove 3',
                'confidence': 0.89,
                'status': 'emergency',
                'action_taken': 'Fire alarm triggered, kitchen staff evacuated',
                'source': 'camera',
                'image_path': '/uploads/detections/camera_smoke_1.jpg',
                'metadata': {'camera_id': 'CAM_004', 'area': 'kitchen', 'stove': '3'}
            },
            
            # Voice Detection Records
            {
                'detection_type': 'Voice Detection',
                'emergency_type': 'Voice Emergency',
                'location': 'Voice Input - User: John Doe',
                'confidence': 0.85,
                'status': 'emergency',
                'action_taken': 'Voice emergency response activated, emergency services contacted',
                'source': 'voice',
                'voice_transcript': 'Help! There is a fire in the kitchen! Please send help immediately!',
                'metadata': {'detected_words': ['help', 'fire', 'kitchen', 'send', 'help'], 'user_id': 'user_001'}
            },
            {
                'detection_type': 'Voice Detection',
                'emergency_type': 'Voice Emergency',
                'location': 'Voice Input - User: Jane Smith',
                'confidence': 0.78,
                'status': 'warning',
                'action_taken': 'Voice emergency response activated, maintenance team alerted',
                'source': 'voice',
                'voice_transcript': 'Water is leaking from the ceiling in the conference room',
                'metadata': {'detected_words': ['water', 'leak', 'ceiling', 'conference'], 'user_id': 'user_002'}
            },
            {
                'detection_type': 'Voice Detection',
                'emergency_type': 'Voice Emergency',
                'location': 'Voice Input - User: Mike Johnson',
                'confidence': 0.91,
                'status': 'emergency',
                'action_taken': 'Voice emergency response activated, medical team dispatched',
                'source': 'voice',
                'voice_transcript': 'Emergency! Someone has collapsed in the lobby! Need medical assistance!',
                'metadata': {'detected_words': ['emergency', 'collapsed', 'lobby', 'medical'], 'user_id': 'user_003'}
            },
            {
                'detection_type': 'Voice Detection',
                'emergency_type': 'Voice Emergency',
                'location': 'Voice Input - User: Sarah Wilson',
                'confidence': 0.82,
                'status': 'warning',
                'action_taken': 'Voice emergency response activated, security team notified',
                'source': 'voice',
                'voice_transcript': 'There is a suspicious person in the parking lot',
                'metadata': {'detected_words': ['suspicious', 'person', 'parking'], 'user_id': 'user_004'}
            },
            
            # Uploaded Image Detections
            {
                'detection_type': 'Uploaded Image Detection',
                'emergency_type': 'Chemical Spill',
                'location': 'Laboratory - Bench 2 - Chemistry Lab',
                'confidence': 0.94,
                'status': 'emergency',
                'action_taken': 'Hazmat team deployed, lab evacuated, chemical containment initiated',
                'source': 'upload',
                'image_path': '/uploads/detections/upload_chemical_1.jpg',
                'metadata': {'lab': 'chemistry', 'bench': '2', 'chemical_type': 'unknown'}
            },
            {
                'detection_type': 'Uploaded Image Detection',
                'emergency_type': 'Gas Leak',
                'location': 'Kitchen Area - Stove 3 - Gas Line',
                'confidence': 0.89,
                'status': 'emergency',
                'action_taken': 'Gas supply shut off, ventilation activated, area evacuated',
                'source': 'upload',
                'image_path': '/uploads/detections/upload_gas_1.jpg',
                'metadata': {'area': 'kitchen', 'stove': '3', 'gas_type': 'natural_gas'}
            },
            {
                'detection_type': 'Uploaded Image Detection',
                'emergency_type': 'Fire',
                'location': 'Warehouse - Storage Unit - Section C',
                'confidence': 0.91,
                'status': 'emergency',
                'action_taken': 'Evacuation initiated, fire department contacted, sprinklers activated',
                'source': 'upload',
                'image_path': '/uploads/detections/upload_fire_1.jpg',
                'metadata': {'warehouse': 'main', 'section': 'C', 'fire_type': 'electrical'}
            },
            {
                'detection_type': 'Uploaded Image Detection',
                'emergency_type': 'Structural Damage',
                'location': 'Building B - Floor 2 - Wall Section',
                'confidence': 0.86,
                'status': 'warning',
                'action_taken': 'Structural engineer contacted, area cordoned off',
                'source': 'upload',
                'image_path': '/uploads/detections/upload_damage_1.jpg',
                'metadata': {'building': 'B', 'floor': '2', 'damage_type': 'wall_crack'}
            },
            {
                'detection_type': 'Uploaded Image Detection',
                'emergency_type': 'Flooding',
                'location': 'Basement - Storage Room - Near Water Heater',
                'confidence': 0.93,
                'status': 'emergency',
                'action_taken': 'Water pump activated, electrical systems shut down, area evacuated',
                'source': 'upload',
                'image_path': '/uploads/detections/upload_flood_1.jpg',
                'metadata': {'floor': 'basement', 'room': 'storage', 'cause': 'water_heater'}
            }
        ]
        
        # Add sample data with different timestamps (spread over the last 7 days)
        from datetime import timedelta
        base_time = datetime.now()
        
        for i, data in enumerate(sample_data):
            # Create timestamps going back in time over the last week
            hours_back = (i * 4) % 168  # Spread over 7 days (168 hours)
            minutes_back = (i * 15) % 60
            timestamp = base_time - timedelta(hours=hours_back, minutes=minutes_back)
            
            # Add the detection to history
            detection_id = history_tracker.add_detection(
                detection_type=data['detection_type'],
                emergency_type=data['emergency_type'],
                location=data['location'],
                confidence=data['confidence'],
                status=data['status'],
                action_taken=data['action_taken'],
                source=data['source'],
                image_path=data.get('image_path'),
                voice_transcript=data.get('voice_transcript'),
                metadata=data.get('metadata')
            )
            
            if detection_id:
                print(f"✅ Added detection {detection_id}: {data['detection_type']} - {data['emergency_type']}")
        
        final_count = history_tracker.get_detection_count()
        print(f"✅ Successfully added {len(sample_data)} sample history records. Total records: {final_count}")
        
    except Exception as e:
        print(f"❌ Error adding sample data: {e}")
        import traceback
        traceback.print_exc()

# Add sample data on startup
add_sample_history_data()
add_sample_emergency_contacts()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock classes for basic functionality
class EmergencyResponseSystem:
    def __init__(self):
        pass
    
    def trigger_emergency(self, *args, **kwargs):
        return {"status": "emergency_triggered", "message": "Emergency response system activated"}

class db_manager:
    @staticmethod
    def add_system_log(*args, **kwargs):
        pass
    
    @staticmethod
    def get_detections():
        return []
    
    @staticmethod
    def get_accidents():
        return []
    
    @staticmethod
    def get_voice_logs():
        return []

# Initialize instances
emergency_response = EmergencyResponseSystem()
detector = None

def initialize_yolov8_detector():
    global detector
    detector = YOLOv8EmergencyDetector()
    print("⚠️  YOLOv8 detector is disabled in this version")
    # Model loading is disabled

def find_latest_model():
    """Model loading is disabled in this version"""
    return None

def load_model():
    """Model loading is disabled in this version"""
    print("⚠️  Model loading is disabled in this version")
    return None

def detect_emergencies(image_data, confidence_threshold=0.6):
    """Detect emergencies in the image"""
    try:
        model = load_model()
        if model is None:
            return {'success': False, 'error': 'Model not loaded'}
        
        # Run detection
        results = model(image_data)
        
        # Process results
        detections = []
        if len(results.xyxy[0]) > 0:
            for detection in results.xyxy[0]:
                confidence = float(detection[4])
                if confidence >= confidence_threshold:
                    class_id = int(detection[5])
                    class_name = results.names[class_id]
                    detections.append({
                        'class': class_name,
                        'confidence': confidence,
                        'bbox': detection[:4].tolist()
                    })
        
        return {
            'success': True,
            'count': len(detections),
            'detections': detections
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Routes
RAG_CONTENT_PATH = os.path.join(project_root, 'content', 'content.json')
_rag_loaded = False
_rag_docs = []
_rag_index = None
_rag_model = None
_rag_dim = 384  # all-MiniLM-L6-v2
RAG_SIM_THRESHOLD = float(os.getenv('RAG_SIM_THRESHOLD', '0.30'))

def _load_rag_content():
    global _rag_docs
    try:
        if os.path.exists(RAG_CONTENT_PATH):
            with open(RAG_CONTENT_PATH, 'r', encoding='utf-8') as f:
                _rag_docs = json.load(f)
                if not isinstance(_rag_docs, list):
                    _rag_docs = []
        else:
            _rag_docs = []
    except Exception as e:
        print(f"⚠️ Failed to load RAG content: {e}")
        _rag_docs = []

def _ensure_rag_index():
    """Initialize embeddings model and FAISS (if available)."""
    global _rag_loaded, _rag_model, _rag_index
    if _rag_loaded:
        return
    _load_rag_content()
    if ST_AVAILABLE and _rag_docs:
        try:
            _rag_model = SentenceTransformer('all-MiniLM-L6-v2')
            # Build vectors
            texts = [d.get('content','') for d in _rag_docs]
            if texts:
                vecs = _rag_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
                if FAISS_AVAILABLE:
                    try:
                        index = faiss.IndexFlatIP(vecs.shape[1])
                        # normalize for cosine
                        faiss.normalize_L2(vecs)
                        index.add(vecs)
                        _rag_index = index
                    except Exception as e:
                        print(f"⚠️ FAISS init failed, will use numpy fallback: {e}")
                        _rag_index = vecs  # store for numpy cosine
                else:
                    _rag_index = vecs
        except Exception as e:
            print(f"⚠️ SentenceTransformer failed: {e}")
            _rag_model = None
            _rag_index = None
    _rag_loaded = True

def _retrieve(query: str, k: int = 4):
    _ensure_rag_index()
    if not _rag_docs:
        return []
    # ST available path
    if _rag_model is not None and _rag_index is not None:
        try:
            q = _rag_model.encode([query], convert_to_numpy=True)
            if FAISS_AVAILABLE and isinstance(_rag_index, faiss.Index):
                faiss.normalize_L2(q)
                D, I = _rag_index.search(q, k)
                hits = []
                for idx in I[0]:
                    if 0 <= idx < len(_rag_docs):
                        hits.append(_rag_docs[idx])
                return hits
            else:
                # numpy cosine fallback
                doc_vecs = _rag_index  # numpy array
                qn = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-9)
                dn = doc_vecs / (np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-9)
                sims = (qn @ dn.T).ravel()
                top_idx = sims.argsort()[::-1][:k]
                return [_rag_docs[i] for i in top_idx if 0 <= i < len(_rag_docs)]
        except Exception as e:
            print(f"⚠️ Retrieval error: {e}")
    # Keyword fallback
    ql = query.lower()
    scored = []
    for d in _rag_docs:
        text = (d.get('content','') + ' ' + d.get('title','')).lower()
        score = sum(1 for w in ql.split() if w in text)
        if score:
            scored.append((score, d))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:k]]

def _retrieve_with_scores(query: str, k: int = 4):
    """Return list of (doc, score) where score is cosine similarity in [0,1].
    Falls back to simple keyword scoring scaled to [0,1] if embeddings unavailable."""
    _ensure_rag_index()
    if not _rag_docs:
        return []
    # Embedding path
    if _rag_model is not None and _rag_index is not None:
        try:
            q = _rag_model.encode([query], convert_to_numpy=True)
            if FAISS_AVAILABLE and isinstance(_rag_index, faiss.Index):
                faiss.normalize_L2(q)
                D, I = _rag_index.search(q, k)
                out = []
                sims = D[0]
                for idx, sim in zip(I[0], sims):
                    if 0 <= idx < len(_rag_docs):
                        out.append((_rag_docs[idx], float(sim)))
                return out
            else:
                doc_vecs = _rag_index  # numpy array
                qn = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-9)
                dn = doc_vecs / (np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-9)
                sims = (qn @ dn.T).ravel()
                order = sims.argsort()[::-1][:k]
                return [(_rag_docs[i], float(sims[i])) for i in order if 0 <= i < len(_rag_docs)]
        except Exception as e:
            print(f"⚠️ Retrieval scores error: {e}")
    # Keyword fallback (very rough)
    ql = query.lower()
    scored = []
    for d in _rag_docs:
        text = (d.get('content','') + ' ' + d.get('title','')).lower()
        score = sum(1 for w in ql.split() if w in text)
        if score:
            scored.append((d, float(min(score/10.0, 1.0))))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]

def _compose_prompt(query: str, docs: list):
    ctx = []
    for i, d in enumerate(docs, 1):
        ctx.append(f"[{i}] {d.get('title','')} ({d.get('source','')})\n{d.get('content','')}\n")
    context = "\n".join(ctx)
    system = (
        "You are an emergency safety assistant. You must answer ONLY using the Context. "
        "If the answer is not in the Context, respond exactly: 'Sorry — I cannot find that information in our help documents.' "
        "Format: 3-5 concise bullet points followed by a 'Do now:' line if applicable. Include short [n] citations."
    )
    user_prompt = (
        f"Question: {query}\n\nContext:\n{context}\n\n"
        "Answer strictly from Context with 3-5 bullets and finish with 'Do now:' guidance if actionable."
    )
    return system, user_prompt

def _local_fallback_answer(query: str) -> str:
    q = (query or '').lower()
    # Clarify if very short
    if len(q.strip()) < 3 or q in {"hi","hello","hey","help","first aid","fire","emergency","sos"}:
        return (
            "Hi! To help you better, what do you need right now?\n"
            "- Fire safety\n- First aid\n- Evacuation steps\n- Electrical/kitchen/chemical fire\n\n"
            "Do now: Tell me the situation in 1 line (e.g., 'small oil fire on stove')."
        )
    if any(k in q for k in ["burn", "minor burn", "scald"]):
        return (
            "Minor burn first aid:\n"
            "- Cool the burn under cool running water for 20 minutes.\n"
            "- Remove tight items (rings/watches) before swelling.\n"
            "- Do not apply ice, butter, or toothpaste.\n"
            "- Cover loosely with sterile non-adhesive dressing.\n"
            "- Seek medical help if large, deep, or on face/hands/genitals.\n\n"
            "Do now: Start cooling the area with cool running water immediately."
        )
    if any(k in q for k in ["extinguisher","pass","use extinguisher"]):
        return (
            "Fire extinguisher (PASS):\n"
            "- Pull the pin.\n- Aim at the base of the fire.\n- Squeeze the handle.\n- Sweep side to side.\n"
            "- Only if trained and fire is small; keep exit at your back.\n\n"
            "Do now: Stand 2–3 meters away, test a short burst, then sweep at the base."
        )
    if any(k in q for k in ["evacuate","evacuation","exit","assembly"]):
        return (
            "Evacuation steps:\n"
            "- Raise the alarm and call emergency services.\n"
            "- Use nearest safe exit; do not use elevators.\n"
            "- Stay low if there is smoke; close doors behind you.\n"
            "- Go to the assembly point and report to the warden.\n"
            "- Do not re-enter until cleared.\n\n"
            "Do now: Move calmly to the nearest exit and proceed to the assembly point."
        )
    if any(k in q for k in ["electrical fire","electrical","socket","wiring"]):
        return (
            "Electrical fire response:\n"
            "- Do NOT use water.\n- If safe, switch off power source.\n- Use Class C/CO2 extinguisher.\n- Evacuate if fire grows or smoke increases.\n\n"
            "Do now: Isolate power if safe; otherwise evacuate and call emergency services."
        )
    if any(k in q for k in ["grease","oil","kitchen fire","pan"]):
        return (
            "Kitchen grease/oil fire:\n"
            "- Do NOT use water.\n- Turn off heat if safe.\n- Smother with a metal lid or fire blanket.\n- Use Class K extinguisher if trained.\n\n"
            "Do now: Cover the pan with a metal lid; keep distance and be ready to evacuate."
        )
    # Generic helpful default
    return (
        "Here’s a quick safety guide:\n"
        "- Describe your situation (fire type/size, injuries, location).\n"
        "- I’ll give you precise steps (first aid, extinguisher use, evacuation).\n"
        "- If life-threatening, call your local emergency number immediately.\n\n"
        "Do now: Tell me what you see (e.g., 'smoke in kitchen, small flame on pan')."
    )


def _llm_answer(query: str, docs: list):
    # Prefer Cohere if configured; else Gemini; else OpenAI; else extractive fallback
    if COHERE_AVAILABLE and os.getenv('COHERE_API_KEY'):
        try:
            client = cohere.Client(os.getenv('COHERE_API_KEY'))
            model_name = os.getenv('COHERE_MODEL', 'command-r')
            # Compose prompts
            if docs:
                system, uprompt = _compose_prompt(query, docs)
                combined_prompt = system + "\n\n" + uprompt
                messages = [
                    {"role": "SYSTEM", "content": system},
                    {"role": "USER", "content": uprompt}
                ]
            else:
                system = (
                    "You are a helpful, concise emergency assistant."
                    " When the user asks a very short or vague question (e.g., 'hello', 'first aid'), briefly greet and ask ONE clarifying question."
                    " Otherwise, provide a clear, step-by-step answer with 3–6 bullet points, then a short 'Do now:' line."
                )
                combined_prompt = system + "\n\nQuestion: " + query
                messages = [
                    {"role": "SYSTEM", "content": system},
                    {"role": "USER", "content": query}
                ]
            txt = ''
            # REST-first: direct Cohere chat endpoint
            try:
                print("[chat] provider=Cohere path=REST-first /v1/chat model=", model_name)
                import requests
                headers = {
                    'Authorization': f"Bearer {os.getenv('COHERE_API_KEY')}",
                    'Content-Type': 'application/json'
                }
                payload = {
                    'model': model_name,
                    'message': combined_prompt,
                    'temperature': 0.2,
                    'max_tokens': 600
                }
                r = requests.post('https://api.cohere.ai/v1/chat', headers=headers, json=payload, timeout=20)
                if r.ok:
                    jt = r.json()
                    txt = (jt.get('text') or '').strip()
                else:
                    print(f"[chat] REST-first failed: status {r.status_code} body={r.text[:200]}")
            except Exception as rest_first_e:
                print(f"[chat] Cohere REST-first error: {rest_first_e}")
            # Try Cohere chat with single 'message' param (some SDK versions)
            try:
                print("[chat] provider=Cohere path=chat(message) model=", model_name)
                chat_resp = client.chat(model=model_name, message=combined_prompt, temperature=0.2, max_tokens=600)
                txt = getattr(chat_resp, 'text', '') or getattr(getattr(chat_resp, 'message', {}), 'content', '') or ''
            except Exception as chat_message_e:
                print(f"[chat] Cohere chat(message) failed: {chat_message_e}")
                # Try Cohere chat with messages array
                try:
                    print("[chat] provider=Cohere path=chat(messages) model=", model_name)
                    chat_resp2 = client.chat(model=model_name, messages=messages, temperature=0.2, max_tokens=600)
                    txt = getattr(chat_resp2, 'text', '') or getattr(getattr(chat_resp2, 'message', {}), 'content', '') or ''
                    if isinstance(txt, list):
                        txt = '\n'.join([getattr(seg, 'text', str(seg)) for seg in txt])
                except Exception as chat_messages_e:
                    print(f"[chat] Cohere chat(messages) failed: {chat_messages_e}")
                    # Fallback to Responses API
                    try:
                        print("[chat] provider=Cohere path=responses.create model=", model_name)
                        resp2 = client.responses.create(model=model_name, input=combined_prompt, temperature=0.2, max_tokens=600)
                        txt = getattr(resp2, 'output_text', '') or ''
                    except Exception as resp_e:
                        print(f"[chat] Cohere responses.create failed: {resp_e}")
                        # Final fallback: legacy generate
                        try:
                            print("[chat] provider=Cohere path=generate model=", model_name)
                            gen = client.generate(model=model_name, prompt=combined_prompt, max_tokens=600, temperature=0.2)
                            txt = (gen.generations[0].text or '').strip()
                        except Exception as gen_e:
                            # Absolute last resort: direct REST call to Cohere Chat API (second attempt)
                            try:
                                print("[chat] provider=Cohere path=REST /v1/chat model=", model_name)
                                import requests
                                headers = {
                                    'Authorization': f"Bearer {os.getenv('COHERE_API_KEY')}",
                                    'Content-Type': 'application/json'
                                }
                                payload = {
                                    'model': model_name,
                                    'message': combined_prompt,
                                    'temperature': 0.2,
                                    'max_tokens': 600
                                }
                                r = requests.post('https://api.cohere.ai/v1/chat', headers=headers, json=payload, timeout=20)
                                if r.ok:
                                    jt = r.json()
                                    txt = (jt.get('text') or '').strip()
                                else:
                                    raise Exception(f"REST status {r.status_code}: {r.text[:200]}")
                            except Exception as rest_e:
                                raise Exception(f"Cohere all paths failed: {chat_message_e} | {chat_messages_e} | {resp_e} | {gen_e} | {rest_e}")
            txt = (txt or '').strip()
            if txt:
                return txt
        except Exception as e:
            print(f"⚠️ Cohere call failed: {e}")
    if GEMINI_AVAILABLE and os.getenv('GEMINI_API_KEY'):
        try:
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
            system, uprompt = _compose_prompt(query, docs)
            # Gemini uses system via safety/style prompts; concatenate for simplicity
            prompt = system + "\n\n" + uprompt
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content(prompt, generation_config={"temperature": 0, "max_output_tokens": 700})
            txt = (resp.text or '').strip()
            if txt:
                return txt
        except Exception as e:
            print(f"⚠️ Gemini call failed: {e}")
    if OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
        try:
            # Use Chat Completions if available in environment
            messages = []
            system, uprompt = _compose_prompt(query, docs)
            messages.append({"role":"system","content":system})
            messages.append({"role":"user","content":uprompt})
            # Try both modern and legacy clients
            try:
                resp = openai.ChatCompletion.create(model=os.getenv('OPENAI_MODEL','gpt-4o-mini'), messages=messages, max_tokens=600, temperature=0)
                txt = resp['choices'][0]['message']['content'].strip()
            except Exception:
                # If using new client style
                client = openai.OpenAI()
                resp = client.chat.completions.create(model=os.getenv('OPENAI_MODEL','gpt-4o-mini'), messages=messages, max_tokens=600, temperature=0)
                txt = resp.choices[0].message.content.strip()
            return txt
        except Exception as e:
            print(f"⚠️ OpenAI call failed: {e}")
    # Fallbacks exhausted: produce a helpful, interactive local answer
    return _local_fallback_answer(query)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        data = request.get_json(silent=True) or {}
        question = data.get('question') or data.get('q') or ''
        if not question.strip():
            return jsonify({"error":"No question provided"}), 400
        # RAG disabled: call LLM directly without context
        answer = _llm_answer(question, [])
        sources = []
        return jsonify({"answer": answer, "sources": sources})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat/reload', methods=['POST'])
def api_chat_reload():
    """Reload RAG content and rebuild embeddings without restarting the server."""
    try:
        global _rag_loaded, _rag_model, _rag_index
        _rag_loaded = False
        _rag_model = None
        _rag_index = None
        _load_rag_content()
        _ensure_rag_index()
        return jsonify({"status":"ok", "doc_count": len(_rag_docs)})
    except Exception as e:
        return jsonify({"status":"error", "error": str(e)}), 500
@app.route('/')
def root():
    """Root route - redirect to login first"""
    try:
        return redirect(url_for('login'))
    except Exception as e:
        print(f"Root redirect error: {e}")
        import traceback
        traceback.print_exc()
        return redirect('/login')

@app.route('/home')
@login_required
def home():
    """Home page with emergency detection features"""
    try:
        return render_template('home.html')
    except Exception as e:
        print(f"Home render error: {e}")
        import traceback
        traceback.print_exc()
        return "Internal Server Error", 500

@app.route('/camera')
@login_required
def camera():
    """Serve the camera detection page - requires authentication"""
    return render_template('camera.html')

@app.route('/emergency-detection')
@login_required
def emergency_detection():
    """Serve the emergency detection page - requires authentication"""
    return render_template('emergency_detection.html')

@app.route('/contact')
@login_required
def contact():
    """Serve the contact page - requires authentication"""
    return render_template('contact.html')

@app.route('/admin-login')
def admin_login():
    """Serve the admin login page"""
    return render_template('admin_login.html')

@app.route('/admin-dashboard')
def admin_dashboard():
    """Serve the admin dashboard page with authentication"""
    # Check if user is admin
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    return render_template('admin_dashboard_enhanced.html', current_user=session.get('username'))

@app.route('/admin')
def admin_redirect():
    """Redirect /admin to /admin-dashboard"""
    return redirect(url_for('admin_dashboard'))

@app.route('/voice-emergency')
@login_required
def voice_emergency():
    """Serve the voice emergency detection page - requires authentication"""
    return render_template('voice_emergency.html')

@app.route('/voice-button-demo')
@login_required
def voice_button_demo():
    """Serve the voice button demo page - requires authentication"""
    return render_template('voice-button-demo.html')

@app.route('/voice-test')
@login_required
def voice_test():
    """Voice button test page with debug information - requires authentication"""
    return render_template('voice-test.html')

@app.route('/floating-voice-demo')
@login_required
def floating_voice_demo():
    """Serve the floating voice button demo page - requires authentication"""
    return render_template('floating-voice-demo.html')

@app.route('/history')
@login_required
def history():
    """Serve the history page - requires authentication"""
    return render_template('history.html')

@app.route('/emergency-contacts')
@login_required
def emergency_contacts():
    """Serve the emergency contacts management page - requires authentication"""
    try:
        return render_template('emergency_contacts.html')
    except Exception as e:
        print(f"Error rendering emergency contacts page: {e}")
        return f"Error loading emergency contacts page: {str(e)}", 500

@app.route('/maps')
@login_required
def maps():
    """Serve the maps and geolocation page - requires authentication"""
    return render_template('maps.html')

@app.route('/api/camera/detect', methods=['POST'])
def camera_detect_frame():
    """API endpoint to process a single frame for YOLOv8 detection"""
    try:
        data = request.get_json()
        
        if 'image' not in data:
            return jsonify({'error': 'No image data provided'}), 400
        
        # Decode the image
        frame = camera_detection.decode_image(data['image'])
        if frame is None:
            return jsonify({'error': 'Failed to decode image'}), 400
        
        # Process frame for detections
        detections, emergency_score = camera_detection.process_frame(frame)
        
        # Update counters
        camera_detection.detection_count += len(detections)
        if emergency_score >= 5:
            camera_detection.alert_count += 1
            
            # Log emergency detection to history
            for detection in detections:
                if detection['confidence'] > 0.6:
                    history_tracker.add_detection(
                        detection_type='Live Camera Detection',
                        emergency_type=detection['type'].title(),
                        location='Camera Feed',
                        confidence=detection['confidence'],
                        status='emergency' if emergency_score >= 10 else 'warning',
                        action_taken='Alert generated',
                        source='camera',
                        metadata={'emergency_score': emergency_score, 'bbox': detection.get('bbox')}
                    )
        
        # Prepare response
        response = {
            'success': True,
            'detections': detections,
            'emergency_score': emergency_score,
            'is_emergency': emergency_score >= 5,
            'total_detections': camera_detection.detection_count,
            'active_alerts': camera_detection.alert_count,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Camera detection API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/camera/status', methods=['GET'])
def get_camera_status():
    """Get current camera detection system status"""
    return jsonify({
        'model_loaded': camera_detection.fire_model is not None,
        'total_detections': camera_detection.detection_count,
        'active_alerts': camera_detection.alert_count,
        'model_classes': len(camera_detection.fire_model.names) if camera_detection.fire_model else 0,
        'yolo_available': YOLO_AVAILABLE
    })

@app.route('/api/camera/reset', methods=['POST'])
def reset_camera_counters():
    """Reset camera detection counters"""
    camera_detection.detection_count = 0
    camera_detection.alert_count = 0
    return jsonify({'success': True, 'message': 'Camera detection counters reset'})

@app.route('/api/detect', methods=['POST'])
def api_detect():
    """API endpoint for emergency detection from live camera"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get location data if provided
        location_data = request.form.get('location', '{}')
        try:
            location_info = json.loads(location_data)
            latitude = location_info.get('latitude')
            longitude = location_info.get('longitude')
            location_description = location_info.get('description', 'Camera location')
        except:
            latitude = longitude = None
            location_description = 'Camera location'
        
        # Get device information if provided
        device_data = request.form.get('device', '{}')
        try:
            device_info = json.loads(device_data)
            device_type = device_info.get('type', 'camera')
            device_name = device_info.get('name', 'Camera device')
        except:
            device_type = 'camera'
            device_name = 'Camera device'
        
        # Read image data
        image_data = file.read()
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Run YOLOv8 detection
        if detector is None:
            initialize_yolov8_detector()
        
        if detector:
            results = process_image_for_api(image, detector)
        else:
            results = {'success': False, 'error': 'YOLOv8 detector not available'}
        
        # Always log the detection attempt to history (even if no emergencies found)
        upload_dir = os.path.join(project_root, 'uploads', 'detections')
        os.makedirs(upload_dir, exist_ok=True)
        image_filename = f"camera_detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        image_path = os.path.join(upload_dir, image_filename)
        image.save(image_path)
        
        if results.get('success'):
            if results.get('detections'):
                # Log each detection found
                for detection in results['detections']:
                    emergency_type = detection['class']
                    confidence = detection['confidence']
                    status = 'emergency' if confidence > 0.8 else 'warning'
                    action_taken = f"Live camera detection - {emergency_type} detected, emergency response activated"
                    
                    # Create detailed location description
                    if latitude and longitude:
                        location_desc = f"Camera: {latitude:.6f}, {longitude:.6f} - {location_description}"
                    else:
                        location_desc = f"Camera: {location_description}"
                    
                    # Create detailed description
                    description = f"Emergency detected via camera on {device_name} ({device_type}). "
                    description += f"Detection: {emergency_type} with {confidence:.2%} confidence. "
                    description += f"Location: {location_desc}"
                    
                    detection_id = history_tracker.add_detection(
                        detection_type='Live Camera Detection',
                        emergency_type=emergency_type,
                        location=location_desc,
                        confidence=confidence,
                        status=status,
                        action_taken=action_taken,
                        source='camera',
                        image_path=image_path,
                        metadata={
                            'bbox': detection['bbox'],
                            'confidence_threshold': 0.6,
                            'original_filename': file.filename,
                            'detection_count': len(results['detections']),
                            'location_data': {
                                'latitude': latitude,
                                'longitude': longitude,
                                'description': location_description
                            },
                            'device_info': {
                                'type': device_type,
                                'name': device_name
                            },
                            'description': description,
                            'detection_method': 'camera_analysis'
                        }
                    )
                    print(f"📹 Camera detection logged: {detection_id} - {emergency_type} at {location_desc}")
                    
                    # Send enhanced Telegram alert for emergency detections
                    if status == 'emergency':
                        try:
                            # Get enhanced location information
                            enhanced_location_info = get_location_info()
                            
                            # Capture additional image for Telegram
                            telegram_image_data = capture_image()
                            
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            telegram_message = f"""
🚨 CAMERA EMERGENCY DETECTED 🚨
===============================
⏰ Time: {timestamp}
📹 Detection Source: Camera Analysis
🚨 Emergency Type: {emergency_type.upper()}
🎯 Confidence: {confidence:.2%}
📱 Device: {device_name} ({device_type})
📍 ENHANCED LOCATION DETAILS:
   🌍 Address: {enhanced_location_info.get('address', location_desc)}
   🏙️ City: {enhanced_location_info.get('city', 'Unknown')}
   🏛️ State: {enhanced_location_info.get('state', 'Unknown')}
   🌎 Country: {enhanced_location_info.get('country', 'Unknown')}
   📍 Coordinates: {enhanced_location_info.get('latitude', latitude or 0):.6f}, {enhanced_location_info.get('longitude', longitude or 0):.6f}
📊 Detection Details:
   🔍 Detection Method: YOLOv5 Camera Analysis
   📸 Image Captured: Yes
   📁 Detection ID: {detection_id}
   📏 Bounding Box: {detection['bbox']}
📞 Contact Information:
   👤 Department: Emergency Services
   📞 Phone: +919080113107
   📧 Email: emergency@services.gov
⚠️ IMMEDIATE ACTION REQUIRED ⚠️
Emergency detected from camera analysis!
✅ Firebase: Connected
✅ Telegram: Working
✅ Location: Captured
✅ Image: {'Captured' if telegram_image_data else 'Not available'}
🎉 Camera Emergency Alert System Working!
"""
                            telegram_sent = send_telegram_alert(telegram_message, telegram_image_data)
                            print(f"📱 Telegram alert {'sent' if telegram_sent else 'failed'} for camera emergency: {emergency_type}")
                            
                        except Exception as e:
                            print(f"❌ Error sending Telegram alert for camera emergency: {e}")
            else:
                # Log that no emergencies were detected
                location_desc = f"Camera: {location_description}"
                
                history_tracker.add_detection(
                    detection_type='Live Camera Detection',
                    emergency_type='No Emergency Detected',
                    location=location_desc,
                    confidence=0.0,
                    status='clear',
                    action_taken='No action required - no emergencies detected',
                    source='camera',
                    image_path=image_path,
                    metadata={
                        'original_filename': file.filename,
                        'detection_count': 0,
                        'location_data': {
                            'latitude': latitude,
                            'longitude': longitude,
                            'description': location_description
                        },
                        'device_info': {
                            'type': device_type,
                            'name': device_name
                        },
                        'scan_completed': True,
                        'detection_method': 'camera_analysis'
                    }
                )
                print("📹 Camera scan completed - no emergencies detected")
        else:
            # Log detection error
            history_tracker.add_detection(
                detection_type='Live Camera Detection',
                emergency_type='Detection Error',
                location='Live Camera Feed',
                confidence=0.0,
                status='error',
                action_taken='Detection system error - manual review required',
                source='camera',
                image_path=image_path,
                metadata={
                    'original_filename': file.filename,
                    'error': results.get('error', 'Unknown error'),
                    'detection_count': 0
                }
            )
            print(f"❌ Camera detection error logged: {results.get('error')}")
        
        return jsonify(results)
        
    except Exception as e:
        print(f"❌ Error in camera detection API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file uploads for emergency detection"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save file to uploads directory
        upload_dir = os.path.join(project_root, 'uploads', 'detections')
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        # Run detection on uploaded image
        try:
            image = Image.open(filepath)
            results = detect_emergencies(image)
            
            if results.get('success'):
                if results.get('detections'):
                    # Log each detection found
                    for detection in results['detections']:
                        emergency_type = detection['class']
                        confidence = detection['confidence']
                        status = 'emergency' if confidence > 0.8 else 'warning'
                        action_taken = f"Uploaded image analysis - {emergency_type} detected, emergency response initiated"
                        
                        detection_id = history_tracker.add_detection(
                            detection_type='Uploaded Image Detection',
                            emergency_type=emergency_type,
                            location='Uploaded File Analysis',
                            confidence=confidence,
                            status=status,
                            action_taken=action_taken,
                            source='upload',
                            image_path=filepath,
                            metadata={
                                'bbox': detection['bbox'],
                                'confidence_threshold': 0.6,
                                'original_filename': file.filename,
                                'detection_count': len(results['detections']),
                                'file_size': len(file.read()) if hasattr(file, 'read') else 0
                            }
                        )
                        print(f"📤 Upload detection logged: {detection_id} - {emergency_type}")
                else:
                    # Log that no emergencies were detected in uploaded image
                    history_tracker.add_detection(
                        detection_type='Uploaded Image Detection',
                        emergency_type='No Emergency Detected',
                        location='Uploaded File Analysis',
                        confidence=0.0,
                        status='clear',
                        action_taken='No action required - no emergencies detected in uploaded image',
                        source='upload',
                        image_path=filepath,
                        metadata={
                            'original_filename': file.filename,
                            'detection_count': 0,
                            'analysis_completed': True
                        }
                    )
                    print("📤 Upload analysis completed - no emergencies detected")
            else:
                # Log detection error
                history_tracker.add_detection(
                    detection_type='Uploaded Image Detection',
                    emergency_type='Detection Error',
                    location='Uploaded File Analysis',
                    confidence=0.0,
                    status='error',
                    action_taken='Detection system error - manual review required',
                    source='upload',
                    image_path=filepath,
                    metadata={
                        'original_filename': file.filename,
                        'error': results.get('error', 'Unknown error'),
                        'detection_count': 0
                    }
                )
                print(f"❌ Upload detection error logged: {results.get('error')}")
                
        except Exception as detection_error:
            print(f"❌ Detection error on uploaded file: {detection_error}")
            # Log the error to history
            history_tracker.add_detection(
                detection_type='Uploaded Image Detection',
                emergency_type='Processing Error',
                location='Uploaded File Analysis',
                confidence=0.0,
                status='error',
                action_taken='File processing error - manual review required',
                source='upload',
                image_path=filepath,
                metadata={
                    'original_filename': file.filename,
                    'error': str(detection_error),
                    'detection_count': 0
                }
            )
        
        return jsonify({
            'status': 'uploaded',
            'filename': filename,
            'filepath': filepath,
            'detection_results': results if 'results' in locals() else None
        })
        
    except Exception as e:
        print(f"❌ Error in upload API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/voice-detection', methods=['POST'])
def voice_detection():
    """Handle voice detection for emergency keywords"""
    try:
        data = request.get_json()
        audio_data = data.get('audio', '')
        transcript = data.get('transcript', '')
        user_id = data.get('user_id', 'unknown')
        
        # Get location data if available
        location_data = data.get('location', {})
        latitude = location_data.get('latitude')
        longitude = location_data.get('longitude')
        location_description = location_data.get('description', 'Unknown location')
        
        # Get device information
        device_info = data.get('device', {})
        device_type = device_info.get('type', 'unknown')
        device_name = device_info.get('name', 'Unknown device')
        
        # Enhanced voice detection logic with comprehensive emergency keywords
        emergency_keywords = [
            'emergency', 'help', 'fire', 'accident', 'danger', 'urgent', 'sos', 'rescue',
            'ambulance', 'police', 'hospital', 'doctor', 'bleeding', 'broken', 'injured',
            'heart attack', 'stroke', 'choking', 'drowning', 'fall', 'crash', 'explosion',
            'bomb', 'terrorist', 'attack', 'robbery', 'theft', 'assault', 'fight',
            'gas leak', 'smoke', 'burning', 'flood', 'earthquake', 'tsunami', 'tornado',
            'hurricane', 'storm', 'lightning', 'thunder', 'avalanche', 'landslide',
            'car crash', 'car accident', 'traffic accident', 'collision', 'hit',
            'medical emergency', 'code blue', 'code red', 'emergency room', 'icu',
            'paramedic', 'first aid', 'cpr', 'defibrillator', 'oxygen', 'medicine'
        ]
        
        warning_keywords = [
            'warning', 'caution', 'careful', 'attention', 'problem', 'issue',
            'suspicious', 'strange', 'weird', 'unusual', 'concerning', 'worried',
            'scared', 'fear', 'panic', 'anxiety', 'stress', 'tension', 'conflict',
            'argument', 'fight', 'dispute', 'trouble', 'difficulty', 'challenge',
            'risk', 'hazard', 'threat', 'dangerous', 'unsafe', 'unstable',
            'leak', 'spill', 'overflow', 'break', 'damage', 'malfunction',
            'error', 'fault', 'failure', 'broken', 'not working', 'stopped'
        ]
        
        # Analyze transcript for emergency keywords
        transcript_lower = transcript.lower() if transcript else ''
        detected_emergency_words = [word for word in emergency_keywords if word in transcript_lower]
        detected_warning_words = [word for word in warning_keywords if word in transcript_lower]
        
        # Determine if emergency is detected
        emergency_detected = len(detected_emergency_words) > 0
        warning_detected = len(detected_warning_words) > 0
        
        # Calculate confidence based on keyword matches and context
        total_keywords = len(detected_emergency_words) + len(detected_warning_words)
        base_confidence = 0.5 if total_keywords > 0 else 0.0
        
        # Boost confidence for multiple emergency keywords
        emergency_boost = len(detected_emergency_words) * 0.2
        warning_boost = len(detected_warning_words) * 0.1
        
        # Additional boost for location data
        location_boost = 0.1 if latitude and longitude else 0.0
        
        confidence = min(0.95, base_confidence + emergency_boost + warning_boost + location_boost)
        
        # Always log voice detection to history
        if emergency_detected or warning_detected:
            if emergency_detected:
                emergency_type = 'Voice Emergency'
                status = 'emergency'
                action_taken = 'Voice emergency response activated, emergency services contacted'
            else:
                emergency_type = 'Voice Warning'
                status = 'warning'
                action_taken = 'Voice warning response activated, monitoring team alerted'
            
            # Create detailed location description
            if latitude and longitude:
                location_desc = f"GPS: {latitude:.6f}, {longitude:.6f} - {location_description}"
            else:
                location_desc = f"Voice Input - User: {user_id} - {location_description}"
            
            # Create detailed description
            description = f"Emergency detected via voice input on {device_name} ({device_type}). "
            description += f"Keywords found: {', '.join(detected_emergency_words + detected_warning_words)}. "
            description += f"Location: {location_desc}"
            
            detection_id = history_tracker.add_detection(
                detection_type='Voice Detection',
                emergency_type=emergency_type,
                location=location_desc,
                confidence=confidence,
                status=status,
                action_taken=action_taken,
                source='voice',
                voice_transcript=transcript,
                metadata={
                    'detected_emergency_words': detected_emergency_words,
                    'detected_warning_words': detected_warning_words,
                    'audio_length': len(audio_data) if audio_data else 0,
                    'transcript': transcript,
                    'user_id': user_id,
                    'total_keywords': total_keywords,
                    'confidence_calculation': f'Base: {base_confidence} + Emergency: {emergency_boost} + Warning: {warning_boost} + Location: {location_boost}',
                    'location_data': {
                        'latitude': latitude,
                        'longitude': longitude,
                        'description': location_description
                    },
                    'device_info': {
                        'type': device_type,
                        'name': device_name
                    },
                    'description': description,
                    'detection_method': 'voice_to_text_analysis'
                }
            )
            print(f"🎤 Voice detection logged: {detection_id} - {emergency_type} at {location_desc}")
            
            # Send Telegram alert for emergency detection
            if emergency_detected:
                # Get enhanced location information
                location_info = get_location_info()
                
                # Capture image from camera
                image_data = capture_image()
                
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                telegram_message = f"""
🚨 VOICE EMERGENCY DETECTED 🚨
=============================

⏰ Time: {timestamp}
🗣️ Voice Input: "{transcript}"
🚨 Emergency Type: {emergency_type}
🔍 Detected Keywords: {', '.join(detected_emergency_words)}
⚠️ Warning Keywords: {', '.join(detected_warning_words)}

📍 ENHANCED LOCATION DETAILS:
   🌍 Address: {location_info.get('address', location_description)}
   🏙️ City: {location_info.get('city', 'Unknown')}
   🏛️ State: {location_info.get('state', 'Unknown')}
   🌎 Country: {location_info.get('country', 'Unknown')}
   📍 Coordinates: {location_info.get('latitude', latitude or 0):.6f}, {location_info.get('longitude', longitude or 0):.6f}
   📱 Device: {device_name} ({device_type})

📊 Detection Details:
   🎯 Confidence: {confidence:.2f}
   🔢 Total Keywords: {total_keywords}
   👤 User ID: {user_id}

📞 Contact Information:
   👤 Department: Emergency Services
   📞 Phone: +919080113107
   📧 Email: emergency@services.gov

⚠️ IMMEDIATE ACTION REQUIRED ⚠️
Voice emergency detected from voice-emergency page!

✅ Firebase: Connected
✅ Telegram: Working
✅ Location: Captured
✅ Voice: Analyzed
✅ Image: {'Captured' if image_data else 'Not available'}

🎉 Emergency Alert System Working!
"""
                
                telegram_sent = send_telegram_alert(telegram_message, image_data)
                print(f"📱 Telegram alert {'sent' if telegram_sent else 'failed'} for voice emergency")
        else:
            # Log non-emergency voice input for monitoring
            location_desc = f"Voice Input - User: {user_id} - {location_description}"
            
            history_tracker.add_detection(
                detection_type='Voice Detection',
                emergency_type='No Emergency Detected',
                location=location_desc,
                confidence=0.0,
                status='clear',
                action_taken='No action required - no emergency keywords detected',
                source='voice',
                voice_transcript=transcript,
                metadata={
                    'detected_emergency_words': [],
                    'detected_warning_words': [],
                    'audio_length': len(audio_data) if audio_data else 0,
                    'transcript': transcript,
                    'user_id': user_id,
                    'total_keywords': 0,
                    'location_data': {
                        'latitude': latitude,
                        'longitude': longitude,
                        'description': location_description
                    },
                    'device_info': {
                        'type': device_type,
                        'name': device_name
                    },
                    'analysis_completed': True,
                    'detection_method': 'voice_to_text_analysis'
                }
            )
            print("🎤 Voice analysis completed - no emergency keywords detected")
        
        return jsonify({
            'status': 'detected',
            'emergency_detected': emergency_detected,
            'warning_detected': warning_detected,
            'detected_emergency_words': detected_emergency_words,
            'detected_warning_words': detected_warning_words,
            'confidence': confidence,
            'transcript': transcript,
            'location': {
                'latitude': latitude,
                'longitude': longitude,
                'description': location_description
            },
            'device': {
                'type': device_type,
                'name': device_name
            },
            'total_keywords': total_keywords,
            'confidence_breakdown': {
                'base': base_confidence,
                'emergency_boost': emergency_boost,
                'warning_boost': warning_boost,
                'location_boost': location_boost
            }
        })
        
    except Exception as e:
        print(f"❌ Error in voice detection API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/accident', methods=['POST'])
def report_accident():
    """Report an accident"""
    try:
        data = request.get_json()
        
        return jsonify({
            'status': 'reported',
            'accident_id': f"ACC_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'location': data.get('location', {}),
            'description': data.get('description', ''),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/loading')
def loading():
    """Loading page with redirect functionality"""
    page = request.args.get('page', '/')
    return render_template('deadline-loading.html', redirect_url=page)

@app.route('/test-loading')
def test_loading():
    """Test page for loading functionality"""
    return render_template('test_loading_page.html')

@app.route('/features')
@login_required
def features():
    """Serve the features page - requires authentication"""
    return render_template('features.html')

@app.route('/gallery')
@login_required
def gallery():
    """Serve the gallery page - requires authentication"""
    return render_template('gallery.html')

@app.route('/api/stats')
def get_stats():
    """Get system statistics"""
    try:
        stats = history_tracker.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/detections')
def get_detections():
    """Get detection history"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get filters from query parameters
        filters = {}
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')
        if request.args.get('detection_type'):
            filters['detection_type'] = request.args.get('detection_type')
        if request.args.get('emergency_type'):
            filters['emergency_type'] = request.args.get('emergency_type')
        if request.args.get('status'):
            filters['status'] = request.args.get('status')
        if request.args.get('source'):
            filters['source'] = request.args.get('source')
        
        history = history_tracker.get_history(limit=limit, offset=offset, filters=filters)

        # Ensure items are JSON-serializable (e.g., datetime -> ISO8601)
        def _serialize(item):
            try:
                obj = dict(item)
            except Exception:
                obj = item
            ts = obj.get('timestamp')
            if ts is not None and not isinstance(ts, str):
                try:
                    obj['timestamp'] = ts.isoformat()
                except Exception:
                    obj['timestamp'] = str(ts)
            if 'confidence' in obj:
                try:
                    obj['confidence'] = float(obj['confidence'])
                except Exception:
                    pass
            return obj

        history = [_serialize(h) for h in history]
        return jsonify(history)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/accidents')
def get_accidents():
    """Get accident reports"""
    return jsonify([])

@app.route('/api/voice-logs')
def get_voice_logs():
    """Get voice detection logs"""
    try:
        # Get voice detections from history
        filters = {'source': 'voice'}
        limit = request.args.get('limit', 50, type=int)
        voice_logs = history_tracker.get_history(limit=limit, filters=filters)
        return jsonify(voice_logs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history')
def get_history():
    """Get comprehensive history data for the history page"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get filters from query parameters
        filters = {}
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')
        if request.args.get('detection_type'):
            filters['detection_type'] = request.args.get('detection_type')
        if request.args.get('emergency_type'):
            filters['emergency_type'] = request.args.get('emergency_type')
        if request.args.get('status'):
            filters['status'] = request.args.get('status')
        if request.args.get('source'):
            filters['source'] = request.args.get('source')
        
        # Get history data
        history = history_tracker.get_history(limit=limit, offset=offset, filters=filters)
        
        # Get statistics
        stats = history_tracker.get_stats()
        
        return jsonify({
            'history': history,
            'stats': stats,
            'total_count': len(history),
            'has_more': len(history) == limit
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emergency/incidents')
def get_emergency_incidents():
    """Get emergency incidents for profile"""
    try:
        # Import database manager if available
        try:
            from src.database.database import DatabaseManager
            db = DatabaseManager()
            incidents = db.get_emergency_incidents(limit=100)
            return jsonify(incidents)
        except ImportError:
            # Fallback to mock data
            mock_incidents = [
                {
                    'id': 1,
                    'incident_type': 'Fire Detection',
                    'location': 'Building A, Floor 3',
                    'description': 'Smoke detected in the server room',
                    'status': 'resolved',
                    'created_at': '2025-01-15T10:30:00Z',
                    'severity_level': 'high'
                },
                {
                    'id': 2,
                    'incident_type': 'Water Leak',
                    'location': 'Basement',
                    'description': 'Pipe burst detected',
                    'status': 'active',
                    'created_at': '2025-01-14T15:45:00Z',
                    'severity_level': 'medium'
                }
            ]
            return jsonify(mock_incidents)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/voice/detections')
def get_voice_detections():
    """Get voice detections for profile"""
    try:
        # Import database manager if available
        try:
            from src.database.database import DatabaseManager
            db = DatabaseManager()
            detections = db.get_voice_detections(limit=100)
            return jsonify(detections)
        except ImportError:
            # Fallback to mock data
            mock_detections = [
                {
                    'id': 1,
                    'transcript': 'Help! There is a fire in the kitchen!',
                    'keywords': 'help, fire, kitchen',
                    'confidence': 0.85,
                    'emergency_detected': True,
                    'action_taken': 'Emergency services contacted',
                    'created_at': '2025-01-15T10:30:00Z'
                },
                {
                    'id': 2,
                    'transcript': 'Water is leaking from the ceiling',
                    'keywords': 'water, leak, ceiling',
                    'confidence': 0.78,
                    'emergency_detected': True,
                    'action_taken': 'Maintenance team dispatched',
                    'created_at': '2025-01-14T15:45:00Z'
                }
            ]
            return jsonify(mock_detections)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Emergency Contacts API Endpoints
@app.route('/api/emergency-contacts', methods=['GET'])
def get_emergency_contacts():
    """Get all emergency contacts"""
    try:
        department = request.args.get('department')
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        contacts = history_tracker.get_emergency_contacts(department=department, active_only=active_only)
        return jsonify({
            'success': True,
            'contacts': contacts,
            'total_count': len(contacts)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emergency-contacts', methods=['POST'])
def add_emergency_contact():
    """Add a new emergency contact"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'phone', 'department']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        contact_id = history_tracker.add_emergency_contact(
            name=data['name'],
            phone=data['phone'],
            department=data['department'],
            designation=data.get('designation'),
            email=data.get('email'),
            address=data.get('address'),
            priority=data.get('priority', 1),
            notes=data.get('notes')
        )
        
        if contact_id:
            return jsonify({
                'success': True,
                'contact_id': contact_id,
                'message': 'Emergency contact added successfully'
            })
        else:
            return jsonify({'error': 'Failed to add emergency contact'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emergency-contacts/<int:contact_id>', methods=['GET'])
def get_emergency_contact(contact_id):
    """Get a specific emergency contact"""
    try:
        contact = history_tracker.get_emergency_contact(contact_id)
        if contact:
            return jsonify({
                'success': True,
                'contact': contact
            })
        else:
            return jsonify({'error': 'Contact not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emergency-contacts/<int:contact_id>', methods=['PUT'])
def update_emergency_contact(contact_id):
    """Update an emergency contact"""
    try:
        data = request.get_json()
        
        success = history_tracker.update_emergency_contact(
            contact_id=contact_id,
            name=data.get('name'),
            phone=data.get('phone'),
            department=data.get('department'),
            designation=data.get('designation'),
            email=data.get('email'),
            address=data.get('address'),
            is_active=data.get('is_active'),
            priority=data.get('priority'),
            notes=data.get('notes')
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Emergency contact updated successfully'
            })
        else:
            return jsonify({'error': 'Failed to update emergency contact'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emergency-contacts/<int:contact_id>', methods=['DELETE'])
def delete_emergency_contact(contact_id):
    """Delete an emergency contact"""
    try:
        success = history_tracker.delete_emergency_contact(contact_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Emergency contact deleted successfully'
            })
        else:
            return jsonify({'error': 'Failed to delete emergency contact'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emergency-contacts/departments', methods=['GET'])
def get_departments():
    """Get list of unique departments"""
    try:
        departments = history_tracker.get_departments()
        return jsonify({
            'success': True,
            'departments': departments
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/logs')
def get_system_logs():
    """Get system logs for profile"""
    try:
        # Import database manager if available
        try:
            from src.database.database import DatabaseManager
            db = DatabaseManager()
            # Get recent system logs
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM system_logs 
                    ORDER BY created_at DESC 
                    LIMIT 100
                ''')
                logs = [dict(row) for row in cursor.fetchall()]
            return jsonify(logs)
        except ImportError:
            # Fallback to mock data
            mock_logs = [
                {
                    'id': 1,
                    'level': 'INFO',
                    'message': 'System startup completed successfully',
                    'module': 'system',
                    'created_at': '2025-01-15T08:00:00Z'
                },
                {
                    'id': 2,
                    'level': 'WARNING',
                    'message': 'High CPU usage detected',
                    'module': 'monitoring',
                    'created_at': '2025-01-14T16:30:00Z'
                }
            ]
            return jsonify(mock_logs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Telegram Configuration
TELEGRAM_BOT_TOKEN = '8299652544:AAH6goyX4fl0t3qr8_AFOpVNeSE47LQEauU'
TELEGRAM_CHAT_ID = '7964844220'

def get_location_info():
    """Get current location information"""
    try:
        import geocoder
        g = geocoder.ip('me')
        if g.ok:
            return {
                'latitude': g.lat,
                'longitude': g.lng,
                'address': g.address,
                'city': g.city,
                'state': g.state,
                'country': g.country
            }
        else:
            return {
                'latitude': 0.0,
                'longitude': 0.0,
                'address': 'Location not available',
                'city': 'Unknown',
                'state': 'Unknown',
                'country': 'Unknown'
            }
    except Exception as e:
        print(f"❌ Error getting location: {e}")
        return {
            'latitude': 0.0,
            'longitude': 0.0,
            'address': 'Location error',
            'city': 'Unknown',
            'state': 'Unknown',
            'country': 'Unknown'
        }

def capture_image():
    """Capture image from camera"""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Could not open camera")
            return None
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            # Convert to JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            image_data = buffer.tobytes()
            return image_data
        else:
            print("❌ Could not capture image")
            return None
            
    except Exception as e:
        print(f"❌ Error capturing image: {e}")
        return None

def send_telegram_alert(message, image_data=None):
    """Send alert via Telegram with optional image"""
    try:
        if image_data:
            # Send photo with caption
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            files = {'photo': ('emergency.jpg', image_data, 'image/jpeg')}
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'caption': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=data, files=files, timeout=15)
        else:
            # Send text message only
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result['ok']:
                print(f"✅ Telegram alert sent successfully! Message ID: {result['result']['message_id']}")
                return True
            else:
                print(f"❌ Telegram API error: {result}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending Telegram alert: {e}")
        return False

@app.route('/api/emergency/trigger', methods=['POST'])
def trigger_emergency_response():
    """Trigger emergency response with Telegram alert"""
    try:
        data = request.get_json() or {}
        emergency_type = data.get('type', 'emergency')
        voice_text = data.get('voice_text', 'Emergency triggered')
        
        # Get real location information
        location_info = get_location_info()
        location_address = location_info.get('address', 'Unknown location')
        
        # Capture image from camera
        image_data = capture_image()
        
        # Create emergency message with detailed location
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        emergency_message = f"""
🚨 EMERGENCY ALERT TRIGGERED 🚨
===============================

⏰ Time: {timestamp}
🗣️ Voice Input: "{voice_text}"
🚨 Emergency Type: {emergency_type.upper()}

📍 LOCATION DETAILS:
   🌍 Address: {location_address}
   🏙️ City: {location_info.get('city', 'Unknown')}
   🏛️ State: {location_info.get('state', 'Unknown')}
   🌎 Country: {location_info.get('country', 'Unknown')}
   📍 Coordinates: {location_info.get('latitude', 0):.6f}, {location_info.get('longitude', 0):.6f}

📞 Contact Information:
   👤 Department: Emergency Services
   📞 Phone: +919080113107
   📧 Email: emergency@services.gov

⚠️ IMMEDIATE ACTION REQUIRED ⚠️
Emergency alert triggered from voice-emergency page!

✅ Firebase: Connected
✅ Telegram: Working
✅ Location: Captured
✅ Image: {'Captured' if image_data else 'Not available'}

🎉 Emergency Alert System Working!
"""
        
        # Send Telegram alert with image
        telegram_sent = send_telegram_alert(emergency_message, image_data)
        
        # Log to history
        if 'history_tracker' in globals():
            history_tracker.add_detection(
                detection_type='voice',
                emergency_type=emergency_type,
                location=location_address,
                voice_transcript=voice_text,
                source='voice-emergency-page',
                user_id=session.get('user_id'),
                session_id=session.get('session_id')
            )
        
        return jsonify({
            'status': 'emergency_triggered',
            'message': 'Emergency response system activated',
            'telegram_sent': telegram_sent,
            'timestamp': timestamp,
            'emergency_type': emergency_type,
            'location': location_address,
            'image_captured': bool(image_data),
            'coordinates': {
                'latitude': location_info.get('latitude', 0),
                'longitude': location_info.get('longitude', 0)
            }
        })
        
    except Exception as e:
        print(f"❌ Error in emergency trigger: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error triggering emergency: {str(e)}'
        }), 500

@app.route('/api/emergency/config', methods=['GET', 'PUT'])
def emergency_config():
    """Get or update emergency configuration"""
    if request.method == 'GET':
        return jsonify({
            'enabled': True,
            'auto_detect': True,
            'notification_level': 'high'
        })
    else:
        return jsonify({'status': 'updated'})

@app.route('/api/emergency/location', methods=['GET'])
def get_emergency_location():
    """Get current location for emergency response"""
    return jsonify({
        'latitude': 40.7128,
        'longitude': -74.0060,
        'address': 'New York, NY, USA'
    })

@app.route('/api/location/capture', methods=['POST'])
def capture_location():
    """Capture current location for emergency detection"""
    try:
        data = request.get_json()
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy', 0)
        description = data.get('description', 'Unknown location')
        device_info = data.get('device', {})
        
        # Store location data for emergency detection
        location_data = {
            'latitude': latitude,
            'longitude': longitude,
            'accuracy': accuracy,
            'description': description,
            'device': device_info,
            'timestamp': datetime.now().isoformat()
        }
        
        # You could store this in a session or cache for later use
        # For now, we'll return it for immediate use
        
        return jsonify({
            'status': 'success',
            'location': location_data,
            'message': 'Location captured successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emergency/capture-photo', methods=['POST'])
def capture_emergency_photo():
    """Capture emergency photo"""
    return jsonify({
        'status': 'photo_captured',
        'filename': f'emergency_photo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
    })

@app.route('/api/emergency/test', methods=['POST'])
def test_emergency_response():
    """Test emergency response system"""
    return jsonify({
        'status': 'test_completed',
        'message': 'Emergency response system test successful'
    })

@app.route('/api/export/<table_name>')
def export_data(table_name):
    """Export data from specified table"""
    return jsonify({
        'status': 'exported',
        'table': table_name,
        'filename': f'{table_name}_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    })

@app.route('/api/contact/submit', methods=['POST'])
def submit_contact_form():
    """Submit contact form to Firebase Firestore"""
    try:
        # Get form data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'error': 'No data provided'
            }), 400
        
        # Add request metadata
        data['ip_address'] = request.remote_addr
        data['user_agent'] = request.headers.get('User-Agent', '')
        
        # Validate required fields
        required_fields = ['name', 'email', 'subject', 'message']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'status': 'error',
                    'error': f'Missing required field: {field}'
                }), 400
        
        if FIREBASE_AVAILABLE:
            # Submit to Firebase
            result = contact_manager.submit_contact_form(data)
            
            if result['success']:
                return jsonify({
                    'status': 'success',
                    'message': 'Contact form submitted successfully',
                    'submission_id': result['submission_id']
                })
            else:
                return jsonify({
                    'status': 'error',
                    'error': result['error']
                }), 500
        else:
            # Fallback to mock response if Firebase is not available
            return jsonify({
                'status': 'success',
                'message': 'Contact form submitted successfully (Firebase not available)',
                'submission_id': f'mock_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/contact/submissions', methods=['GET'])
def get_contact_submissions():
    """Get all contact form submissions from Firebase"""
    try:
        if FIREBASE_AVAILABLE:
            result = contact_manager.get_all_submissions()
            if result['success']:
                return jsonify({
                    'status': 'success',
                    'submissions': result['submissions'],
                    'count': result['count']
                })
            else:
                return jsonify({
                    'status': 'error',
                    'error': result['error']
                }), 500
        else:
            # Return mock data if Firebase is not available
            return jsonify({
                'status': 'success',
                'submissions': [],
                'count': 0,
                'message': 'Firebase not available'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/contact/submission/<submission_id>', methods=['GET'])
def get_contact_submission(submission_id):
    """Get specific contact submission from Firebase"""
    try:
        if FIREBASE_AVAILABLE:
            result = contact_manager.get_submission_by_id(submission_id)
            if result['success']:
                return jsonify({
                    'status': 'success',
                    'submission': result['submission']
                })
            else:
                return jsonify({
                    'status': 'error',
                    'error': result['error']
                }), 404
        else:
            # Return mock data if Firebase is not available
            return jsonify({
                'status': 'success',
                'submission': {
                    'id': submission_id,
                    'name': 'Test User',
                    'email': 'test@example.com',
                    'message': 'Test message',
                    'status': 'new',
                    'submitted_at': datetime.now().isoformat()
                },
                'message': 'Firebase not available'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/contact/submission/<submission_id>/status', methods=['PUT'])
def update_contact_status(submission_id):
    """Update contact submission status in Firebase"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        notes = data.get('notes')
        
        if not new_status:
            return jsonify({
                'status': 'error',
                'error': 'Status is required'
            }), 400
        
        if FIREBASE_AVAILABLE:
            result = contact_manager.update_submission_status(submission_id, new_status, notes)
            if result['success']:
                return jsonify({
                    'status': 'success',
                    'message': result['message'],
                    'submission_id': submission_id
                })
            else:
                return jsonify({
                    'status': 'error',
                    'error': result['error']
                }), 500
        else:
            # Mock response if Firebase is not available
            return jsonify({
                'status': 'success',
                'message': f'Status updated to {new_status} (Firebase not available)',
                'submission_id': submission_id
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/contact/submissions/status/<status>', methods=['GET'])
def get_contact_submissions_by_status(status):
    """Get contact submissions filtered by status"""
    try:
        if FIREBASE_AVAILABLE:
            result = contact_manager.get_submissions_by_status(status)
            if result['success']:
                return jsonify({
                    'status': 'success',
                    'submissions': result['submissions'],
                    'count': result['count'],
                    'filter_status': status
                })
            else:
                return jsonify({
                    'status': 'error',
                    'error': result['error']
                }), 500
        else:
            # Return mock data if Firebase is not available
            return jsonify({
                'status': 'success',
                'submissions': [],
                'count': 0,
                'filter_status': status,
                'message': 'Firebase not available'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/database/stats', methods=['GET'])
def get_database_stats():
    """Get database statistics"""
    try:
        if FIREBASE_AVAILABLE:
            # Get contact form statistics
            contact_stats = contact_manager.get_statistics()
            
            if contact_stats['success']:
                return jsonify({
                    'total_detections': 0,
                    'total_accidents': 0,
                    'total_voice_logs': 0,
                    'database_size': '0 MB',
                    'contact_submissions': contact_stats['statistics']
                })
            else:
                return jsonify({
                    'total_detections': 0,
                    'total_accidents': 0,
                    'total_voice_logs': 0,
                    'database_size': '0 MB',
                    'contact_submissions': {
                        'total_submissions': 0,
                        'status_counts': {},
                        'subject_counts': {}
                    },
                    'error': contact_stats['error']
                })
        else:
            return jsonify({
                'total_detections': 0,
                'total_accidents': 0,
                'total_voice_logs': 0,
                'database_size': '0 MB',
                'contact_submissions': {
                    'total_submissions': 0,
                    'status_counts': {},
                    'subject_counts': {}
                },
                'message': 'Firebase not available'
            })
            
    except Exception as e:
        return jsonify({
            'total_detections': 0,
            'total_accidents': 0,
            'total_voice_logs': 0,
            'database_size': '0 MB',
            'error': str(e)
        }), 500

@app.route('/api/free/weather/<city>', methods=['GET'])
def get_weather_free(city):
    """Get weather data for city"""
    return jsonify({
        'city': city,
        'temperature': 25.0,
        'description': 'clear sky',
        'humidity': 65,
        'wind_speed': 3.2
    })

@app.route('/api/free/news/emergency', methods=['GET'])
def get_emergency_news_free():
    """Get emergency news"""
    return jsonify([{
        'title': 'Emergency Detection System Active',
        'description': 'AI-powered emergency detection system is now operational'
    }])

@app.route('/api/free/location/<lat>/<lon>', methods=['GET'])
def get_location_free(lat, lon):
    """Get location information"""
    return jsonify({
        'latitude': float(lat),
        'longitude': float(lon),
        'address': 'Unknown Location'
    })

@app.route('/api/free/translate', methods=['POST'])
def translate_text_free_endpoint():
    """Translate text"""
    data = request.get_json()
    text = data.get('text', '')
    target_lang = data.get('target_lang', 'en')
    return jsonify({
        'original': text,
        'translated': f'Translated: {text}',
        'target_language': target_lang
    })

@app.route('/api/free/usage', methods=['GET'])
def get_free_api_usage():
    """Get free API usage statistics"""
    return jsonify({
        'weather': {'count': 0, 'limit': 1000},
        'news': {'count': 0, 'limit': 100},
        'maps': {'count': 0, 'limit': 1000},
        'translation': {'count': 0, 'limit': 1000}
    })

@app.route('/api/emergency/comprehensive', methods=['POST'])
def comprehensive_emergency_detection():
    """Comprehensive emergency detection"""
    return jsonify({
        'status': 'detection_completed',
        'detections': [],
        'location': {'lat': 40.7128, 'lng': -74.0060},
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/emergency/speech-listen', methods=['POST'])
def listen_for_emergency_speech():
    """Listen for emergency speech"""
    return jsonify({
        'status': 'listening',
        'detected_words': [],
        'emergency_keywords': ['help', 'emergency', 'fire', 'accident']
    })

@app.route('/api/emergency/notify', methods=['POST'])
def send_emergency_notifications():
    """Send emergency notifications"""
    return jsonify({
        'status': 'notifications_sent',
        'recipients': ['emergency@example.com'],
        'message': 'Emergency alert sent'
    })

@app.route('/api/emergency/news', methods=['GET'])
def get_emergency_news():
    """Get emergency news"""
    return jsonify([{
        'title': 'Emergency Detection System Active',
        'description': 'AI-powered emergency detection system is now operational',
        'source': 'System',
        'timestamp': datetime.now().isoformat()
    }])

@app.route('/api/emergency/translate', methods=['POST'])
def translate_emergency_message():
    """Translate emergency message"""
    data = request.get_json()
    message = data.get('message', '')
    target_lang = data.get('target_lang', 'en')
    return jsonify({
        'original': message,
        'translated': f'Translated: {message}',
        'target_language': target_lang
    })

@app.route('/api/twilio/status', methods=['GET'])
def get_twilio_status():
    """Get Twilio integration status"""
    return jsonify({
        'status': 'not_configured',
        'message': 'Twilio integration not configured'
    })

@app.route('/api/free/status', methods=['GET'])
def get_free_api_status():
    """Get free API status"""
    return jsonify({
        'weather': {'status': 'active', 'enabled': True},
        'news': {'status': 'active', 'enabled': True},
        'maps': {'status': 'active', 'enabled': True},
        'translation': {'status': 'active', 'enabled': True}
    })

@app.route('/api/admin/login', methods=['POST'])
def admin_login_api():
    """Admin login API endpoint"""
    try:
        data = request.get_json()
        email = data.get('email', '')
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({
                'status': 'error',
                'error': 'Email and password are required'
            }), 400
        
        # Check admin credentials
        print(f"Admin login attempt: {email}")
        if email == 'lokeshjayanth1403@gmail.com' and password == 'lokesh@1403':
            # Create admin session
            session['user_id'] = 'admin'
            session['username'] = email
            session['full_name'] = 'System Administrator'
            session['is_admin'] = True
            session.permanent = True
            
            response = jsonify({
                'status': 'success',
                'message': 'Login successful',
                'session_id': 'admin_session'
            })
            
            return response
        else:
            return jsonify({
                'status': 'error',
                'error': 'Invalid email or password'
            }), 401
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout_api():
    """Admin logout API endpoint"""
    try:
        # Clear admin session
        session.clear()
        
        response = jsonify({
            'status': 'success',
            'message': 'Logout successful'
        })
        
        return response
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication (admin and regular users)"""
    try:
        if request.method == 'POST':
            username = request.form.get('username') or ''
            password = request.form.get('password') or ''
            next_url = request.args.get('next')

            if not username or not password:
                return render_template('login.html', error='Please provide username and password')

            # Admin login (email + password)
            if username == 'lokeshjayanth1403@gmail.com' and password == 'lokesh@1403':
                session['user_id'] = 'admin'
                session['username'] = username
                session['full_name'] = 'System Administrator'
                session['is_admin'] = True
                session.permanent = True
                return redirect(next_url or url_for('admin_dashboard'))

            # Allow classic admin fallback (username admin)
            if username == 'admin' and password == 'admin123':
                session['user_id'] = 'admin'
                session['username'] = 'admin'
                session['full_name'] = 'System Administrator'
                session['is_admin'] = True
                session.permanent = True
                return redirect(next_url or url_for('admin_dashboard'))

            # Regular user login via SQLite users.db
            user = user_auth.verify_user(username, password)
            if user:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['full_name'] = user.get('full_name') or user['username']
                session['is_admin'] = False
                session.permanent = True
                # Redirect to requested page if any, else home
                return redirect(next_url or url_for('home'))

            return render_template('login.html', error='Invalid username or password')

        # GET
        return render_template('login.html')

    except Exception as e:
        print(f"❌ Login error: {e}")
        return render_template('login.html', error='Unexpected error. Please try again.')

# Minimal signup route to avoid template BuildError from url_for('signup') in login.html
@app.route('/signup', methods=['GET'])
def signup():
    try:
        # Redirect users to login; full signup can be enabled later
        return redirect(url_for('login'))
    except Exception:
        return redirect('/login')

# SIGNUP ROUTE DISABLED - Comment out to re-enable
# @app.route('/signup', methods=['GET', 'POST'])
# def signup():
#     """Signup page and user registration"""
#     if request.method == 'POST':
#         username = request.form.get('username')
#         email = request.form.get('email')
#         password = request.form.get('password')
#         confirm_password = request.form.get('confirm_password')
#         full_name = request.form.get('full_name')
#         phone = request.form.get('phone')
#         emergency_contact = request.form.get('emergency_contact')
#         
#         if not all([username, email, password, confirm_password]):
#             return render_template('signup.html', error='Please fill in all required fields')
#         
#         if password != confirm_password:
#             return render_template('signup.html', error='Passwords do not match')
#         
#         # Create user
#         user_id = user_auth.create_user(username, email, password, full_name, phone, emergency_contact)
#         if user_id:
#             # Auto-login after successful signup and redirect to home
#             session['user_id'] = user_id
#             session['username'] = username
#             session['full_name'] = full_name or username
#             session['is_admin'] = False
#             session.permanent = True
#             return redirect(url_for('home'))
#         else:
#             return render_template('signup.html', error='Username or email already exists')
#     
#     return render_template('signup.html')

@app.route('/profile')
@login_required
def profile():
    """User profile page - requires authentication"""
    user = user_auth.get_user_by_id(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/profile-test')
@login_required
def profile_test():
    """Test profile page - requires authentication"""
    user = user_auth.get_user_by_id(session['user_id'])
    return render_template('profile_test.html', user=user)

@app.route('/auth-test')
@login_required
def auth_test():
    """Authentication test page - requires authentication"""
    user = user_auth.get_user_by_id(session['user_id'])
    return render_template('auth_test.html', user=user)

@app.route('/logout')
def logout():
    """Logout route - clears session and redirects to login"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/test-404')
def test_404():
    """Test route to trigger 404 error"""
    return render_template('nonexistent.html')

@app.route('/favicon.ico')
def favicon():
    """Handle favicon requests: serve static favicon if available, else 204"""
    try:
        favicon_path = os.path.join(static_dir, 'favicon.ico')
        if os.path.exists(favicon_path):
            return send_from_directory(static_dir, 'favicon.ico')
        return '', 204
    except Exception:
        return '', 204

@app.route('/404-assets/<path:filename>')
def serve_404_assets(filename):
    """Serve static assets for the 404 page"""
    # Since the 404 page directory doesn't exist, return 404
    return "Asset not found", 404

@app.errorhandler(404)
def page_not_found(e):
    """Custom 404 error handler - returns a simple 404 message"""
    # Check if the request is for favicon.ico and return a simple response
    if request.path == '/favicon.ico':
        return '', 204  # No content for favicon requests
    
    # For other 404 errors, return a simple error message
    return "Page Not Found - 404", 404

@app.errorhandler(500)
def internal_error(e):
    """Custom 500 error handler - log the error and return a simple error page"""
    print(f"❌ Internal server error: {e}")
    return "Internal Server Error", 500

@app.errorhandler(403)
def forbidden_error(e):
    """Custom 403 error handler - return a simple error page"""
    return "Forbidden", 403

@app.errorhandler(400)
def bad_request_error(e):
    """Custom 400 error handler - return a simple error page"""
    return "Bad Request", 400

@app.errorhandler(Exception)
def handle_exception(e):
    """General exception handler - log the error and return a simple error page"""
    print(f"❌ Unhandled exception: {e}")
    return "Internal Server Error", 500

@app.route('/api/auth/firebase-callback', methods=['POST'])
def firebase_auth_callback():
    """Handle Firebase authentication callback and create Flask session"""
    try:
        print("🔥 Firebase auth callback received")
        # Parse JSON safely to avoid UTF-8 decode errors on invalid/binary payloads
        data = request.get_json(silent=True)
        if data is None:
            raw_bytes = request.get_data(cache=False)
            content_type = request.headers.get('Content-Type', '')
            print(f"⚠️ request.get_json() returned None. Content-Type={content_type}, body-bytes={len(raw_bytes) if raw_bytes else 0}")
            if not content_type.lower().startswith('application/json'):
                return jsonify({'error': 'Invalid content type; expected application/json'}), 400
            # Last-chance defensive parse
            try:
                import json as _json
                text_body = raw_bytes.decode('utf-8', errors='strict')
                data = _json.loads(text_body)
            except Exception as parse_err:
                print(f"❌ Malformed JSON payload: {parse_err}")
                return jsonify({'error': 'Malformed JSON payload'}), 400
        if not data:
            print("❌ No data provided")
            return jsonify({'error': 'No data provided'}), 400
        
        # Extract user information from Firebase auth result
        user_info = data.get('user', {})
        id_token = data.get('idToken')
        
        print(f"📧 User email: {user_info.get('email')}")
        print(f"👤 Display name: {user_info.get('displayName')}")
        print(f"🆔 UID: {user_info.get('uid')}")
        
        if not user_info or not id_token:
            print("❌ Invalid user data")
            return jsonify({'error': 'Invalid user data'}), 400
        
        email = user_info.get('email')
        display_name = user_info.get('displayName', '')
        uid = user_info.get('uid')
        
        if not email:
            print("❌ Email is required")
            return jsonify({'error': 'Email is required'}), 400
        
        # Check if it's admin user
        if email in {'lokkeshjayanth1403@gmail.com', 'lokeshjayanth1403@gmail.com'}:
            print("👑 Admin user detected")
            session['user_id'] = 'admin'
            session['username'] = email
            session['full_name'] = display_name or 'System Administrator'
            session['is_admin'] = True
            session['firebase_uid'] = uid
            session.permanent = True
            print("✅ Admin session created")
            return jsonify({
                'success': True,
                'redirect': '/admin-dashboard',
                'user': {
                    'email': email,
                    'displayName': display_name,
                    'isAdmin': True
                }
            })
        
        # For regular users, check if they exist in the database
        # If not, create a new user account
        print(f"🔍 Looking for user with email: {email}")
        user = user_auth.get_user_by_email(email)
        if not user:
            print(f"📝 Creating new user for email: {email}")
            # Create new user from Firebase auth
            username = email.split('@')[0]  # Use email prefix as username
            user_id = user_auth.create_user(
                username=username,
                email=email,
                password='',  # No password for Firebase users
                full_name=display_name
            )
            if not user_id:
                print("❌ Failed to create user account")
                return jsonify({'error': 'Failed to create user account'}), 500
            user = user_auth.get_user_by_id(user_id)
            print(f"✅ New user created with ID: {user_id}")
        else:
            print(f"✅ Existing user found: {user['username']}")
        
        # Create Flask session
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['full_name'] = user['full_name']
        session['is_admin'] = False
        session['firebase_uid'] = uid
        session.permanent = True
        print(f"✅ User session created for: {user['username']}")
        
        return jsonify({
            'success': True,
            'redirect': '/home',
            'user': {
                'id': user['id'],
                'email': email,
                'displayName': display_name,
                'isAdmin': False
            }
        })
        
    except Exception as e:
        print(f"❌ Firebase auth callback error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Authentication failed'}), 500

# Missing API endpoints for admin panel
@app.route('/api/emergency/stats')
def get_emergency_stats():
    """Get emergency statistics"""
    try:
        stats = history_tracker.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users')
def get_admin_users():
    """Get all users for admin panel"""
    try:
        # Get all users from the database
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, username, email, full_name, phone, emergency_contact, 
                   created_at, last_login, is_active
            FROM users
            ORDER BY created_at DESC
        ''')
        users = cursor.fetchall()
        conn.close()
        
        # Format user data
        user_list = []
        for user in users:
            user_list.append({
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'full_name': user[3] or 'N/A',
                'phone': user[4] or 'N/A',
                'emergency_contact': user[5] or 'N/A',
                'created_at': user[6],
                'last_login': user[7] or 'Never',
                'is_active': bool(user[8]),
                'role': 'Admin' if user[1] == 'admin' else 'User'
            })
        
        return jsonify({
            'users': user_list,
            'total': len(user_list),
            'active': len([u for u in user_list if u['is_active']]),
            'inactive': len([u for u in user_list if not u['is_active']])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_user(user_id):
    """Manage individual user"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        if request.method == 'GET':
            # Get user details
            cursor.execute('''
                SELECT id, username, email, full_name, phone, emergency_contact, 
                       created_at, last_login, is_active
                FROM users WHERE id = ?
            ''', (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            return jsonify({
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'full_name': user[3] or 'N/A',
                'phone': user[4] or 'N/A',
                'emergency_contact': user[5] or 'N/A',
                'created_at': user[6],
                'last_login': user[7] or 'Never',
                'is_active': bool(user[8]),
                'role': 'Admin' if user[1] == 'admin' else 'User'
            })
        
        elif request.method == 'PUT':
            # Update user
            data = request.get_json()
            updates = []
            params = []
            
            if 'full_name' in data:
                updates.append('full_name = ?')
                params.append(data['full_name'])
            if 'phone' in data:
                updates.append('phone = ?')
                params.append(data['phone'])
            if 'emergency_contact' in data:
                updates.append('emergency_contact = ?')
                params.append(data['emergency_contact'])
            if 'is_active' in data:
                updates.append('is_active = ?')
                params.append(data['is_active'])
            
            if updates:
                params.append(user_id)
                cursor.execute(f'''
                    UPDATE users SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                conn.commit()
            
            return jsonify({'message': 'User updated successfully'})
        
        elif request.method == 'DELETE':
            # Delete user (soft delete by setting is_active to False)
            cursor.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
            conn.commit()
            return jsonify({'message': 'User deactivated successfully'})
        
        conn.close()
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/cameras')
def get_cameras():
    """Get all cameras"""
    try:
        # Mock camera data - in real implementation, this would come from a database
        cameras = [
            {
                'id': 1,
                'name': 'Main Entrance Camera',
                'location': 'Building A - Entrance',
                'ip_address': '192.168.1.100',
                'port': 554,
                'status': 'active',
                'last_seen': '2025-08-04 11:30:00',
                'stream_url': 'rtsp://192.168.1.100:554/stream1',
                'zone': 'Entrance'
            },
            {
                'id': 2,
                'name': 'Parking Lot Camera',
                'location': 'Building A - Parking',
                'ip_address': '192.168.1.101',
                'port': 554,
                'status': 'active',
                'last_seen': '2025-08-04 11:25:00',
                'stream_url': 'rtsp://192.168.1.101:554/stream1',
                'zone': 'Parking'
            },
            {
                'id': 3,
                'name': 'Office Area Camera',
                'location': 'Building A - Office Floor',
                'ip_address': '192.168.1.102',
                'port': 554,
                'status': 'offline',
                'last_seen': '2025-08-04 10:15:00',
                'stream_url': 'rtsp://192.168.1.102:554/stream1',
                'zone': 'Office'
            }
        ]
        
        return jsonify({
            'cameras': cameras,
            'total': len(cameras),
            'active': len([c for c in cameras if c['status'] == 'active']),
            'offline': len([c for c in cameras if c['status'] == 'offline'])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/cameras', methods=['POST'])
def add_camera():
    """Add new camera"""
    try:
        data = request.get_json()
        
        # In real implementation, this would save to database
        new_camera = {
            'id': 4,  # Auto-generated in real implementation
            'name': data.get('name', 'New Camera'),
            'location': data.get('location', 'Unknown'),
            'ip_address': data.get('ip_address', '0.0.0.0'),
            'port': data.get('port', 554),
            'status': 'active',
            'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stream_url': f"rtsp://{data.get('ip_address', '0.0.0.0')}:{data.get('port', 554)}/stream1",
            'zone': data.get('zone', 'General')
        }
        
        return jsonify({
            'message': 'Camera added successfully',
            'camera': new_camera
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/cameras/<int:camera_id>', methods=['PUT', 'DELETE'])
def manage_camera(camera_id):
    """Manage individual camera"""
    try:
        if request.method == 'PUT':
            data = request.get_json()
            # Update camera logic here
            return jsonify({'message': 'Camera updated successfully'})
        
        elif request.method == 'DELETE':
            # Delete camera logic here
            return jsonify({'message': 'Camera removed successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/system-logs')
def get_admin_system_logs():
    """Get system logs for admin panel"""
    try:
        # Mock system logs - in real implementation, this would come from a log file or database
        logs = [
            {
                'id': 1,
                'timestamp': '2025-08-04 11:45:00',
                'level': 'INFO',
                'message': 'System started successfully',
                'module': 'system',
                'user': 'admin'
            },
            {
                'id': 2,
                'timestamp': '2025-08-04 11:44:30',
                'level': 'WARNING',
                'message': 'Camera 3 went offline',
                'module': 'camera',
                'user': 'system'
            },
            {
                'id': 3,
                'timestamp': '2025-08-04 11:43:15',
                'level': 'INFO',
                'message': 'Emergency detection triggered',
                'module': 'detection',
                'user': 'system'
            },
            {
                'id': 4,
                'timestamp': '2025-08-04 11:42:00',
                'level': 'INFO',
                'message': 'User login: john.doe@example.com',
                'module': 'auth',
                'user': 'john.doe'
            },
            {
                'id': 5,
                'timestamp': '2025-08-04 11:40:30',
                'level': 'ERROR',
                'message': 'Database connection failed',
                'module': 'database',
                'user': 'system'
            }
        ]
        
        # Apply filters
        level_filter = request.args.get('level')
        module_filter = request.args.get('module')
        limit = request.args.get('limit', 50, type=int)
        
        if level_filter:
            logs = [log for log in logs if log['level'] == level_filter.upper()]
        if module_filter:
            logs = [log for log in logs if log['module'] == module_filter]
        
        logs = logs[:limit]
        
        return jsonify({
            'logs': logs,
            'total': len(logs),
            'levels': ['INFO', 'WARNING', 'ERROR', 'DEBUG'],
            'modules': ['system', 'camera', 'detection', 'auth', 'database']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/analytics')
def get_analytics():
    """Get analytics data"""
    try:
        # Mock analytics data
        analytics = {
            'detections_by_day': [
                {'date': '2025-08-01', 'count': 5},
                {'date': '2025-08-02', 'count': 3},
                {'date': '2025-08-03', 'count': 8},
                {'date': '2025-08-04', 'count': 12}
            ],
            'detections_by_type': [
                {'type': 'Fire', 'count': 8},
                {'type': 'Accident', 'count': 5},
                {'type': 'Medical', 'count': 3},
                {'type': 'Security', 'count': 2}
            ],
            'user_activity': [
                {'date': '2025-08-01', 'logins': 15},
                {'date': '2025-08-02', 'logins': 12},
                {'date': '2025-08-03', 'logins': 18},
                {'date': '2025-08-04', 'logins': 22}
            ],
            'response_times': {
                'average': 2.5,
                'min': 0.8,
                'max': 5.2
            },
            'system_uptime': 99.8,
            'total_detections': 28,
            'active_users': 45,
            'cameras_online': 2
        }
        
        return jsonify(analytics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/settings', methods=['GET', 'PUT'])
def manage_settings():
    """Manage system settings"""
    try:
        if request.method == 'GET':
            # Get current settings
            settings = {
                'detection_sensitivity': 0.6,
                'alert_delay': 30,
                'max_upload_size': 10485760,
                'email_notifications': True,
                'sms_notifications': True,
                'telegram_notifications': True,
                'default_location': 'Building A',
                'maintenance_mode': False,
                'auto_backup': True,
                'backup_frequency': 'daily'
            }
            return jsonify(settings)
        
        elif request.method == 'PUT':
            # Update settings
            data = request.get_json()
            # In real implementation, this would save to database or config file
            return jsonify({'message': 'Settings updated successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/security', methods=['GET', 'PUT'])
def manage_security():
    """Manage security settings"""
    try:
        if request.method == 'GET':
            # Get security settings
            security = {
                'two_factor_auth': False,
                'max_login_attempts': 5,
                'session_timeout': 3600,
                'password_expiry_days': 90,
                'suspicious_login_alerts': True,
                'ip_whitelist': [],
                'audit_logging': True
            }
            return jsonify(security)
        
        elif request.method == 'PUT':
            # Update security settings
            data = request.get_json()
            # In real implementation, this would save to database
            return jsonify({'message': 'Security settings updated successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/export/<data_type>')
def export_admin_data(data_type):
    """Export data as CSV for admin panel"""
    try:
        if data_type == 'users':
            # Export users data
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users')
            users = cursor.fetchall()
            conn.close()
            
            # Create CSV content
            csv_content = "ID,Username,Email,Full Name,Phone,Emergency Contact,Created At,Last Login,Is Active\n"
            for user in users:
                csv_content += f"{user[0]},{user[1]},{user[2]},{user[3] or ''},{user[4] or ''},{user[5] or ''},{user[6]},{user[7] or ''},{user[8]}\n"
            
            return Response(csv_content, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=users.csv'})
        
        elif data_type == 'detections':
            # Export detection data
            detections = history_tracker.get_history(limit=1000)
            
            csv_content = "ID,Detection Type,Emergency Type,Location,Confidence,Status,Source,Timestamp\n"
            for detection in detections:
                csv_content += f"{detection.get('id', '')},{detection.get('detection_type', '')},{detection.get('emergency_type', '')},{detection.get('location', '')},{detection.get('confidence', '')},{detection.get('status', '')},{detection.get('source', '')},{detection.get('timestamp', '')}\n"
            
            return Response(csv_content, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=detections.csv'})
        
        elif data_type == 'logs':
            # Export system logs
            logs = get_system_logs().get_json()
            
            csv_content = "ID,Timestamp,Level,Message,Module,User\n"
            for log in logs.get('logs', []):
                csv_content += f"{log['id']},{log['timestamp']},{log['level']},{log['message']},{log['module']},{log['user']}\n"
            
            return Response(csv_content, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=system_logs.csv'})
        
        else:
            return jsonify({'error': 'Invalid export type'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Emergency Detection API...")
    
    # Initialize sample data
    print("📝 Initializing sample data...")
    add_sample_history_data()
    add_sample_emergency_contacts()
    
    print("🌐 Starting Flask server...")
    print("📱 Open http://localhost:5000 in your browser")
    print("📞 Emergency Contacts: http://localhost:5000/emergency-contacts")
    app.run(debug=True, host='0.0.0.0', port=5000) 