#!/usr/bin/env python3
"""
Detailed test to debug the complaint flow step by step
"""
import os
import django
import sys

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

def test_complaint_conversation_flow():
    """Test the exact conversation flow step by step"""
    print("=== DETAILED COMPLAINT CONVERSATION FLOW TEST ===")
    
    from bestyy.communication.whatsapp.ai_service import WhatsAppAIService
    from bestyy.communication.whatsapp.models import WhatsAppConversation, WhatsAppMessage
    from bestyy.communication.whatsapp.complaint_handler import WhatsAppComplaintHandler
    
    # Clean up any existing test data
    WhatsAppConversation.objects.filter(phone_number='+1234567890').delete()
    
    # Initialize services
    ai_service = WhatsAppAIService()
    complaint_handler = WhatsAppComplaintHandler()
    
    # Create fresh conversation
    conversation = WhatsAppConversation.objects.create(phone_number='+1234567890', is_active=True)
    
    print(f"\n--- STEP 1: User sends complaint ---")
    message1 = WhatsAppMessage.objects.create(
        conversation=conversation,
        message_id='test_msg_1',
        content='you are stupid',
        message_type='text',
        direction='inbound'
    )
    
    result1 = ai_service.process_message(message1, context={'user_exists': True})
    print(f"Message: '{message1.content}'")
    print(f"Category: {result1.get('category', 'unknown')}")
    print(f"Response: {result1.get('response', 'No response')[:150]}...")
    
    # Check if complaint state was set
    phone = conversation.phone_number
    print(f"Phone number: {phone}")
    try:
        expecting = complaint_handler.state_manager.is_expecting_category_selection(phone)
        print(f"Is expecting category selection: {expecting}")
        
        # Debug state manager
        state = complaint_handler.state_manager._states.get(phone)
        print(f"Current state in manager: {state}")
    except Exception as e:
        print(f"Error checking state: {e}")
    
    print(f"\n--- STEP 2: User selects payment concerns ---")
    message2 = WhatsAppMessage.objects.create(
        conversation=conversation,
        message_id='test_msg_2',
        content='payment concerns',
        message_type='text', 
        direction='inbound'
    )
    
    result2 = ai_service.process_message(message2, context={'user_exists': True})
    print(f"Message: '{message2.content}'")
    print(f"Category: {result2.get('category', 'unknown')}")
    print(f"Response: {result2.get('response', 'No response')[:150]}...")
    
    # Check if it's being recognized as a problem category
    is_category = complaint_handler._is_problem_category_response(message2.content)
    print(f"Is problem category response: {is_category}")
    
    # Test direct complaint handler call
    print(f"\n--- STEP 3: Direct complaint handler test ---")
    user_context = {
        'phone_number': phone,
        'first_name': 'TestUser'
    }
    
    direct_result = complaint_handler.handle_complaint('payment concerns', user_context)
    print(f"Direct complaint handler response: {direct_result.get('response', 'No response')[:150]}...")
    
    # Success check
    if "payment" in result2.get('response', '').lower() and "charged" in result2.get('response', '').lower():
        print("\n✅ SUCCESS: Payment-specific complaint response detected")
    else:
        print("\n❌ FAILURE: Generic response instead of payment-specific complaint response")
        print(f"Expected: Payment-specific response with options")
        print(f"Got: {result2.get('response', 'No response')}")
    
    # Clean up
    conversation.delete()

if __name__ == "__main__":
    test_complaint_conversation_flow()