#!/usr/bin/env python3
"""
Voice to Email Integration
==========================
Automatically sends emergency emails when voice emergencies are detected
"""

from email_sender import EmergencyEmailSender
from database_manager import db_manager

class VoiceEmergencyEmailSystem:
    def __init__(self):
        self.email_sender = EmergencyEmailSender()
        print("🎤 Voice Emergency Email System initialized")
    
    def process_voice_emergency(self, voice_text, confidence, emergency_type=None):
        """
        Process voice input and automatically send emergency emails
        This is the main function to call from your voice detection system
        """
        print(f"\n🎤 VOICE EMERGENCY DETECTED!")
        print(f"   Text: '{voice_text}'")
        print(f"   Confidence: {confidence:.2f}")
        
        # Auto-detect emergency type if not provided
        if not emergency_type:
            emergency_type = self.detect_emergency_type(voice_text)
        
        print(f"   Emergency Type: {emergency_type}")
        
        # 1. Log to database
        db_manager.add_emergency_detection(
            detection_type="voice",
            emergency_type=emergency_type,
            confidence=confidence,
            source="voice_detection",
            voice_transcript=voice_text,
            status="detected"
        )
        
        # 2. Automatically send emails to all contacts
        print(f"\n📧 AUTO-SENDING EMERGENCY EMAILS...")
        success = self.email_sender.send_alert_to_contacts(
            emergency_type=emergency_type,
            voice_text=voice_text,
            confidence=confidence
        )
        
        if success:
            print("✅ Emergency emails sent automatically!")
        else:
            print("❌ Failed to send emergency emails")
        
        return success
    
    def detect_emergency_type(self, voice_text):
        """Auto-detect emergency type from voice text"""
        voice_lower = voice_text.lower()
        
        # Fire emergency keywords
        if any(word in voice_lower for word in ['fire', 'burning', 'smoke', 'flames', 'burn']):
            return "fire"
        
        # Medical emergency keywords
        elif any(word in voice_lower for word in ['medical', 'heart', 'collapsed', 'unconscious', 'bleeding', 'hurt', 'injured', 'ambulance', 'doctor']):
            return "medical"
        
        # Security emergency keywords
        elif any(word in voice_lower for word in ['intruder', 'break', 'theft', 'security', 'unauthorized', 'robbery']):
            return "security"
        
        # General help/emergency
        elif any(word in voice_lower for word in ['help', 'emergency', 'urgent', 'danger', 'crisis']):
            return "emergency"
        
        # Default
        else:
            return "emergency"

# Example usage functions for testing
def test_fire_voice():
    """Test fire emergency voice detection"""
    system = VoiceEmergencyEmailSystem()
    
    voice_text = "help me there is a fire in the building"
    confidence = 0.95
    
    return system.process_voice_emergency(voice_text, confidence)

def test_medical_voice():
    """Test medical emergency voice detection"""
    system = VoiceEmergencyEmailSystem()
    
    voice_text = "someone collapsed, need medical help urgently"
    confidence = 0.88
    
    return system.process_voice_emergency(voice_text, confidence)

def test_security_voice():
    """Test security emergency voice detection"""
    system = VoiceEmergencyEmailSystem()
    
    voice_text = "there's an intruder in the building"
    confidence = 0.82
    
    return system.process_voice_emergency(voice_text, confidence)

# Integration example for your voice detection system
def integrate_with_voice_detection():
    """
    Example of how to integrate with your existing voice detection system
    Call this function from your voice detection code
    """
    
    # Initialize the voice-to-email system
    voice_email_system = VoiceEmergencyEmailSystem()
    
    # Example: When your voice detection detects emergency speech
    # Replace this with your actual voice detection results
    detected_text = "help me there is a fire"
    detection_confidence = 0.92
    
    # Automatically process and send emails
    voice_email_system.process_voice_emergency(
        voice_text=detected_text,
        confidence=detection_confidence
    )

def main():
    """Test menu for voice emergency system"""
    print("🎤 VOICE EMERGENCY EMAIL SYSTEM")
    print("=" * 40)
    
    while True:
        print("\n📋 Test Options:")
        print("1. Test Fire Emergency Voice")
        print("2. Test Medical Emergency Voice") 
        print("3. Test Security Emergency Voice")
        print("4. Custom Voice Input")
        print("0. Exit")
        
        choice = input("\nEnter choice (0-4): ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            test_fire_voice()
        elif choice == "2":
            test_medical_voice()
        elif choice == "3":
            test_security_voice()
        elif choice == "4":
            voice_text = input("Enter voice text: ")
            confidence = float(input("Enter confidence (0.0-1.0): "))
            system = VoiceEmergencyEmailSystem()
            system.process_voice_emergency(voice_text, confidence)
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()
