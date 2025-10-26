#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.contrib.auth import get_user_model
from bestyy.communication.whatsapp.models import WhatsAppConversation

User = get_user_model()

def test_email_processing():
    print("Testing email processing in WhatsApp conversations...")

    # Create a test conversation
    test_phone = "+1234567890"

    # Clean up any existing test data
    WhatsAppConversation.objects.filter(phone_number=test_phone).delete()

    # Create conversation
    conversation, created = WhatsAppConversation.objects.get_or_create(
        phone_number=test_phone,
        defaults={'is_active': True}
    )
    print(f"{'Created' if created else 'Found'} conversation for {test_phone}")
    print(f"Initial state: {conversation.onboarding_state}")

    # Test 1: Email provided directly (no greeting first)
    print("\n=== Test 1: Email provided directly ===")
    test_email = "test@example.com"

    # Simulate the email detection logic
    import re
    email_match = re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", test_email)

    if email_match:
        print(f"Email detected: {test_email}")
        conversation.onboarding_state = 'awaiting_email'
        conversation.save()
        print(f"State set to: {conversation.onboarding_state}")

        # Now simulate the email processing
        existing = User.objects.filter(email=test_email).first()
        if not existing:
            print("No existing user found - would create new account")
        else:
            print(f"Existing user found: {existing.email}")
    else:
        print("No email detected")

    # Test 2: Greeting after email provided
    print("\n=== Test 2: Greeting while in awaiting_email state ===")
    greeting_content = "hello"

    if conversation.onboarding_state == 'awaiting_email':
        greeting_words = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings']
        if greeting_content.lower().strip() in greeting_words or any(word in greeting_content.lower() for word in greeting_words):
            print("Greeting detected while awaiting email - would send reminder")
        else:
            print("Not a greeting")

    # Test 3: Another email provided
    print("\n=== Test 3: Another email provided ===")
    another_email = "another@example.com"

    if conversation.onboarding_state == 'awaiting_email':
        email_match = re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", another_email)
        if email_match:
            print(f"Another email detected: {another_email}")
            print("Would process this email and create account or link existing account")
        else:
            print("No email detected")

    # Cleanup
    print("\n=== Cleanup ===")
    conversation.delete()
    print("SUCCESS: Email processing test completed")

if __name__ == '__main__':
    test_email_processing()