#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.contrib.auth import get_user_model
from bestyy.communication.whatsapp.models import WhatsAppConversation, WhatsAppMessage
from bestyy.communication.whatsapp.ai_service import WhatsAppAIService

User = get_user_model()

def test_user_persistence():
    print("Testing user persistence in WhatsApp conversations...")

    # Create a test user
    test_phone = "+1234567890"
    test_email = "test@example.com"

    # Clean up any existing test data
    WhatsAppConversation.objects.filter(phone_number=test_phone).delete()
    User.objects.filter(email=test_email).delete()

    # Create conversation
    conversation, created = WhatsAppConversation.objects.get_or_create(
        phone_number=test_phone,
        defaults={'is_active': True}
    )
    print(f"{'Created' if created else 'Found'} conversation for {test_phone}")

    # Test 1: New user (no user linked)
    print("\n=== Test 1: New user scenario ===")
    print(f"Conversation user: {conversation.user}")
    print(f"Conversation state: {conversation.onboarding_state}")

    # Should be treated as new user
    if not conversation.user and not conversation.onboarding_state:
        print("SUCCESS: Correctly identified as new user")
    else:
        print("ERROR: Incorrectly identified existing user")

    # Test 2: Link user to conversation
    print("\n=== Test 2: Linking user to conversation ===")
    user = User.objects.create_user(
        email=test_email,
        password="testpass123",
        first_name="Test",
        last_name="User",
        phone=test_phone
    )

    conversation.user = user
    conversation.onboarding_state = 'onboarded'
    conversation.save()

    print(f"Linked user {user.email} to conversation")
    print(f"Conversation state: {conversation.onboarding_state}")

    # Test 3: Simulate returning user
    print("\n=== Test 3: Returning user scenario ===")
    # Refresh conversation from database
    conversation.refresh_from_db()

    if conversation.user and conversation.onboarding_state == 'onboarded':
        print("SUCCESS: Correctly identified as returning user")
    else:
        print("ERROR: Failed to identify returning user")

    # Test 4: Test AI service with user context
    print("\n=== Test 4: AI service with user context ===")
    try:
        ai_service = WhatsAppAIService()

        # Create a test message
        message = WhatsAppMessage.objects.create(
            conversation=conversation,
            message_type='text',
            content='hello',
            direction='inbound'
        )

        # Test categorization
        category = ai_service._categorize_message('hello')
        print(f"Message categorized as: {category}")

        # Test with user context
        ai_response = ai_service.process_message(message, context={'user_exists': True})
        print(f"AI response success: {ai_response.get('success', False)}")

        if ai_response.get('success'):
            print(f"AI response: {ai_response.get('response', '')[:100]}...")
        else:
            print(f"AI response error: {ai_response.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"ERROR: AI service test failed: {e}")
        import traceback
        traceback.print_exc()

    # Cleanup
    print("\n=== Cleanup ===")
    conversation.delete()
    user.delete()
    print("SUCCESS: Test completed and cleaned up")

if __name__ == '__main__':
    test_user_persistence()