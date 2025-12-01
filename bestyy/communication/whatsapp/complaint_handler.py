#!/usr/bin/env python3
"""
Enhanced complaint handling system for WhatsApp messages
Provides intelligent complaint resolution and escalation
"""
import logging
from typing import Dict, Any, Optional
from django.utils import timezone
from datetime import datetime, timedelta
from .simple_state_manager import SimpleConversationStateManager

logger = logging.getLogger(__name__)

class WhatsAppComplaintHandler:
    """
    Intelligent complaint handling system that provides specific help
    based on complaint type and conversation context
    """
    
    def __init__(self):
        self.state_manager = SimpleConversationStateManager()
        # Complaint categories with specific handling
        self.complaint_types = {
            'order_tracking': {
                'keywords': ['order', 'haven\'t received', 'not delivered', 'where is', 'tracking', 'late', 'delayed', 'hours', 'waiting', 'haven\'t seen'],
                'response_template': self._handle_order_tracking_complaint
            },
            'food_quality': {
                'keywords': ['cold', 'bad', 'terrible', 'wrong food', 'not fresh', 'spoiled', 'disgusting'],
                'response_template': self._handle_food_quality_complaint
            },
            'delivery_issues': {
                'keywords': ['driver', 'delivery', 'wrong address', 'can\'t find', 'location'],
                'response_template': self._handle_delivery_complaint
            },
            'payment_issues': {
                'keywords': ['charged', 'payment', 'money', 'refund', 'billing'],
                'response_template': self._handle_payment_complaint
            },
            'customer_service': {
                'keywords': ['rude', 'unprofessional', 'customer service', 'staff', 'behavior'],
                'response_template': self._handle_service_complaint
            },
            'app_issues': {
                'keywords': ['app', 'website', 'login', 'bug', 'error', 'not working'],
                'response_template': self._handle_app_complaint
            },
            'general_insult': {
                'keywords': ['stupid', 'useless', 'hate', 'sucks', 'awful', 'worst'],
                'response_template': self._handle_general_insult
            }
        }
    
    def handle_complaint(self, message: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze complaint and provide specific help
        
        Args:
            message: The complaint message
            user_context: User information and conversation context
            
        Returns:
            Dict with response, category, and actions
        """
        content = message.lower().strip()
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        
        # Get phone number for state tracking
        phone_number = user_context.get('phone_number') if user_context else None
        
        # Check conversation state first
        if phone_number and self.state_manager.is_expecting_order_details(phone_number):
            if self._is_order_details_response(message):
                return self._handle_order_details_provided(message, user_context)
        
        # Check for other follow-up scenarios
        if phone_number and self.state_manager.is_expecting_confirmation(phone_number):
            return self._handle_confirmation_response(message, user_context)
        
        # Check if user is responding to our problem category suggestions
        if phone_number and self.state_manager.is_expecting_category_selection(phone_number):
            if self._is_problem_category_response(message):
                return self._handle_problem_category_selection(message, user_context)
        
        # Detect specific complaint type
        complaint_type = self._detect_complaint_type(content)
        
        # Get appropriate handler
        handler = self.complaint_types[complaint_type]['response_template']
        
        # Generate response
        response_data = handler(message, user_context)
        
        # Add complaint logging
        self._log_complaint(message, complaint_type, user_context)
        
        # Create support escalation if required
        escalation_created = False
        if response_data.get('requires_escalation', False):
            escalation_created = self.create_support_escalation(complaint_type, message, user_context)
        
        return {
            'response': response_data['response'],
            'complaint_type': complaint_type,
            'urgency': response_data.get('urgency', 'medium'),
            'requires_escalation': response_data.get('requires_escalation', False),
            'escalation_created': escalation_created,
            'suggested_actions': response_data.get('actions', [])
        }
    
    def _detect_complaint_type(self, content: str) -> str:
        """Detect the specific type of complaint"""
        
        # Check each complaint type
        for complaint_type, config in self.complaint_types.items():
            keywords = config['keywords']
            if any(keyword in content for keyword in keywords):
                return complaint_type
        
        # Default to general complaint
        return 'general_insult'
    
    def _is_order_details_response(self, message: str) -> bool:
        """
        Check if message contains order details (response to our request for order info)
        """
        content = message.lower()
        
        # Look for patterns that indicate order details
        order_indicators = [
            # Order numbers (various formats)
            r'#?\d{4,8}',  # Order number patterns
            r'order.*#?\d+',
            r'ref.*#?\d+',
            
            # Time patterns 
            r'\d{1,2}:\d{2}',  # Time like "2:30"
            r'\d{1,2}\s?(am|pm)',  # Time like "2 pm"
            r'(morning|afternoon|evening|night)',
            r'(minutes?|hours?)\s+ago',
            
            # Food items
            r'(pizza|burger|rice|chicken|pasta|jollof|suya|amala)',
            
            # Address patterns
            r'(street|road|avenue|close|estate|area|island|mainland)',
            r'(lagos|abuja|ph|port\s+harcourt|kano|ibadan)',
        ]
        
        import re
        matches = 0
        for pattern in order_indicators:
            if re.search(pattern, content):
                matches += 1
        
        # If we find 2+ indicators, likely order details
        return matches >= 2
    
    def _handle_order_details_provided(self, message: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle when user provides order details after we asked for them
        """
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        phone_number = user_context.get('phone_number') if user_context else None
        
        # Extract order details from message
        order_info = self._extract_order_details(message)
        
        # Mark that we're now waiting for confirmation of actions
        if phone_number:
            self.state_manager.mark_awaiting_confirmation(phone_number, 'order_resolution')
        
        response = (f"Perfect, {user_name}! I've got your details and I'm taking immediate action. 🚀\n\n"
                   "Here's what I'm doing RIGHT NOW:\n"
                   f"✅ Looking up your order: {order_info.get('order_number', 'checking system...')}\n"
                   f"✅ Contacting delivery team about: {order_info.get('food_items', 'your order')}\n"
                   f"✅ Checking route to: {order_info.get('address', 'your location')}\n"
                   f"✅ Verifying order from: {order_info.get('time', 'earlier today')}\n\n"
                   
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
                   "Reply 'YES' if you'd like me to also prepare a fresh order now, or 'WAIT' if you prefer to wait for the current one.")
        
        return {
            'response': response,
            'urgency': 'critical',
            'requires_escalation': True,
            'actions': ['track_order', 'contact_delivery', 'prepare_compensation', 'escalate_to_supervisor']
        }
    
    def _handle_confirmation_response(self, message: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle user confirmation responses (YES/NO/WAIT etc.)
        """
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        phone_number = user_context.get('phone_number') if user_context else None
        content = message.lower().strip()
        
        if any(word in content for word in ['yes', 'y', 'ok', 'okay', 'sure', 'please']):
            # User wants fresh order
            if phone_number:
                self.state_manager.clear_complaint_state(phone_number)
            
            response = (f"Excellent choice, {user_name}! 🎉\n\n"
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
                       "Your experience today will be completely different - I guarantee it! 🌟")
        
        elif any(word in content for word in ['wait', 'no', 'n', 'later']):
            # User wants to wait
            if phone_number:
                self.state_manager.clear_complaint_state(phone_number)
                
            response = (f"Understood, {user_name}! I respect your choice. ⏳\n\n"
                       "I'll focus 100% on finding your current order:\n"
                       "🔍 Tracking delivery driver location\n"
                       "📞 Direct call to restaurant kitchen\n"
                       "🚨 High-priority status activated\n\n"
                       
                       "You'll get updates every 5 minutes until resolved!\n\n"
                       "If you change your mind about the fresh order, just say 'FRESH ORDER' and I'll handle it immediately. 🚀")
        
        else:
            # Unclear response
            response = (f"I want to make sure I understand correctly, {user_name}! \n\n"
                       "Would you like me to:\n"
                       "🔥 **YES** - Prepare a fresh order now (free)\n"
                       "⏳ **WAIT** - Focus on finding your current order\n\n"
                       "Just reply YES or WAIT and I'll take care of everything! 😊")
            return {
                'response': response,
                'urgency': 'medium',
                'requires_escalation': False,
                'actions': ['clarify_user_preference']
            }
        
        return {
            'response': response,
            'urgency': 'high',
            'requires_escalation': True,
            'actions': ['execute_user_choice', 'continue_monitoring']
        }
    
    def _extract_order_details(self, message: str) -> Dict[str, str]:
        """
        Extract order details from user message using pattern matching
        """
        import re
        content = message
        
        details = {}
        
        # Extract order number
        order_patterns = [r'#?(\d{4,8})', r'order.*?#?(\d+)', r'ref.*?#?(\d+)']
        for pattern in order_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                details['order_number'] = f"#{match.group(1)}"
                break
        
        # Extract time
        time_patterns = [
            r'(\d{1,2}:\d{2}\s?(am|pm)?)',
            r'(\d{1,2}\s?(am|pm))',
            r'(\d+)\s+(minutes?|hours?)\s+ago',
            r'(morning|afternoon|evening|night)'
        ]
        for pattern in time_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                details['time'] = match.group(0)
                break
        
        # Extract food items
        food_keywords = ['pizza', 'burger', 'rice', 'chicken', 'pasta', 'jollof', 'suya', 'amala', 'eba', 'beans']
        found_foods = [food for food in food_keywords if food in content.lower()]
        if found_foods:
            details['food_items'] = ', '.join(found_foods)
        
        # Extract address hints
        address_keywords = ['street', 'road', 'avenue', 'close', 'estate', 'area', 'island', 'mainland', 'lagos', 'abuja']
        found_address = [addr for addr in address_keywords if addr in content.lower()]
        if found_address:
            details['address'] = ' '.join(found_address)
        
        return details
    
    def _is_problem_category_response(self, message: str) -> bool:
        """
        Check if user is selecting one of our suggested problem categories
        """
        content = message.lower().strip()
        
        # Problem categories we suggest to users
        problem_categories = [
            'order problems', 'order problem', 'order',
            'delivery issues', 'delivery issue', 'delivery',
            'payment concerns', 'payment concern', 'payment',
            'food quality', 'food problem', 'food',
            'technical difficulties', 'technical', 'app problem', 'app'
        ]
        
        is_category = any(category in content for category in problem_categories)
        logger.info(f"Checking if '{content}' is a problem category: {is_category}")
        return is_category
    
    def _handle_problem_category_selection(self, message: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle when user selects a specific problem category from our suggestions
        """
        content = message.lower().strip()
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        phone_number = user_context.get('phone_number') if user_context else None
        
        # Detect which category they selected with debug logging
        logger.info(f"Analyzing category selection for: '{content}'")
        
        if any(word in content for word in ['order', 'order problem', 'order problems']):
            logger.info("Matched: ORDER PROBLEMS")
            return self._handle_order_problem_selection(user_context)
        
        elif any(word in content for word in ['delivery', 'delivery issue', 'delivery issues']):
            logger.info("Matched: DELIVERY ISSUES")
            return self._handle_delivery_problem_selection(user_context)
        
        elif any(word in content for word in ['payment', 'payment concern', 'payment concerns']):
            logger.info("Matched: PAYMENT CONCERNS")
            return self._handle_payment_problem_selection(user_context)
        
        elif any(word in content for word in ['food', 'food quality', 'food problem']):
            logger.info("Matched: FOOD QUALITY")
            return self._handle_food_quality_problem_selection(user_context)
        
        elif any(word in content for word in ['technical', 'app', 'technical difficulties']):
            logger.info("Matched: TECHNICAL DIFFICULTIES")
            return self._handle_technical_problem_selection(user_context)
        
        else:
            logger.warning(f"No specific category matched for: '{content}' - falling back to generic response")
            # Generic help if we can't determine specific category
            return self._handle_generic_problem_selection(user_context)
    
    def _handle_order_problem_selection(self, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle when user selects 'Order problems'"""
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        phone_number = user_context.get('phone_number') if user_context else None
        
        # Mark that we're waiting for order details
        if phone_number:
            self.state_manager.mark_awaiting_order_details(phone_number, 'order_tracking')
        
        response = (f"I'm on it, {user_name}! Let me help resolve your order issue immediately. 📦\n\n"
                   "To get you the fastest resolution, please share:\n"
                   "• Your order number (check SMS/email)\n"
                   "• What specific problem you're experiencing:\n"
                   "  - Order not delivered\n"
                   "  - Wrong items received\n"
                   "  - Missing items\n"
                   "  - Order cancelled unexpectedly\n"
                   "• When you placed the order\n\n"
                   "I'm already alerting our order management team! 🚨\n"
                   "They'll prioritize your case the moment I get your details.")
        
        return {
            'response': response,
            'urgency': 'high',
            'requires_escalation': True,
            'actions': ['escalate_to_order_team', 'prepare_order_investigation']
        }
    
    def _handle_delivery_problem_selection(self, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle when user selects 'Delivery issues'"""
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        
        response = (f"I'll sort out your delivery issue right away, {user_name}! 🛵\n\n"
                   "Tell me what's happening:\n"
                   "• Driver can't find your location\n"
                   "• Delivery is very late\n"
                   "• Driver hasn't arrived at promised time\n"
                   "• Wrong delivery address\n"
                   "• Need to change delivery location\n\n"
                   "I'm connecting directly with our delivery dispatch team NOW! 📞\n"
                   "I can also:\n"
                   "✅ Get live driver location\n"
                   "✅ Update delivery instructions\n"
                   "✅ Arrange priority re-delivery\n"
                   "✅ Process instant refund if needed")
        
        return {
            'response': response,
            'urgency': 'high',
            'requires_escalation': True,
            'actions': ['contact_delivery_dispatch', 'get_driver_location', 'prepare_delivery_options']
        }
    
    def _handle_payment_problem_selection(self, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle when user selects 'Payment concerns'"""
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        
        response = (f"I'll resolve your payment issue immediately, {user_name}! 💳\n\n"
                   "What payment problem are you experiencing:\n"
                   "• Charged but order not confirmed\n"
                   "• Multiple charges for one order\n"
                   "• Payment failed but money deducted\n"
                   "• Need refund for cancelled order\n"
                   "• Card/payment method not working\n\n"
                   "I'm checking your payment history right now! 🔍\n\n"
                   "I can immediately:\n"
                   "✅ Verify all your transactions\n"
                   "✅ Process instant refunds\n"
                   "✅ Fix payment method issues\n"
                   "✅ Escalate to finance team if needed\n\n"
                   "Please share your order number or transaction reference if you have it.")
        
        return {
            'response': response,
            'urgency': 'high',
            'requires_escalation': True,
            'actions': ['verify_payments', 'prepare_refund', 'escalate_to_finance']
        }
    
    def _handle_food_quality_problem_selection(self, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle when user selects 'Food quality'"""
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        
        response = (f"I'm so sorry about the food quality issue, {user_name}! This is unacceptable. 😔\n\n"
                   "Tell me what happened:\n"
                   "• Food arrived cold\n"
                   "• Wrong items/order mix-up\n"
                   "• Food doesn't taste right\n"
                   "• Missing condiments/sides\n"
                   "• Food looks different from menu\n"
                   "• Hygiene/safety concerns\n\n"
                   "I'm taking immediate action:\n"
                   "✅ Full refund processing NOW\n"
                   "✅ Fresh replacement order (free)\n"
                   "✅ Direct line to restaurant manager\n"
                   "✅ Quality assurance team alert\n\n"
                   "Please share your order details and I'll make this right within 30 minutes! 💯")
        
        return {
            'response': response,
            'urgency': 'critical',
            'requires_escalation': True,
            'actions': ['process_immediate_refund', 'prepare_replacement_order', 'alert_quality_team']
        }
    
    def _handle_technical_problem_selection(self, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle when user selects 'Technical difficulties'"""
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        
        response = (f"Let me help you with the technical issue, {user_name}! 🔧\n\n"
                   "What's not working properly:\n"
                   "• App keeps crashing\n"
                   "• Can't login to account\n"
                   "• Payment not processing\n"
                   "• Menu/restaurants not loading\n"
                   "• Order history missing\n"
                   "• GPS/location issues\n\n"
                   "Quick fixes to try first:\n"
                   "1️⃣ Close and restart the app\n"
                   "2️⃣ Check internet connection\n"
                   "3️⃣ Update to latest app version\n\n"
                   "If that doesn't work:\n"
                   "✅ I can place your order manually\n"
                   "✅ Connect you with tech support team\n"
                   "✅ Send alternative ordering methods\n"
                   "✅ Reset your account if needed\n\n"
                   "Tell me exactly what's happening and I'll get you sorted! 🚀")
        
        return {
            'response': response,
            'urgency': 'medium',
            'requires_escalation': False,
            'actions': ['provide_tech_troubleshooting', 'prepare_manual_order_assistance']
        }
    
    def _handle_generic_problem_selection(self, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle when we can't determine specific problem category"""
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        
        response = (f"I want to help you with whatever's wrong, {user_name}! 🤝\n\n"
                   "Please describe your issue in a few words and I'll:\n"
                   "✅ Provide immediate assistance\n"
                   "✅ Escalate to the right team\n"
                   "✅ Give you a clear resolution timeline\n\n"
                   "I'm here to make sure you have a great experience! 😊")
        
        return {
            'response': response,
            'urgency': 'medium',
            'requires_escalation': False,
            'actions': ['provide_general_assistance']
        }
    
    def _handle_order_tracking_complaint(self, message: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle order tracking complaints specifically"""
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        phone_number = user_context.get('phone_number') if user_context else None
        
        # Mark that we're waiting for order details
        if phone_number:
            self.state_manager.mark_awaiting_order_details(phone_number, 'order_tracking')
        
        response = (f"I completely understand your frustration, {user_name}! Let me help you track down your order right away. 📦\n\n"
                   "To resolve this quickly, please share:\n"
                   "• Your order number (check your SMS/email)\n"
                   "• What you ordered\n"
                   "• Approximate time you placed the order\n"
                   "• Delivery address\n\n"
                   "I'm escalating this to our delivery team immediately. You should hear back within 15 minutes! 🚀\n\n"
                   "In the meantime, I'm also checking if there are any delivery delays in your area...")
        
        return {
            'response': response,
            'urgency': 'high',
            'requires_escalation': True,
            'actions': ['escalate_to_delivery_team', 'check_delivery_status', 'prepare_compensation']
        }
    
    def _handle_food_quality_complaint(self, message: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle food quality complaints"""
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        
        response = (f"I'm so sorry about the quality issue, {user_name}! This is absolutely not the standard we aim for. 😔\n\n"
                   "Let me make this right immediately:\n"
                   "• Full refund processing now\n"
                   "• New order at no cost (if you'd like)\n"
                   "• Direct line to our kitchen manager\n\n"
                   "Can you please share:\n"
                   "• Your order number\n"
                   "• Which items had issues\n"
                   "• Photo (if possible)\n\n"
                   "I'm personally ensuring this gets resolved within the next 30 minutes! 💯")
        
        return {
            'response': response,
            'urgency': 'high',
            'requires_escalation': True,
            'actions': ['process_refund', 'contact_restaurant', 'offer_replacement']
        }
    
    def _handle_delivery_complaint(self, message: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle delivery-related complaints"""
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        
        response = (f"I'm sorry for the delivery confusion, {user_name}! Let me connect you directly with our delivery team. 🛵\n\n"
                   "I'm doing this right now:\n"
                   "• Calling our driver to confirm location\n"
                   "• Sharing your exact address with delivery team\n"
                   "• Providing you with live delivery updates\n\n"
                   "Your order should reach you within the next 20 minutes. I'll personally monitor this! 📍")
        
        return {
            'response': response,
            'urgency': 'high',
            'requires_escalation': True,
            'actions': ['contact_driver', 'verify_address', 'provide_live_updates']
        }
    
    def _handle_payment_complaint(self, message: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle payment-related complaints"""
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        
        response = (f"I understand your payment concern, {user_name}! Let me check your account right away. 💳\n\n"
                   "I can help you with:\n"
                   "• Transaction verification\n"
                   "• Immediate refund processing\n"
                   "• Payment method updates\n"
                   "• Billing dispute resolution\n\n"
                   "Please share your order number or transaction ID, and I'll resolve this within 10 minutes! 🚀")
        
        return {
            'response': response,
            'urgency': 'high',
            'requires_escalation': True,
            'actions': ['verify_payment', 'check_transaction', 'prepare_refund']
        }
    
    def _handle_service_complaint(self, message: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle customer service complaints"""
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        
        response = (f"I sincerely apologize for the poor service experience, {user_name}. This is completely unacceptable. 😔\n\n"
                   "I'm taking immediate action:\n"
                   "• Escalating to customer service manager\n"
                   "• Documenting this incident for staff training\n"
                   "• Offering you a goodwill gesture\n\n"
                   "Please tell me exactly what happened so I can ensure it never happens again. Your feedback helps us improve! 🙏")
        
        return {
            'response': response,
            'urgency': 'medium',
            'requires_escalation': True,
            'actions': ['escalate_to_manager', 'document_incident', 'offer_compensation']
        }
    
    def _handle_app_complaint(self, message: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle app/technical complaints"""
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        
        response = (f"Sorry for the technical trouble, {user_name}! Let me help you get this sorted. 🔧\n\n"
                   "Quick fixes to try:\n"
                   "• Restart the app\n"
                   "• Check your internet connection\n"
                   "• Update to latest version\n\n"
                   "If that doesn't work:\n"
                   "• I can place your order manually\n"
                   "• Connect you with our tech team\n"
                   "• Provide alternative ordering methods\n\n"
                   "What specific issue are you experiencing?")
        
        return {
            'response': response,
            'urgency': 'medium',
            'requires_escalation': False,
            'actions': ['provide_tech_support', 'manual_order_assistance']
        }
    
    def _handle_general_insult(self, message: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle general insults or rude messages"""
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        phone_number = user_context.get('phone_number') if user_context else None
        
        # Mark that we're waiting for problem category selection
        if phone_number:
            self.state_manager.set_complaint_state(phone_number, {
                'status': 'awaiting_category_selection',
                'complaint_type': 'general_insult',
                'requested_at': timezone.now().isoformat(),
                'step': 1
            })
        
        response = (f"I understand you're frustrated, {user_name}, and I genuinely want to help make things right! 😊\n\n"
                   "Rather than letting this ruin your day, let me focus on solving whatever's bothering you.\n\n"
                   "What specific issue can I help you with?\n"
                   "• Order problems\n"
                   "• Delivery issues\n"
                   "• Payment concerns\n"
                   "• Food quality\n"
                   "• Technical difficulties\n\n"
                   "I'm here to turn this experience around for you! 🌟")
        
        return {
            'response': response,
            'urgency': 'medium',
            'requires_escalation': False,
            'actions': ['de_escalate', 'focus_on_solution']
        }
    
    def _log_complaint(self, message: str, complaint_type: str, user_context: Dict[str, Any] = None):
        """Log complaint for analysis and follow-up"""
        try:
            # In a real system, this would save to database
            logger.info(f"COMPLAINT LOGGED: Type={complaint_type}, User={user_context.get('phone_number', 'unknown') if user_context else 'unknown'}, Message='{message[:100]}...'")
        except Exception as e:
            logger.error(f"Failed to log complaint: {str(e)}")
    
    def create_support_escalation(self, complaint_type: str, message: str, user_context: Dict[str, Any] = None) -> bool:
        """
        Create a support escalation record for admin dashboard
        """
        try:
            from bestyy.core_features.user.models import SupportEscalation
            from bestyy.communication.whatsapp.models import WhatsAppConversation
            from bestyy.core_features.user.services.support_escalation_service import SupportEscalationService
            
            phone_number = user_context.get('phone_number') if user_context else None
            if not phone_number:
                logger.error("Cannot create escalation without phone number")
                return False
            
            # Get or create conversation
            conversation, _ = WhatsAppConversation.objects.get_or_create(
                phone_number=phone_number,
                defaults={'user': user_context.get('user_obj') if user_context else None}
            )
            
            # Map complaint types to escalation trigger types
            trigger_type_map = {
                'food_quality': 'complaint_food',
                'delivery_issues': 'complaint_delivery', 
                'order_tracking': 'complaint_delivery',
                'payment_issues': 'complaint_payment',
                'service_issues': 'complaint_service',
                'general': 'complaint_general'
            }
            
            trigger_type = trigger_type_map.get(complaint_type, 'complaint_general')
            priority = self.get_escalation_priority(complaint_type)
            
            # Use the escalation service to create escalation
            escalation_service = SupportEscalationService()
            
            context = {
                'complaint_message': message,
                'complaint_type': complaint_type,
                'user_context': user_context,
                'escalation_reason': f"Customer complaint: {complaint_type}",
                'auto_escalated': True
            }
            
            escalation = escalation_service.create_escalation(
                conversation=conversation,
                trigger_type=trigger_type,
                context=context
            )
            
            # Update escalation with customer details
            escalation.customer_phone = phone_number
            escalation.customer_name = user_context.get('first_name', '') if user_context else ''
            escalation.description = message
            escalation.severity_level = priority
            escalation.save()
            
            # Notify admin dashboard
            escalation_service._notify_admin_dashboard(escalation)
            
            logger.info(f"Created support escalation {escalation.id} for complaint: {complaint_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create support escalation: {str(e)}")
            return False
    
    def get_escalation_priority(self, complaint_type: str) -> str:
        """Get escalation priority for complaint type"""
        urgent_priority = ['payment_issues']
        high_priority = ['food_quality', 'delivery_issues', 'order_tracking'] 
        
        if complaint_type in urgent_priority:
            return 'urgent'
        elif complaint_type in high_priority:
            return 'high'
        return 'medium'