#!/usr/bin/env python3
"""
Admin Authentication for Emergency Detection System
Simple authentication system for admin dashboard access
"""

import hashlib
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Admin credentials
ADMIN_EMAIL = "lokeshjayanth1403@gmail.com"
ADMIN_PASSWORD_HASH = "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"  # "lokesh1403"

# Session management
admin_sessions = {}

def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_admin_credentials(email, password):
    """Verify admin credentials"""
    if email.lower() == ADMIN_EMAIL.lower():
        password_hash = hash_password(password)
        return password_hash == ADMIN_PASSWORD_HASH
    return False

def create_admin_session(email):
    """Create an admin session"""
    session_id = hashlib.sha256(f"{email}{datetime.now()}".encode()).hexdigest()
    admin_sessions[session_id] = {
        'email': email,
        'created_at': datetime.now(),
        'expires_at': datetime.now() + timedelta(hours=24)  # 24 hour session
    }
    logger.info(f"✅ Admin session created for {email}")
    return session_id

def verify_admin_session(session_id):
    """Verify if admin session is valid"""
    if session_id not in admin_sessions:
        return False
    
    session = admin_sessions[session_id]
    if datetime.now() > session['expires_at']:
        # Session expired, remove it
        del admin_sessions[session_id]
        return False
    
    return True

def get_admin_email(session_id):
    """Get admin email from session"""
    if session_id in admin_sessions:
        return admin_sessions[session_id]['email']
    return None

def logout_admin(session_id):
    """Logout admin by removing session"""
    if session_id in admin_sessions:
        email = admin_sessions[session_id]['email']
        del admin_sessions[session_id]
        logger.info(f"✅ Admin logged out: {email}")
        return True
    return False

def cleanup_expired_sessions():
    """Clean up expired admin sessions"""
    current_time = datetime.now()
    expired_sessions = []
    
    for session_id, session in admin_sessions.items():
        if current_time > session['expires_at']:
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        del admin_sessions[session_id]
    
    if expired_sessions:
        logger.info(f"🧹 Cleaned up {len(expired_sessions)} expired admin sessions") 