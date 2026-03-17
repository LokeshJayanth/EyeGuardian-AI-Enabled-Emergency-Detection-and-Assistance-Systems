#!/usr/bin/env python3
"""
🚨 Emergency Services API
Backend API to handle emergency services location and Telegram integration
"""

from flask import Flask, request, jsonify, render_template
import requests
import os
import json
import asyncio
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')

class EmergencyServicesAPI:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="emergency_services")
        
        # Emergency services database with contact information
        self.emergency_services_db = {
            'medical': [
                {
                    'name': 'All India Institute of Medical Sciences (AIIMS)',
                    'phone': '+91-11-2659-3333',
                    'emergency_phone': '+91-11-2659-3444',
                    'address': 'Ansari Nagar, New Delhi',
                    'type': 'hospital',
                    'services': ['Emergency Care', 'Trauma Center', 'ICU', 'Surgery'],
                    'rating': 4.8
                },
                {
                    'name': 'Safdarjung Hospital',
                    'phone': '+91-11-2673-0000',
                    'emergency_phone': '+91-11-2673-0001',
                    'address': 'Ring Road, Safdarjung Enclave, New Delhi',
                    'type': 'hospital',
                    'services': ['Emergency Care', 'General Medicine', 'Surgery'],
                    'rating': 4.2
                },
                {
                    'name': 'Apollo Hospital',
                    'phone': '+91-11-2692-5858',
                    'emergency_phone': '+91-11-2692-5801',
                    'address': 'Sarita Vihar, New Delhi',
                    'type': 'hospital',
                    'services': ['Emergency Care', 'Cardiology', 'Neurology', 'ICU'],
                    'rating': 4.6
                },
                {
                    'name': 'Max Super Speciality Hospital',
                    'phone': '+91-11-2651-5050',
                    'emergency_phone': '+91-11-2651-5051',
                    'address': 'Saket, New Delhi',
                    'type': 'hospital',
                    'services': ['Emergency Care', 'Trauma Center', 'Critical Care'],
                    'rating': 4.5
                }
            ],
            'fire': [
                {
                    'name': 'Delhi Fire Service Headquarters',
                    'phone': '+91-11-2331-1111',
                    'emergency_phone': '101',
                    'address': 'Connaught Place, New Delhi',
                    'type': 'fire',
                    'services': ['Fire Fighting', 'Rescue Operations', 'Emergency Response'],
                    'rating': 4.3
                },
                {
                    'name': 'Central Fire Station',
                    'phone': '+91-11-2336-2222',
                    'emergency_phone': '101',
                    'address': 'Parliament Street, New Delhi',
                    'type': 'fire',
                    'services': ['Fire Fighting', 'Ambulance Service', 'Rescue'],
                    'rating': 4.1
                },
                {
                    'name': 'Karol Bagh Fire Station',
                    'phone': '+91-11-2575-3333',
                    'emergency_phone': '101',
                    'address': 'Karol Bagh, New Delhi',
                    'type': 'fire',
                    'services': ['Fire Fighting', 'Emergency Response'],
                    'rating': 4.0
                }
            ],
            'police': [
                {
                    'name': 'Delhi Police Headquarters',
                    'phone': '+91-11-2331-4444',
                    'emergency_phone': '100',
                    'address': 'ITO, New Delhi',
                    'type': 'police',
                    'services': ['Emergency Response', 'Crime Investigation', 'Traffic Control'],
                    'rating': 4.0
                },
                {
                    'name': 'Connaught Place Police Station',
                    'phone': '+91-11-2336-5555',
                    'emergency_phone': '100',
                    'address': 'Connaught Place, New Delhi',
                    'type': 'police',
                    'services': ['Emergency Response', 'Tourist Help', 'Crime Prevention'],
                    'rating': 3.8
                },
                {
                    'name': 'Women Safety Helpline',
                    'phone': '+91-11-2338-1091',
                    'emergency_phone': '1091',
                    'address': 'Delhi Police Headquarters',
                    'type': 'police',
                    'services': ['Women Safety', '24x7 Helpline', 'Emergency Response'],
                    'rating': 4.2
                }
            ]
        }
    
    def get_user_location_from_ip(self):
        """Get approximate location from IP address"""
        try:
            response = requests.get('http://ip-api.com/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'latitude': data.get('lat', 28.6139),
                    'longitude': data.get('lon', 77.2090),
                    'city': data.get('city', 'Delhi'),
                    'country': data.get('country', 'India')
                }
        except Exception as e:
            logger.error(f"Error getting location from IP: {e}")
        
        # Default to Delhi coordinates
        return {
            'latitude': 28.6139,
            'longitude': 77.2090,
            'city': 'Delhi',
            'country': 'India'
        }
    
    def calculate_distance(self, user_location, service_location):
        """Calculate distance between user and service"""
        try:
            user_coords = (user_location['latitude'], user_location['longitude'])
            service_coords = (service_location['latitude'], service_location['longitude'])
            distance = geodesic(user_coords, service_coords).kilometers
            return round(distance, 2)
        except Exception as e:
            logger.error(f"Error calculating distance: {e}")
            return 0
    
    def add_location_coordinates(self, services, user_location):
        """Add realistic coordinates to services based on user location"""
        import random
        
        for service in services:
            # Add some random offset to user location to simulate nearby services
            lat_offset = random.uniform(-0.05, 0.05)  # ~5km radius
            lng_offset = random.uniform(-0.05, 0.05)
            
            service['latitude'] = user_location['latitude'] + lat_offset
            service['longitude'] = user_location['longitude'] + lng_offset
            
            # Calculate distance
            service['distance'] = self.calculate_distance(user_location, service)
        
        return services
    
    def find_emergency_services(self, location, emergency_type, radius_km=10):
        """Find emergency services based on type and location"""
        try:
            if emergency_type == 'general':
                # Return all types of services
                all_services = []
                for service_type in ['medical', 'fire', 'police']:
                    services = self.emergency_services_db.get(service_type, [])
                    all_services.extend(services[:2])  # Limit to 2 per type
            else:
                all_services = self.emergency_services_db.get(emergency_type, [])
            
            # Add coordinates and calculate distances
            services_with_location = self.add_location_coordinates(all_services.copy(), location)
            
            # Filter by radius and sort by distance
            nearby_services = [s for s in services_with_location if s['distance'] <= radius_km]
            nearby_services.sort(key=lambda x: x['distance'])
            
            return nearby_services[:10]  # Return top 10
            
        except Exception as e:
            logger.error(f"Error finding emergency services: {e}")
            return []
    
    async def send_telegram_alert(self, message, bot_token=None, chat_id=None):
        """Send emergency alert via Telegram"""
        bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            logger.warning("Telegram credentials not configured")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            return False

# Initialize API
emergency_api = EmergencyServicesAPI()

@app.route('/')
def home():
    """Serve the main emergency map page"""
    return render_template('emergency_map.html')

@app.route('/emergency-map')
def emergency_map():
    """Serve the emergency map page"""
    return render_template('emergency_map.html')

@app.route('/api/emergency-services', methods=['POST'])
def get_emergency_services():
    """API endpoint to get nearby emergency services"""
    try:
        data = request.get_json()
        
        # Get location (from request or IP)
        location = data.get('location')
        if not location:
            location = emergency_api.get_user_location_from_ip()
        
        emergency_type = data.get('emergency_type', 'medical')
        radius = data.get('radius', 10)
        
        # Find nearby services
        services = emergency_api.find_emergency_services(location, emergency_type, radius)
        
        return jsonify({
            'success': True,
            'location': location,
            'emergency_type': emergency_type,
            'services': services,
            'count': len(services)
        })
        
    except Exception as e:
        logger.error(f"Error in emergency services API: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/voice-emergency', methods=['POST'])
def handle_voice_emergency():
    """Handle voice emergency detection and send alerts"""
    try:
        data = request.get_json()
        
        emergency_text = data.get('text', '')
        emergency_type = data.get('emergency_type', 'general')
        location = data.get('location') or emergency_api.get_user_location_from_ip()
        
        # Create emergency alert message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"🚨 VOICE EMERGENCY ALERT 🚨\n\n"
        message += f"🕐 Time: {timestamp}\n"
        message += f"📍 Type: {emergency_type.upper()}\n"
        message += f"🗣️ Voice: '{emergency_text}'\n"
        message += f"📍 Location: {location.get('city', 'Unknown')}\n"
        message += f"🌐 Coordinates: {location.get('latitude')}, {location.get('longitude')}\n"
        message += f"\n⚡ Immediate response required!"
        
        # Send Telegram alert
        telegram_sent = asyncio.run(emergency_api.send_telegram_alert(message))
        
        # Find nearby services
        services = emergency_api.find_emergency_services(location, emergency_type)
        
        return jsonify({
            'success': True,
            'alert_sent': telegram_sent,
            'location': location,
            'nearby_services': services,
            'message': 'Emergency alert processed successfully'
        })
        
    except Exception as e:
        logger.error(f"Error handling voice emergency: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/send-emergency-alert', methods=['POST'])
def send_emergency_alert():
    """Send emergency alert via Telegram"""
    try:
        data = request.get_json()
        
        message = data.get('message', 'Emergency alert triggered')
        bot_token = data.get('bot_token')
        chat_id = data.get('chat_id')
        
        # Send alert
        success = asyncio.run(emergency_api.send_telegram_alert(message, bot_token, chat_id))
        
        return jsonify({
            'success': success,
            'message': 'Alert sent successfully' if success else 'Failed to send alert'
        })
        
    except Exception as e:
        logger.error(f"Error sending emergency alert: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/emergency-contacts')
def get_emergency_contacts():
    """Get emergency contact numbers"""
    contacts = {
        'india': {
            'police': '100',
            'fire': '101',
            'medical': '108',
            'women_helpline': '1091',
            'child_helpline': '1098',
            'disaster_management': '1078'
        },
        'international': {
            'usa': '911',
            'uk': '999',
            'europe': '112'
        }
    }
    
    return jsonify({
        'success': True,
        'contacts': contacts
    })

if __name__ == '__main__':
    print("🚨 Starting Emergency Services API...")
    print("🗺️ Emergency Map: http://localhost:5002")
    print("📡 API Endpoints:")
    print("  POST /api/emergency-services - Get nearby services")
    print("  POST /api/voice-emergency - Handle voice emergencies")
    print("  POST /api/send-emergency-alert - Send Telegram alerts")
    print("  GET  /api/emergency-contacts - Get emergency numbers")
    
    app.run(host='0.0.0.0', port=5002, debug=True)
