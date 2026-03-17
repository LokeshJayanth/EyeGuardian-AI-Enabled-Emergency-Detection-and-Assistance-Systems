#!/usr/bin/env python3
"""
Database Manager for Emergency Detection System
Comprehensive database operations with proper error handling and data validation
"""

import sqlite3
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Comprehensive database manager for the Emergency Detection System"""
    
    def __init__(self, db_path: str = 'emergency_system.db'):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.init_database()
        logger.info(f"🔧 Database Manager initialized with database: {self.db_path}")
    
    def get_connection(self):
        """Get a database connection with proper configuration"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable row factory for named columns
        return conn
    
    def init_database(self):
        """Initialize the database with schema and default data"""
        try:
            with self.lock:
                # Read and execute the schema file
                schema_file = Path(__file__).parent / 'database_schema.sql'
                if schema_file.exists():
                    with open(schema_file, 'r') as f:
                        schema_sql = f.read()
                    
                    conn = self.get_connection()
                    cursor = conn.cursor()
                    
                    # Execute schema in transactions
                    cursor.executescript(schema_sql)
                    conn.commit()
                    conn.close()
                    logger.info("✅ Database schema initialized successfully")
                else:
                    logger.warning("⚠️ Schema file not found, creating basic tables")
                    self._create_basic_tables()
                    
        except Exception as e:
            logger.error(f"❌ Error initializing database: {e}")
            raise
    
    def _create_basic_tables(self):
        """Create basic tables if schema file is not available"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create basic tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                role TEXT DEFAULT 'user',
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emergency_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                detection_type TEXT NOT NULL,
                emergency_type TEXT NOT NULL,
                location TEXT,
                confidence REAL,
                status TEXT DEFAULT 'detected',
                source TEXT NOT NULL,
                user_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    # User Management Methods
    def create_user(self, username: str, email: str, password_hash: str, 
                   full_name: str = None, role: str = 'user') -> bool:
        """Create a new user"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, full_name, role)
                    VALUES (?, ?, ?, ?, ?)
                ''', (username, email, password_hash, full_name, role))
                
                conn.commit()
                conn.close()
                logger.info(f"✅ User created: {username}")
                return True
                
        except sqlite3.IntegrityError as e:
            logger.error(f"❌ User creation failed (duplicate): {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error creating user: {e}")
            return False
    
    def get_user_by_credentials(self, username: str, password_hash: str) -> Optional[Dict]:
        """Get user by username and password"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM users 
                WHERE (username = ? OR email = ?) AND password_hash = ? AND is_active = 1
            ''', (username, username, password_hash))
            
            user = cursor.fetchone()
            conn.close()
            
            if user:
                return dict(user)
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting user: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                return dict(user)
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting user by ID: {e}")
            return None
    
    def update_user_last_login(self, user_id: int):
        """Update user's last login timestamp"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE users SET last_login = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (user_id,))
                
                conn.commit()
                conn.close()
                
        except Exception as e:
            logger.error(f"❌ Error updating user last login: {e}")
    
    def get_all_users(self, active_only: bool = True) -> List[Dict]:
        """Get all users"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if active_only:
                cursor.execute('SELECT * FROM users WHERE is_active = 1 ORDER BY created_at DESC')
            else:
                cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            
            users = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return users
            
        except Exception as e:
            logger.error(f"❌ Error getting users: {e}")
            return []
    
    # Emergency History Methods
    def add_emergency_detection(self, detection_type: str, emergency_type: str, 
                               location: str = None, confidence: float = None,
                               status: str = 'detected', source: str = 'unknown',
                               user_id: int = None, image_path: str = None,
                               voice_transcript: str = None, metadata: Dict = None) -> bool:
        """Add a new emergency detection record"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                metadata_json = json.dumps(metadata) if metadata else None
                
                cursor.execute('''
                    INSERT INTO emergency_history 
                    (detection_type, emergency_type, location, confidence, status, source, 
                     user_id, image_path, voice_transcript, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (detection_type, emergency_type, location, confidence, status, source,
                     user_id, image_path, voice_transcript, metadata_json))
                
                conn.commit()
                conn.close()
                logger.info(f"✅ Emergency detection added: {emergency_type}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error adding emergency detection: {e}")
            return False
    
    def get_emergency_history(self, limit: int = 100, offset: int = 0, 
                            filters: Dict = None) -> List[Dict]:
        """Get emergency history with optional filters"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = '''
                SELECT eh.*, u.username, u.full_name 
                FROM emergency_history eh
                LEFT JOIN users u ON eh.user_id = u.id
            '''
            params = []
            
            if filters:
                conditions = []
                if filters.get('detection_type'):
                    conditions.append('eh.detection_type = ?')
                    params.append(filters['detection_type'])
                if filters.get('emergency_type'):
                    conditions.append('eh.emergency_type = ?')
                    params.append(filters['emergency_type'])
                if filters.get('status'):
                    conditions.append('eh.status = ?')
                    params.append(filters['status'])
                if filters.get('source'):
                    conditions.append('eh.source = ?')
                    params.append(filters['source'])
                if filters.get('date_from'):
                    conditions.append('eh.timestamp >= ?')
                    params.append(filters['date_from'])
                if filters.get('date_to'):
                    conditions.append('eh.timestamp <= ?')
                    params.append(filters['date_to'])
                
                if conditions:
                    query += ' WHERE ' + ' AND '.join(conditions)
            
            query += ' ORDER BY eh.timestamp DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            history = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return history
            
        except Exception as e:
            logger.error(f"❌ Error getting emergency history: {e}")
            return []
    
    def get_emergency_stats(self) -> Dict:
        """Get emergency detection statistics"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Total detections
            cursor.execute('SELECT COUNT(*) as total FROM emergency_history')
            total_detections = cursor.fetchone()['total']
            
            # Detections by type
            cursor.execute('''
                SELECT emergency_type, COUNT(*) as count 
                FROM emergency_history 
                GROUP BY emergency_type
            ''')
            detections_by_type = {row['emergency_type']: row['count'] for row in cursor.fetchall()}
            
            # Detections by status
            cursor.execute('''
                SELECT status, COUNT(*) as count 
                FROM emergency_history 
                GROUP BY status
            ''')
            detections_by_status = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Recent detections (last 24 hours)
            cursor.execute('''
                SELECT COUNT(*) as recent 
                FROM emergency_history 
                WHERE timestamp >= datetime('now', '-1 day')
            ''')
            recent_detections = cursor.fetchone()['recent']
            
            # Active emergencies (status = 'detected' or 'confirmed')
            cursor.execute('''
                SELECT COUNT(*) as active 
                FROM emergency_history 
                WHERE status IN ('detected', 'confirmed')
            ''')
            active_emergencies = cursor.fetchone()['active']
            
            conn.close()
            
            return {
                'total_detections': total_detections,
                'recent_detections': recent_detections,
                'active_emergencies': active_emergencies,
                'detections_by_type': detections_by_type,
                'detections_by_status': detections_by_status
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting emergency stats: {e}")
            return {}
    
    # Emergency Contacts Methods
    def add_emergency_contact(self, name: str, phone: str, department: str,
                            designation: str = None, email: str = None,
                            address: str = None, priority: int = 1, notes: str = None) -> bool:
        """Add a new emergency contact"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO emergency_contacts 
                    (name, phone, department, designation, email, address, priority, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, phone, department, designation, email, address, priority, notes))
                
                conn.commit()
                conn.close()
                logger.info(f"✅ Emergency contact added: {name}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error adding emergency contact: {e}")
            return False
    
    def get_emergency_contacts(self, department: str = None, active_only: bool = True) -> List[Dict]:
        """Get emergency contacts"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = 'SELECT * FROM emergency_contacts'
            params = []
            
            conditions = []
            if active_only:
                conditions.append('is_active = 1')
            if department:
                conditions.append('department = ?')
                params.append(department)
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            query += ' ORDER BY priority ASC, name ASC'
            
            cursor.execute(query, params)
            contacts = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return contacts
            
        except Exception as e:
            logger.error(f"❌ Error getting emergency contacts: {e}")
            return []
    
    def update_emergency_contact(self, contact_id: int, **kwargs) -> bool:
        """Update emergency contact"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Build dynamic update query
                valid_fields = ['name', 'phone', 'department', 'designation', 'email', 
                              'address', 'is_active', 'priority', 'notes']
                updates = []
                params = []
                
                for field, value in kwargs.items():
                    if field in valid_fields and value is not None:
                        updates.append(f'{field} = ?')
                        params.append(value)
                
                if not updates:
                    return False
                
                params.append(contact_id)
                query = f'UPDATE emergency_contacts SET {", ".join(updates)} WHERE id = ?'
                
                cursor.execute(query, params)
                conn.commit()
                conn.close()
                
                logger.info(f"✅ Emergency contact updated: ID {contact_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error updating emergency contact: {e}")
            return False

    def delete_emergency_contact(self, contact_id: int) -> bool:
        """Delete an emergency contact by ID"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('DELETE FROM emergency_contacts WHERE id = ?', (contact_id,))
                deleted = cursor.rowcount > 0
                conn.commit()
                conn.close()
                if deleted:
                    logger.info(f"🗑️ Emergency contact deleted: ID {contact_id}")
                else:
                    logger.warning(f"⚠️ No emergency contact found to delete: ID {contact_id}")
                return deleted
        except Exception as e:
            logger.error(f"❌ Error deleting emergency contact: {e}")
            return False
    
    # Contact Submissions Methods
    def add_contact_submission(self, name: str, email: str, subject: str, 
                             message: str, priority: str = 'normal') -> bool:
        """Add a new contact submission"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO contact_submissions (name, email, subject, message, priority)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, email, subject, message, priority))
                
                conn.commit()
                conn.close()
                logger.info(f"✅ Contact submission added: {subject}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error adding contact submission: {e}")
            return False
    
    def get_contact_submissions(self, status: str = None, limit: int = 100) -> List[Dict]:
        """Get contact submissions"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = 'SELECT * FROM contact_submissions'
            params = []
            
            if status:
                query += ' WHERE status = ?'
                params.append(status)
            
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            submissions = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return submissions
            
        except Exception as e:
            logger.error(f"❌ Error getting contact submissions: {e}")
            return []
    
    # System Configuration Methods
    def get_config(self, key: str, default: str = None) -> str:
        """Get system configuration value"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT config_value FROM system_config WHERE config_key = ?', (key,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result['config_value']
            return default
            
        except Exception as e:
            logger.error(f"❌ Error getting config: {e}")
            return default
    
    def set_config(self, key: str, value: str, description: str = None, 
                  category: str = 'general') -> bool:
        """Set system configuration value"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO system_config (config_key, config_value, description, category)
                    VALUES (?, ?, ?, ?)
                ''', (key, value, description, category))
                
                conn.commit()
                conn.close()
                logger.info(f"✅ Config updated: {key} = {value}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error setting config: {e}")
            return False
    
    # System Logging Methods
    def add_system_log(self, level: str, module: str, message: str, 
                      details: Dict = None, user_id: int = None,
                      ip_address: str = None, user_agent: str = None) -> bool:
        """Add a system log entry"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                details_json = json.dumps(details) if details else None
                
                cursor.execute('''
                    INSERT INTO system_logs (level, module, message, details, user_id, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (level, module, message, details_json, user_id, ip_address, user_agent))
                
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            logger.error(f"❌ Error adding system log: {e}")
            return False
    
    def get_system_logs(self, level: str = None, module: str = None, 
                       limit: int = 100) -> List[Dict]:
        """Get system logs"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = 'SELECT * FROM system_logs'
            params = []
            
            conditions = []
            if level:
                conditions.append('level = ?')
                params.append(level)
            if module:
                conditions.append('module = ?')
                params.append(module)
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            logs = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return logs
            
        except Exception as e:
            logger.error(f"❌ Error getting system logs: {e}")
            return []
    
    # Database Maintenance Methods
    def cleanup_old_data(self, days: int = 90) -> bool:
        """Clean up old data based on retention policy"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                cutoff_date = datetime.now() - timedelta(days=days)
                
                # Clean up old emergency history
                cursor.execute('''
                    DELETE FROM emergency_history 
                    WHERE timestamp < ?
                ''', (cutoff_date,))
                history_deleted = cursor.rowcount
                
                # Clean up old system logs
                cursor.execute('''
                    DELETE FROM system_logs 
                    WHERE timestamp < ?
                ''', (cutoff_date,))
                logs_deleted = cursor.rowcount
                
                conn.commit()
                conn.close()
                
                logger.info(f"✅ Cleanup completed: {history_deleted} history records, {logs_deleted} log records")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
            return False
    
    def get_database_stats(self) -> Dict:
        """Get comprehensive database statistics"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            stats = {}
            
            # Table row counts
            tables = ['users', 'emergency_history', 'emergency_contacts', 
                     'contact_submissions', 'system_logs', 'emergency_incidents',
                     'voice_detections', 'camera_devices', 'system_config', 'api_usage']
            
            for table in tables:
                try:
                    cursor.execute(f'SELECT COUNT(*) as count FROM {table}')
                    result = cursor.fetchone()
                    stats[f'{table}_count'] = result['count'] if result else 0
                except:
                    stats[f'{table}_count'] = 0
            
            # Database size
            try:
                cursor.execute('PRAGMA page_count')
                page_count = cursor.fetchone()[0]
                cursor.execute('PRAGMA page_size')
                page_size = cursor.fetchone()[0]
                stats['database_size_mb'] = round((page_count * page_size) / (1024 * 1024), 2)
            except:
                stats['database_size_mb'] = 0
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting database stats: {e}")
            return {}
    
    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database"""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"✅ Database backed up to: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Error backing up database: {e}")
            return False

# Global database manager instance
db_manager = DatabaseManager() 