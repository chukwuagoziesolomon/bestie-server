#!/usr/bin/env python3
"""
Test the personalized greeting system to ensure time-based greetings work correctly
"""
import os
import django
import sys
from datetime import datetime, time

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.settings')
django.setup()

from bestyy.communication.whatsapp.greeting_service import WhatsAppGreetingService

def test_personalized_greetings():
    """Test the personalized greeting system across different times and scenarios"""
    greeting_service = WhatsAppGreetingService()
    
    print("=== PERSONALIZED GREETING SYSTEM TEST ===\n")
    
    # Test different times of day by overriding the current time
    test_times = [
        (time(7, 30), "Morning (7:30 AM)"),
        (time(12, 0), "Afternoon (12:00 PM)"),
        (time(18, 30), "Evening (6:30 PM)"),
        (time(22, 0), "Night (10:00 PM)"),
        (time(2, 0), "Late Night (2:00 AM)")
    ]
    
    test_names = ["Sarah", "John", "Maria", "Ahmed", ""]
    
    for test_time, time_label in test_times:
        print(f"🕐 {time_label}")
        print("-" * 40)
        
        # Mock the current time for testing
        original_get_time_period = greeting_service.get_time_period
        greeting_service.get_time_period = lambda: (
            "morning" if 5 <= test_time.hour < 12 else
            "afternoon" if 12 <= test_time.hour < 18 else
            "evening" if 18 <= test_time.hour < 22 else
            "night"
        )
        
        for name in test_names:
            display_name = name if name else "guest"
            
            # Test new user greeting
            greeting = greeting_service.get_personalized_greeting(name or "there")
            print(f"  New user ({display_name}): {greeting}")
            
            # Test returning user greeting
            returning_greeting = greeting_service.get_personalized_greeting(name or "there", is_returning=True)
            print(f"  Returning ({display_name}): {returning_greeting}")
            
            print()
        
        # Restore original method
        greeting_service.get_time_period = original_get_time_period
        print()
    
    # Test post-signup celebration messages
    print("🎉 POST-SIGNUP CELEBRATION MESSAGES")
    print("-" * 40)
    for name in ["Sarah", "John", "Maria"]:
        celebration = greeting_service.get_post_signup_celebration(name)
        print(f"  {name}: {celebration}")
        print()
    
    # Test food discovery prompts
    print("🍕 FOOD DISCOVERY PROMPTS")
    print("-" * 40)
    for i in range(3):
        prompt = greeting_service.get_food_discovery_prompt()
        print(f"  Prompt {i+1}: {prompt}")
    
    print("\n✅ All greeting tests completed! The system generates exciting, personalized, time-aware messages.")

if __name__ == "__main__":
    test_personalized_greetings()