#!/usr/bin/env python3
"""
Debug test for complaint handling system to check category recognition
"""
import os
import django
import sys

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.communication.whatsapp.complaint_handler import WhatsAppComplaintHandler

def test_payment_concerns_flow():
    """Test the exact flow from user's screenshot"""
    print("=== TESTING PAYMENT CONCERNS FLOW ===")
    
    # Test the AI Service integration
    from bestyy.communication.whatsapp.ai_service import WhatsAppAIService
    from bestyy.communication.whatsapp.models import WhatsAppConversation, WhatsAppMessage
    
    print("\n--- Testing AI Service Integration ---")
    ai_service = WhatsAppAIService()
    
    # Create test conversation and message
    conversation, created = WhatsAppConversation.objects.get_or_create(
        phone_number='+1234567890',
        defaults={'is_active': True}
    )
    
    # Test complaint detection
    message1 = WhatsAppMessage.objects.create(
        conversation=conversation,
        message_id='test1',
        content='you are stupid',
        message_type='text',
        direction='inbound'
    )
    
    result1 = ai_service.process_message(message1, context={'user_exists': True})
    print(f"1. Complaint 'you are stupid':")
    print(f"   Response: {result1.get('response', 'No response')[:200]}...")
    
    # Test payment concerns selection
    message2 = WhatsAppMessage.objects.create(
        conversation=conversation,
        message_id='test2', 
        content='payment concerns',
        message_type='text',
        direction='inbound'
    )
    
    result2 = ai_service.process_message(message2, context={'user_exists': True})
    print(f"\n2. Selection 'payment concerns':")
    print(f"   Response: {result2.get('response', 'No response')[:200]}...")
    
    # Check success
    if "payment" in result2.get('response', '').lower():
        print("✅ SUCCESS: AI Service properly detected and handled complaint")
    else:
        print("❌ FAILURE: AI Service didn't handle complaint properly")
    
    # Clean up
    conversation.delete()

def test_all_categories():
    """Test all complaint categories"""
    print("\n\n=== TESTING ALL CATEGORIES ===")
    
    handler = WhatsAppComplaintHandler()
    user_context = {
        'phone_number': '+1234567890',
        'first_name': 'TestUser'
    }
    
    # First trigger complaint mode
    print("\nTriggering complaint mode...")
    handler.handle_complaint("i'm having issues", user_context)
    
    categories = [
        "order problems",
        "delivery issues", 
        "payment concerns",
        "food quality",
        "technical difficulties"
    ]
    
    for category in categories:
        print(f"\nTesting: '{category}'")
        response = handler.handle_complaint(category, user_context)
        response_text = response.get('response', '')
        
        # Check if response is category-specific
        if len(response_text) > 100:  # Specific responses are longer
            print(f"✅ {category}: Got specific response")
        else:
            print(f"❌ {category}: Got generic response")
            print(f"   Response: {response_text[:100]}...")

if __name__ == "__main__":
    # Test the specific issue from user's screenshot
    test_payment_concerns_flow()
    
    # Test all categories
    test_all_categories()