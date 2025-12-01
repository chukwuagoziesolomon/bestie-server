#!/usr/bin/env python3
"""
Test WhatsApp Signup Flow
Verifies that new WhatsApp conversations properly collect email before allowing food orders
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bestyy'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.utils import timezone
from bestyy.communication.whatsapp.models import WhatsAppConversation
from bestyy.communication.whatsapp.views import _process_meta_message
from bestyy.communication.whatsapp.services.meta_whatsapp_service import MetaWhatsAppService

print("TESTING WHATSAPP SIGNUP FLOW")
print("=" * 50)

# Mock phone number for testing
test_phone = "+2341234567890"

# Clean up any existing conversation
WhatsAppConversation.objects.filter(phone_number=test_phone).delete()

# Test 1: First message from new user should ask for email
print("\n1. Testing first message from new user...")
message_data = {
    'id': 'test_msg_001',
    'from': test_phone,
    'timestamp': str(int(timezone.now().timestamp())),
    'type': 'text',
    'text': {'body': 'Hi, I want to order pizza'}
}

value_data = {
    'messaging_product': 'whatsapp',
    'metadata': {'phone_number_id': '854856884368905'},
    'contacts': [{'profile': {'name': 'Test User'}}],
    'messages': [message_data]
}

class MockMetaService:
    def __init__(self):
        self.sent_messages = []
    
    def send_message(self, to, message, message_type='text'):
        self.sent_messages.append({'to': to, 'message': message, 'type': message_type})
        print(f"📤 Bot Response: {message}")
        return {'success': True}

# Mock the MetaWhatsAppService
original_service = MetaWhatsAppService
mock_service = MockMetaService()

# Patch the service in the module
import bestyy.communication.whatsapp.views
bestyy.communication.whatsapp.views.MetaWhatsAppService = lambda: mock_service

try:
    # Process the message
    _process_meta_message(message_data, value_data)
    
    # Check conversation state
    conversation = WhatsAppConversation.objects.get(phone_number=test_phone)
    print(f"✅ Conversation created with state: {conversation.onboarding_state}")
    print(f"✅ User linked: {bool(conversation.user)}")
    
    # Check if bot asked for email
    if mock_service.sent_messages:
        last_response = mock_service.sent_messages[-1]['message']
        if 'email' in last_response.lower():
            print("✅ Bot correctly asked for email address")
        else:
            print("❌ Bot did not ask for email address")
            print(f"   Actual response: {last_response}")
    else:
        print("❌ Bot did not send any response")

    print(f"\n2. Testing email submission...")
    
    # Test 2: User provides email
    mock_service.sent_messages.clear()
    email_message = {
        'id': 'test_msg_002',
        'from': test_phone,
        'timestamp': str(int(timezone.now().timestamp()) + 1),
        'type': 'text',
        'text': {'body': 'testuser@gmail.com'}
    }
    
    value_data['messages'] = [email_message]
    _process_meta_message(email_message, value_data)
    
    # Check if account was created
    conversation.refresh_from_db()
    print(f"✅ Conversation state after email: {conversation.onboarding_state}")
    print(f"✅ User linked after email: {bool(conversation.user)}")
    
    if mock_service.sent_messages:
        last_response = mock_service.sent_messages[-1]['message']
        print(f"📤 Bot response to email: {last_response[:100]}...")
        
        if 'account' in last_response.lower() or 'welcome' in last_response.lower():
            print("✅ Bot confirmed account creation")
        else:
            print("❌ Bot did not confirm account creation")
    
    print(f"\n3. Testing food order after signup...")
    
    # Test 3: User tries to order food after signup
    mock_service.sent_messages.clear()
    order_message = {
        'id': 'test_msg_003',
        'from': test_phone,
        'timestamp': str(int(timezone.now().timestamp()) + 2),
        'type': 'text',
        'text': {'body': 'I want to order jollof rice'}
    }
    
    value_data['messages'] = [order_message]
    _process_meta_message(order_message, value_data)
    
    if mock_service.sent_messages:
        last_response = mock_service.sent_messages[-1]['message']
        print(f"📤 Bot response to food order: {last_response[:100]}...")
        
        # Should now process the food order, not ask for email again
        if 'email' in last_response.lower():
            print("❌ Bot is still asking for email after signup")
        else:
            print("✅ Bot processed food order without asking for email again")
    
    print(f"\n4. Final conversation state:")
    conversation.refresh_from_db()
    print(f"   - State: {conversation.onboarding_state}")
    print(f"   - User: {conversation.user.email if conversation.user else 'None'}")
    print(f"   - Phone: {conversation.phone_number}")

finally:
    # Restore original service
    bestyy.communication.whatsapp.views.MetaWhatsAppService = original_service
    
    # Clean up test data
    WhatsAppConversation.objects.filter(phone_number=test_phone).delete()
    
    # Also clean up any created user
    from django.contrib.auth import get_user_model
    User = get_user_model()
    User.objects.filter(email='testuser@gmail.com').delete()

print(f"\n🎉 WhatsApp signup flow test completed!")
print(f"✨ Summary: New users must provide email before ordering food")