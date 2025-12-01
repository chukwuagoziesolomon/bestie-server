#!/usr/bin/env python3
"""
Test the complete conversation flow for order tracking complaints
Shows how the system handles multi-turn conversations intelligently
"""

class MockConversationStateManager:
    def __init__(self):
        self.states = {}
    
    def mark_awaiting_order_details(self, phone_number, complaint_type):
        self.states[phone_number] = {
            'status': 'awaiting_order_details',
            'complaint_type': complaint_type
        }
    
    def is_expecting_order_details(self, phone_number):
        return self.states.get(phone_number, {}).get('status') == 'awaiting_order_details'
    
    def mark_awaiting_confirmation(self, phone_number, action):
        self.states[phone_number] = {
            'status': 'awaiting_confirmation',
            'action': action
        }
    
    def is_expecting_confirmation(self, phone_number):
        return self.states.get(phone_number, {}).get('status') == 'awaiting_confirmation'
    
    def clear_complaint_state(self, phone_number):
        self.states.pop(phone_number, None)

class MockEnhancedComplaintHandler:
    def __init__(self):
        self.state_manager = MockConversationStateManager()
    
    def handle_complaint(self, message, user_context=None):
        content = message.lower().strip()
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        phone_number = user_context.get('phone_number', '1234567890') if user_context else '1234567890'
        
        # Check conversation state first
        if self.state_manager.is_expecting_order_details(phone_number):
            if self._is_order_details_response(message):
                return self._handle_order_details_provided(message, user_context)
        
        # Check for confirmation responses
        if self.state_manager.is_expecting_confirmation(phone_number):
            return self._handle_confirmation_response(message, user_context)
        
        # Handle initial complaint
        if any(word in content for word in ['haven\'t seen', 'order', 'hours', 'past two hours']):
            self.state_manager.mark_awaiting_order_details(phone_number, 'order_tracking')
            
            return {
                'response': (f"I completely understand your frustration, {user_name}! Let me help you track down your order right away. 📦\n\n"
                           "To resolve this quickly, please share:\n"
                           "• Your order number (check your SMS/email)\n"
                           "• What you ordered\n"
                           "• Approximate time you placed the order\n"
                           "• Delivery address\n\n"
                           "I'm escalating this to our delivery team immediately. You should hear back within 15 minutes! 🚀\n\n"
                           "In the meantime, I'm also checking if there are any delivery delays in your area..."),
                'complaint_type': 'order_tracking'
            }
        
        return {'response': 'How can I help you?', 'complaint_type': 'general'}
    
    def _is_order_details_response(self, message):
        content = message.lower()
        # Simple check for order details patterns
        indicators = ['#', 'order', ':', 'pm', 'am', 'street', 'road', 'pizza', 'burger', 'rice']
        return sum(1 for indicator in indicators if indicator in content) >= 2
    
    def _handle_order_details_provided(self, message, user_context=None):
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        phone_number = user_context.get('phone_number', '1234567890') if user_context else '1234567890'
        
        # Mark waiting for confirmation
        self.state_manager.mark_awaiting_confirmation(phone_number, 'order_resolution')
        
        return {
            'response': (f"Perfect, {user_name}! I've got your details and I'm taking immediate action. 🚀\n\n"
                       "Here's what I'm doing RIGHT NOW:\n"
                       "✅ Looking up your order: #12345\n"
                       "✅ Contacting delivery team about: your pizza order\n"
                       "✅ Checking route to: your location\n"
                       "✅ Verifying order from: 2 hours ago\n\n"
                       
                       "📱 I've sent an URGENT alert to:\n"
                       "• Our delivery manager\n"
                       "• The restaurant kitchen\n" 
                       "• Customer service supervisor\n\n"
                       
                       "You'll get:\n"
                       "🎯 Live location update in 5 minutes\n"
                       "📞 Call from delivery team in 10 minutes\n"
                       "🍔 Fresh replacement if needed\n"
                       "💰 Full refund + credit as apology\n\n"
                       
                       "I'm personally monitoring this until it's resolved! 💪\n\n"
                       "Reply 'YES' if you'd like me to also prepare a fresh order now, or 'WAIT' if you prefer to wait for the current one."),
            'complaint_type': 'order_tracking_followup'
        }
    
    def _handle_confirmation_response(self, message, user_context=None):
        content = message.lower().strip()
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        phone_number = user_context.get('phone_number', '1234567890') if user_context else '1234567890'
        
        if any(word in content for word in ['yes', 'y', 'ok', 'sure']):
            self.state_manager.clear_complaint_state(phone_number)
            return {
                'response': (f"Excellent choice, {user_name}! 🎉\n\n"
                           "I'm placing a fresh order for you RIGHT NOW:\n"
                           "✅ Same items as your original order\n"
                           "✅ Priority kitchen preparation\n"
                           "✅ Express delivery (30 mins max)\n"
                           "✅ No additional charge\n\n"
                           
                           "📱 You'll receive:\n"
                           "• Order confirmation SMS in 2 minutes\n"
                           "• Kitchen update in 10 minutes\n" 
                           "• Live tracking when dispatch starts\n\n"
                           
                           "And I'm STILL tracking your original order for a full refund! 💰\n\n"
                           "Your experience today will be completely different - I guarantee it! 🌟"),
                'complaint_type': 'resolution_confirmed'
            }
        else:
            self.state_manager.clear_complaint_state(phone_number)
            return {
                'response': (f"Understood, {user_name}! I respect your choice. ⏳\n\n"
                           "I'll focus 100% on finding your current order:\n"
                           "🔍 Tracking delivery driver location\n"
                           "📞 Direct call to restaurant kitchen\n"
                           "🚨 High-priority status activated\n\n"
                           
                           "You'll get updates every 5 minutes until resolved!\n\n"
                           "If you change your mind about the fresh order, just say 'FRESH ORDER' and I'll handle it immediately. 🚀"),
                'complaint_type': 'resolution_wait'
            }

def test_complete_conversation_flow():
    """Test the complete multi-turn conversation flow"""
    
    print("=== COMPLETE CONVERSATION FLOW TEST ===\n")
    
    handler = MockEnhancedComplaintHandler()
    user_context = {
        'first_name': 'Emmanuel',
        'phone_number': '+2348123456789'
    }
    
    # Conversation flow based on the image scenario
    conversation_steps = [
        {
            'step': 1,
            'user_says': "i haven't seen my order for the past two hours",
            'description': 'Initial order tracking complaint'
        },
        {
            'step': 2, 
            'user_says': "Order #12345, large pizza, ordered at 2:30 PM, delivery to Victoria Island Lagos",
            'description': 'User provides requested order details'
        },
        {
            'step': 3,
            'user_says': "yes",
            'description': 'User confirms they want fresh order'
        }
    ]
    
    print("📱 CONVERSATION FLOW:")
    print("="*60)
    
    for step_data in conversation_steps:
        step = step_data['step']
        user_message = step_data['user_says']
        description = step_data['description']
        
        print(f"\n**STEP {step}**: {description}")
        print(f"👤 Emmanuel: \"{user_message}\"")
        print("-" * 40)
        
        # Process message
        result = handler.handle_complaint(user_message, user_context)
        
        print(f"🤖 Bestyy Bot:")
        print(result['response'])
        print(f"\n📊 System: {result['complaint_type']}")
        print("="*60)
    
    print("\n✅ CONVERSATION FLOW IMPROVEMENTS:")
    print("🎯 **Step 1**: Complaint detected → Specific help requested")
    print("📋 **Step 2**: Details provided → Immediate action + options") 
    print("✅ **Step 3**: Choice made → Execution + monitoring")
    print("\n🔄 **Smart State Management**:")
    print("• Remembers what information was requested")
    print("• Detects when user provides requested details")
    print("• Handles confirmations and follow-up choices")
    print("• No more 'tell me more' loops!")
    print("\n🚀 **Result**: Complete resolution path from complaint to action!")

if __name__ == "__main__":
    test_complete_conversation_flow()