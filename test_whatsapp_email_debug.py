#!/usr/bin/env python3
"""
Test WhatsApp email detection in real scenarios
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.communication.whatsapp.models import WhatsAppConversation
from unittest.mock import patch, MagicMock
import re

def test_email_detection_flow():
    print("TESTING WHATSAPP EMAIL DETECTION FLOW")
    print("=" * 50)
    
    # Clean test data
    test_phone = "+2348000000999"
    WhatsAppConversation.objects.filter(phone_number=test_phone).delete()
    
    # Create conversation in awaiting_email state
    conversation = WhatsAppConversation.objects.create(
        phone_number=test_phone,
        is_active=True,
        onboarding_state='awaiting_email'
    )
    print(f"✅ Created conversation with state: {conversation.onboarding_state}")
    
    # Test different email formats users might send
    test_messages = [
        "user@gmail.com",
        "test.email@yahoo.com", 
        "my.email@domain.co.uk",
        "user123@example.org",
        "My email is user@gmail.com",
        "user@gmail.com please",
        "Here's my email: user@gmail.com",
        "Contact me at user@gmail.com thanks",
        "user @gmail.com",  # space in email - should fail
        "user@gmail .com",  # space in email - should fail
        "notanemail",
        "user@",
        "@gmail.com",
        "user@domain",
        "123456",
        "",
        "user@gmail.com\nwith newline",  # with newline
        "user@gmail.com with extra text",
    ]
    
    # Test each message format
    email_pattern = r"[^@\s]+@[^@\s]+\.[^@\s]+"
    
    for i, content in enumerate(test_messages, 1):
        print(f"\n{i:2d}. Testing: '{content}'")
        
        # Test the exact regex logic from views.py
        email_match = re.match(email_pattern, content)
        
        if email_match:
            extracted_email = content  # In the current code, it uses full content
            print(f"    ✅ MATCH - Email: '{extracted_email}'")
            
            # Check if it's a valid-looking email
            if '@' in extracted_email and '.' in extracted_email.split('@')[-1]:
                print(f"    ✅ Valid email structure")
            else:
                print(f"    ⚠️  Questionable email structure")
        else:
            print(f"    ❌ NO MATCH - Would ask for email again")
    
    # Test improved email extraction
    print(f"\n" + "=" * 50)
    print("TESTING IMPROVED EMAIL EXTRACTION")
    print("=" * 50)
    
    improved_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    
    for i, content in enumerate(test_messages, 1):
        print(f"\n{i:2d}. Testing: '{content}'")
        
        # Try to extract email from anywhere in the message
        email_search = re.search(improved_pattern, content)
        
        if email_search:
            extracted_email = email_search.group()
            print(f"    ✅ FOUND EMAIL - '{extracted_email}'")
        else:
            print(f"    ❌ NO EMAIL FOUND")
    
    # Cleanup
    conversation.delete()
    print(f"\n🧹 Cleaned up test data")

if __name__ == '__main__':
    test_email_detection_flow()