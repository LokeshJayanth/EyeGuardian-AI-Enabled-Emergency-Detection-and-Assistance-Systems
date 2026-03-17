#!/usr/bin/env python3
"""
🚨 Enhanced Emergency Voice Detection with Telegram Integration
Real-time voice detection that sends Telegram alerts and finds nearby emergency services
"""

import speech_recognition as sr
import requests
import json
import os
import time
import threading
from datetime import datetime
import asyncio
import logging
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedEmergencyVoiceDetector:
    def __init__(self, telegram_bot_token=None, telegram_chat_id=None):
        """
        Initialize enhanced voice detector with Telegram integration
        
        Args:
            telegram_bot_token (str): Telegram bot token
            telegram_chat_id (str): Telegram chat ID to send messages
        """
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        
        # Telegram configuration
        self.telegram_bot_token = telegram_bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = telegram_chat_id or os.getenv('TELEGRAM_CHAT_ID')
        
        # Emergency keywords with categories
        self.emergency_keywords = {
            'medical': ['help me', 'heart attack', 'stroke', 'bleeding', 'unconscious', 'seizure', 'overdose', 'allergic reaction'],
            'fire': ['fire', 'smoke', 'burning', 'explosion', 'gas leak'],
            'police': ['robbery', 'theft', 'violence', 'assault', 'break in', 'intruder'],
            'general': ['emergency', 'accident', 'danger', 'sos', 'call 911', 'help']
        }
        
        # Initialize geocoder for location services
        self.geolocator = Nominatim(user_agent="emergency_detector")
        
        # Adjust for ambient noise
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        
        print("🎤 Enhanced Emergency Voice Detector initialized!")
        print("📱 Telegram integration:", "✅ Enabled" if self.telegram_bot_token else "❌ Disabled")
    
    def classify_emergency_type(self, text):
        """Classify the type of emergency based on keywords"""
        text_lower = text.lower()
        
        # Medical emergency keywords
        medical_keywords = [
            'heart attack', 'chest pain', 'breathing', 'unconscious', 'bleeding',
            'injury', 'accident', 'hurt', 'pain', 'sick', 'medical', 'ambulance',
            'hospital', 'doctor', 'medicine', 'health', 'emergency room', 'stroke',
            'seizure', 'overdose', 'poisoning', 'broken bone', 'wound'
        ]
        
        # Fire emergency keywords
        fire_keywords = [
            'fire', 'smoke', 'burning', 'flames', 'gas leak', 'explosion',
            'burn', 'hot', 'heat', 'firefighter', 'carbon monoxide', 'electrical fire',
            'house fire', 'building fire', 'wildfire'
        ]
        
        # Police emergency keywords
        police_keywords = [
            'robbery', 'theft', 'break in', 'burglar', 'attack', 'violence',
            'threat', 'dangerous', 'weapon', 'police', 'crime', 'safety',
            'assault', 'kidnapping', 'domestic violence', 'suspicious person',
            'vandalism', 'trespassing'
        ]
        
        # Count keyword matches
        medical_score = sum(1 for keyword in medical_keywords if keyword in text_lower)
        fire_score = sum(1 for keyword in fire_keywords if keyword in text_lower)
        police_score = sum(1 for keyword in police_keywords if keyword in text_lower)
        
        # Determine emergency type
        if medical_score > fire_score and medical_score > police_score:
            return "medical"
        elif fire_score > police_score:
            return "fire"
        elif police_score > 0:
            return "police"
        else:
            return "medical"  # Default to medical for general help requests
    
    async def send_telegram_alert(self, emergency_type, text, keywords, location=None):
        """
        Send emergency alert via Telegram
        
        Args:
            emergency_type (str): Type of emergency
            text (str): Original speech text
            keywords (list): Detected keywords
            location (dict): Location information
        """
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.warning("Telegram credentials not configured")
            return False
        
        # Create emergency message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"🚨 EMERGENCY ALERT 🚨\n\n"
        message += f"🕐 Time: {timestamp}\n"
        message += f"📍 Type: {emergency_type.upper()}\n"
        message += f"🗣️ Speech: '{text}'\n"
        message += f"🔍 Keywords: {', '.join(keywords)}\n"
        
        if location:
            message += f"📍 Location: {location.get('address', 'Unknown')}\n"
            message += f"🌐 Coordinates: {location.get('latitude')}, {location.get('longitude')}\n"
        
        message += f"\n⚡ Immediate action required!"
        
        # Send message
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Telegram alert sent successfully")
                return True
            else:
                logger.error(f"❌ Telegram alert failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending Telegram alert: {e}")
            return False
    
    def get_current_location(self):
        """
        Get current location using IP geolocation
        
        Returns:
            dict: Location information
        """
        try:
            # Using IP geolocation as fallback
            response = requests.get('http://ip-api.com/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'latitude': data.get('lat'),
                    'longitude': data.get('lon'),
                    'city': data.get('city'),
                    'country': data.get('country'),
                    'address': f"{data.get('city')}, {data.get('regionName')}, {data.get('country')}"
                }
        except Exception as e:
            logger.error(f"Error getting location: {e}")
        
        return None
    
    def find_nearby_emergency_services(self, location, emergency_type, radius_km=10):
        """
        Find nearby emergency services based on emergency type
        
        Args:
            location (dict): Current location
            emergency_type (str): Type of emergency
            radius_km (int): Search radius in kilometers
            
        Returns:
            list: List of nearby emergency services
        """
        if not location:
            return []
        
        # Define search queries based on emergency type
        search_queries = {
            'medical': ['hospital', 'clinic', 'medical center'],
            'fire': ['fire station', 'fire department'],
            'police': ['police station', 'police department'],
            'general': ['hospital', 'police station', 'fire station']
        }
        
        queries = search_queries.get(emergency_type, search_queries['general'])
        all_services = []
        
        for query in queries:
            services = self.search_places_nearby(location, query, radius_km)
            all_services.extend(services)
        
        # Remove duplicates and sort by distance
        unique_services = []
        seen_names = set()
        
        for service in all_services:
            if service['name'] not in seen_names:
                unique_services.append(service)
                seen_names.add(service['name'])
        
        # Sort by distance
        unique_services.sort(key=lambda x: x['distance'])
        
        return unique_services[:10]  # Return top 10 closest
    
    def search_places_nearby(self, location, query, radius_km):
        """
        Search for places using OpenStreetMap Nominatim
        
        Args:
            location (dict): Current location
            query (str): Search query
            radius_km (int): Search radius
            
        Returns:
            list: List of found places
        """
        try:
            # Search using Nominatim
            search_query = f"{query} near {location['city']}, {location['country']}"
            results = self.geolocator.geocode(search_query, exactly_one=False, limit=20)
            
            if not results:
                return []
            
            services = []
            user_location = (location['latitude'], location['longitude'])
            
            for result in results:
                if result.latitude and result.longitude:
                    service_location = (result.latitude, result.longitude)
                    distance = geodesic(user_location, service_location).kilometers
                    
                    if distance <= radius_km:
                        services.append({
                            'name': result.address.split(',')[0],
                            'address': result.address,
                            'latitude': result.latitude,
                            'longitude': result.longitude,
                            'distance': round(distance, 2),
                            'type': query
                        })
            
            return services
            
        except Exception as e:
            logger.error(f"Error searching places: {e}")
            return []
    
    def generate_emergency_response(self, emergency_type, location, services):
        """
        Generate emergency response with nearby services
        
        Args:
            emergency_type (str): Type of emergency
            location (dict): Current location
            services (list): Nearby emergency services
            
        Returns:
            dict: Emergency response data
        """
        response = {
            'timestamp': datetime.now().isoformat(),
            'emergency_type': emergency_type,
            'location': location,
            'nearby_services': services,
            'recommendations': []
        }
        
        # Add specific recommendations based on emergency type
        if emergency_type == 'medical':
            response['recommendations'] = [
                "Call emergency services immediately: 108/102",
                "Stay calm and provide first aid if trained",
                "Prepare to give clear location and symptoms"
            ]
        elif emergency_type == 'fire':
            response['recommendations'] = [
                "Call fire department: 101",
                "Evacuate immediately if safe to do so",
                "Do not use elevators",
                "Stay low to avoid smoke"
            ]
        elif emergency_type == 'police':
            response['recommendations'] = [
                "Call police: 100",
                "Move to a safe location",
                "Do not confront if dangerous"
            ]
        else:
            response['recommendations'] = [
                "Call appropriate emergency service",
                "Stay calm and assess the situation",
                "Provide clear location information"
            ]
        
        return response
    
    async def trigger_emergency_alert(self, text, keywords, emergency_type):
        """
        Trigger comprehensive emergency alert system
        
        Args:
            text (str): Original speech text
            keywords (list): Detected emergency keywords
            emergency_type (str): Classified emergency type
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\n🚨 EMERGENCY ALERT TRIGGERED! 🚨")
        print(f"⏰ Time: {timestamp}")
        print(f"🎯 Type: {emergency_type.upper()}")
        print(f"💬 Text: '{text}'")
        print(f"🔍 Keywords: {', '.join(keywords)}")
        
        # Get location information
        location_info = await self.get_location_info()
        if location_info:
            print(f"📍 Location: {location_info['city']}, {location_info['country']}")
        
        # Send Telegram alert
        if self.telegram_bot_token and self.telegram_chat_id:
            await self.send_telegram_alert(emergency_type, text, keywords, location_info)
        
        # Find nearby emergency services
        nearby_services = await self.find_nearby_emergency_services(emergency_type, location_info)
        if nearby_services:
            print(f"\n🏥 Nearby {emergency_type} services found:")
            for service in nearby_services[:3]:  # Show top 3
                print(f"   • {service['name']} - {service.get('distance', 'Unknown distance')}")
        
        # Open emergency map with specific type
        self.open_emergency_map(emergency_type)
        
        # Log emergency
        self.log_emergency(text, keywords, emergency_type, location_info)
        
        # Play alert sound (if available)
        self.play_alert_sound()
        
        print(f"\n✅ Emergency alert system activated!")
        print(f"📱 Telegram alert: {'✅ Sent' if self.telegram_bot_token else '❌ Not configured'}")
        print(f"🗺️  Emergency services: {'✅ Located' if nearby_services else '❌ Not found'}")
        print(f"🌐 Emergency map: ✅ Opened with {emergency_type} services")
        
        return {
            'timestamp': timestamp,
            'type': emergency_type,
            'text': text,
            'keywords': keywords,
            'location': location_info,
            'services': nearby_services
        }
    
    def open_emergency_map(self, emergency_type):
        """Open the emergency map page with the specific emergency type"""
        import webbrowser
        map_url = f"http://localhost:5000/maps?emergency={emergency_type}"
        try:
            webbrowser.open(map_url)
            print(f"🌐 Opening emergency map: {map_url}")
        except Exception as e:
            print(f"❌ Could not open emergency map: {e}")
            print(f"💡 Please manually open: {map_url}")
    
    def save_emergency_data(self, response):
        """
        Save emergency data to file
        
        Args:
            response (dict): Emergency response data
        """
        try:
            with open("emergency_responses.json", "a") as f:
                f.write(json.dumps(response) + "\n")
        except Exception as e:
            logger.error(f"Error saving emergency data: {e}")
    
    def start_listening(self):
        """
        Start listening for emergency keywords
        """
        self.is_listening = True
        
        print("🎤 Enhanced Emergency Voice Detection Active")
        print("💡 Say emergency phrases like 'help me', 'fire', 'medical emergency'")
        print("⏹️ Press Ctrl+C to stop\n")
        
        try:
            while self.is_listening:
                try:
                    with self.microphone as source:
                        print("🎤 Listening...")
                        audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    
                    # Recognize speech
                    text = self.recognizer.recognize_google(audio)
                    print(f"🗣️ You said: '{text}'")
                    
                    # Check for emergency keywords
                    emergency_type, keywords = self.detect_emergency_type(text)
                    
                    if emergency_type and keywords:
                        # Run emergency alert in async context
                        asyncio.run(self.trigger_emergency_alert(text, emergency_type, keywords))
                    
                except sr.UnknownValueError:
                    print("🤔 Could not understand audio")
                except sr.RequestError as e:
                    print(f"❌ Speech recognition error: {e}")
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Error in listening loop: {e}")
                    continue
                    
        except KeyboardInterrupt:
            print("\n⏹️ Stopping voice detection...")
        finally:
            self.is_listening = False
            print("✅ Voice detection stopped.")

def main():
    """
    Main function to run the enhanced voice detector
    """
    print("🚨 Enhanced Emergency Voice Detection System")
    print("="*60)
    
    # Initialize detector
    detector = EnhancedEmergencyVoiceDetector()
    
    # Start listening
    print("\n🚀 Starting enhanced emergency voice detection...")
    detector.start_listening()

if __name__ == "__main__":
    main()
