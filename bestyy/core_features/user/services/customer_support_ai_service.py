"""
Customer support AI service using OpenRouter LLM for intelligent customer interactions
"""
import requests
import json
import logging
from typing import Dict, List, Optional
from django.conf import settings
from django.utils import timezone
from ..models import Order, User

logger = logging.getLogger(__name__)


class CustomerSupportAIService:
    """
    AI-powered customer support service using OpenRouter LLM
    """
    
    def __init__(self):
        # OpenRouter LLM configuration
        self.openrouter_api_key = getattr(settings, 'OPENROUTER_API_KEY', None)
        self.openrouter_base_url = "https://openrouter.ai/api/v1"
        self.app_url = getattr(settings, 'OPENROUTER_APP_URL', 'https://bestyy.com')
        self.app_name = getattr(settings, 'OPENROUTER_APP_NAME', 'Bestyy Customer Support')
        
        # Support categories
        self.support_categories = [
            'order_status', 'delivery_time', 'complaint', 'cancellation',
            'modification', 'payment_issue', 'refund_request', 'general_inquiry'
        ]
    
    def handle_customer_inquiry(self, customer_message: str, customer_id: int = None, order_id: int = None) -> Dict:
        """
        Handle customer inquiry using AI
        
        Args:
            customer_message: Customer's message
            customer_id: Customer ID (optional)
            order_id: Order ID (optional)
            
        Returns:
            Dictionary with AI response and actions
        """
        try:
            if not self.openrouter_api_key:
                return {'error': 'OpenRouter API key not configured'}
            
            # Get customer and order context
            context = self._get_customer_context(customer_id, order_id)
            
            # Generate AI response
            ai_response = self._generate_support_response(customer_message, context)
            
            # Determine follow-up actions
            actions = self._determine_follow_up_actions(ai_response, context)
            
            return {
                'success': True,
                'customer_message': customer_message,
                'ai_response': ai_response,
                'follow_up_actions': actions,
                'context': context,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error handling customer inquiry: {str(e)}")
            return {'error': str(e)}
    
    def _get_customer_context(self, customer_id: int = None, order_id: int = None) -> Dict:
        """
        Get customer and order context
        """
        try:
            context = {
                'customer_id': customer_id,
                'order_id': order_id,
                'customer_info': {},
                'order_info': {},
                'delivery_status': {}
            }
            
            # Get customer information
            if customer_id:
                try:
                    customer = User.objects.get(id=customer_id)
                    context['customer_info'] = {
                        'name': f"{customer.first_name} {customer.last_name}".strip(),
                        'email': customer.email,
                        'phone': getattr(customer, 'phone', 'Not provided')
                    }
                except User.DoesNotExist:
                    pass
            
            # Get order information
            if order_id:
                try:
                    order = Order.objects.get(id=order_id)
                    context['order_info'] = {
                        'order_id': order.id,
                        'status': order.status,
                        'total_price': float(order.total_price),
                        'order_time': order.order_placed_at.isoformat(),
                        'vendor_name': order.vendor.business_name,
                        'delivery_address': order.delivery_address
                    }
                    
                    # Calculate elapsed time
                    elapsed = timezone.now() - order.order_placed_at
                    context['delivery_status'] = {
                        'elapsed_minutes': int(elapsed.total_seconds() / 60),
                        'estimated_delivery': self._estimate_delivery_time(order),
                        'courier_assigned': order.courier is not None,
                        'courier_name': f"{order.courier.user.first_name} {order.courier.user.last_name}".strip() if order.courier else None
                    }
                except Order.DoesNotExist:
                    pass
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting customer context: {str(e)}")
            return {}
    
    def _generate_support_response(self, customer_message: str, context: Dict) -> Dict:
        """
        Generate AI response for customer support
        """
        try:
            # Build context string
            context_str = self._build_context_string(context)
            
            prompt = f"""
You are a helpful customer support AI for Bestyy, a food delivery service. 

CUSTOMER MESSAGE: "{customer_message}"

CONTEXT:
{context_str}

Provide a helpful, empathetic response. Consider:
1. The customer's concern or question
2. Current order status and delivery progress
3. Appropriate tone based on urgency
4. Clear next steps or information

Respond with JSON:
{{
    "response_type": "information|apology|confirmation|escalation",
    "tone": "friendly|empathetic|urgent|professional",
    "response_message": "your response to the customer",
    "confidence": 0.0-1.0,
    "suggested_actions": ["list of suggested actions"],
    "escalation_needed": true/false,
    "follow_up_required": true/false,
    "estimated_resolution_time": "immediate|5-10 min|10-30 min|1+ hour"
}}

Guidelines:
- Be empathetic and understanding
- Provide clear, actionable information
- Acknowledge delays or problems
- Offer solutions when possible
- Escalate urgent issues
- Keep responses concise but helpful
"""
            
            # Call OpenRouter LLM
            response = requests.post(
                url=f"{self.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self.app_url,
                    "X-Title": self.app_name,
                },
                data=json.dumps({
                    "model": "meta-llama/llama-3.2-3b-instruct:free",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a helpful customer support AI for a food delivery service. Provide empathetic, clear, and actionable responses. Always respond with valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500
                })
            )
            
            if response.status_code == 200:
                response_data = response.json()
                ai_response = response_data['choices'][0]['message']['content'].strip()
                
                try:
                    return json.loads(ai_response)
                except json.JSONDecodeError:
                    # Fallback response
                    return {
                        "response_type": "information",
                        "tone": "friendly",
                        "response_message": "Thank you for contacting us. We're looking into your inquiry and will get back to you shortly.",
                        "confidence": 0.5,
                        "suggested_actions": ["Review customer inquiry", "Check order status"],
                        "escalation_needed": False,
                        "follow_up_required": True,
                        "estimated_resolution_time": "10-30 min"
                    }
            else:
                logger.error(f"OpenRouter API error: {response.status_code}")
                return {'error': 'AI service unavailable'}
                
        except Exception as e:
            logger.error(f"Error generating support response: {str(e)}")
            return {'error': str(e)}
    
    def _build_context_string(self, context: Dict) -> str:
        """
        Build context string for AI prompt
        """
        context_parts = []
        
        # Customer info
        if context.get('customer_info'):
            customer = context['customer_info']
            context_parts.append(f"Customer: {customer.get('name', 'Unknown')} ({customer.get('email', 'No email')})")
        
        # Order info
        if context.get('order_info'):
            order = context['order_info']
            context_parts.append(f"Order #{order.get('order_id', 'N/A')}: {order.get('status', 'Unknown status')}")
            context_parts.append(f"Vendor: {order.get('vendor_name', 'Unknown')}")
            context_parts.append(f"Total: ₦{order.get('total_price', 0)}")
            context_parts.append(f"Order Time: {order.get('order_time', 'Unknown')}")
        
        # Delivery status
        if context.get('delivery_status'):
            delivery = context['delivery_status']
            context_parts.append(f"Elapsed Time: {delivery.get('elapsed_minutes', 0)} minutes")
            context_parts.append(f"Estimated Delivery: {delivery.get('estimated_delivery', 'Unknown')}")
            if delivery.get('courier_assigned'):
                context_parts.append(f"Courier: {delivery.get('courier_name', 'Assigned')}")
            else:
                context_parts.append("Courier: Not yet assigned")
        
        return "\n".join(context_parts) if context_parts else "No context available"
    
    def _estimate_delivery_time(self, order: Order) -> str:
        """
        Estimate delivery time based on order status
        """
        try:
            elapsed = timezone.now() - order.order_placed_at
            elapsed_minutes = int(elapsed.total_seconds() / 60)
            
            if order.status == 'pending':
                return "15-20 minutes"
            elif order.status == 'confirmed':
                return "10-15 minutes"
            elif order.status == 'preparing':
                return "5-10 minutes"
            elif order.status == 'ready':
                return "5-10 minutes"
            elif order.status == 'assigned':
                return "5-10 minutes"
            elif order.status == 'picked_up':
                return "5-10 minutes"
            elif order.status == 'out_for_delivery':
                return "5-10 minutes"
            else:
                return "Unknown"
                
        except Exception as e:
            logger.error(f"Error estimating delivery time: {str(e)}")
            return "Unknown"
    
    def _determine_follow_up_actions(self, ai_response: Dict, context: Dict) -> List[Dict]:
        """
        Determine follow-up actions based on AI response
        """
        try:
            actions = []
            
            # Check if escalation is needed
            if ai_response.get('escalation_needed'):
                actions.append({
                    'type': 'escalate',
                    'priority': 'high',
                    'description': 'Escalate to human support',
                    'reason': 'AI detected urgent issue requiring human intervention'
                })
            
            # Check if follow-up is required
            if ai_response.get('follow_up_required'):
                actions.append({
                    'type': 'follow_up',
                    'priority': 'medium',
                    'description': 'Schedule follow-up check',
                    'estimated_time': ai_response.get('estimated_resolution_time', '10-30 min')
                })
            
            # Check for specific order actions
            if context.get('order_id'):
                order_id = context['order_id']
                
                # Check if order needs status update
                if context.get('delivery_status', {}).get('elapsed_minutes', 0) > 20:
                    actions.append({
                        'type': 'check_delivery_status',
                        'priority': 'high',
                        'description': 'Check delivery status - order is overdue',
                        'order_id': order_id
                    })
                
                # Check if courier needs to be contacted
                if not context.get('delivery_status', {}).get('courier_assigned'):
                    actions.append({
                        'type': 'assign_courier',
                        'priority': 'high',
                        'description': 'Assign courier to order',
                        'order_id': order_id
                    })
            
            return actions
            
        except Exception as e:
            logger.error(f"Error determining follow-up actions: {str(e)}")
            return []
    
    def generate_status_update_message(self, order: Order, update_type: str = 'general') -> str:
        """
        Generate status update message for customer
        
        Args:
            order: Order instance
            update_type: Type of update (general, delay, problem, completed)
            
        Returns:
            Formatted status message
        """
        try:
            elapsed = timezone.now() - order.order_placed_at
            elapsed_minutes = int(elapsed.total_seconds() / 60)
            
            if update_type == 'delay':
                message = f"""⏰ *Order Update - Order #{order.id}*

We apologize for the delay with your order from {order.vendor.business_name}.

🕐 *Current Status:* {order.status.title()}
⏰ *Elapsed Time:* {elapsed_minutes} minutes

We're working to get your order to you as soon as possible. Thank you for your patience.

---
*Bestyy Customer Support*"""
            
            elif update_type == 'problem':
                message = f"""⚠️ *Order Update - Order #{order.id}*

We're experiencing an issue with your order from {order.vendor.business_name}.

🕐 *Current Status:* {order.status.title()}
⏰ *Elapsed Time:* {elapsed_minutes} minutes

Our team is working to resolve this quickly. We'll keep you updated.

---
*Bestyy Customer Support*"""
            
            elif update_type == 'completed':
                message = f"""✅ *Order Delivered - Order #{order.id}*

Your order from {order.vendor.business_name} has been successfully delivered!

🕐 *Delivery Time:* {elapsed_minutes} minutes
📍 *Delivered To:* {order.delivery_address}

Thank you for choosing Bestyy! Enjoy your meal! 🍽️

---
*Bestyy Customer Support*"""
            
            else:  # general update
                message = f"""📱 *Order Update - Order #{order.id}*

Your order from {order.vendor.business_name} is progressing well.

🕐 *Current Status:* {order.status.title()}
⏰ *Elapsed Time:* {elapsed_minutes} minutes

We'll keep you updated on the progress. Thank you for your patience!

---
*Bestyy Customer Support*"""
            
            return message
            
        except Exception as e:
            logger.error(f"Error generating status update message: {str(e)}")
            return "Thank you for your inquiry. We're looking into your order status."
    
    def handle_urgent_customer_issue(self, customer_message: str, customer_id: int, order_id: int = None) -> Dict:
        """
        Handle urgent customer issues with immediate response
        
        Args:
            customer_message: Customer's urgent message
            customer_id: Customer ID
            order_id: Order ID (optional)
            
        Returns:
            Dictionary with urgent response and actions
        """
        try:
            # Get context
            context = self._get_customer_context(customer_id, order_id)
            
            # Generate urgent response
            urgent_prompt = f"""
URGENT CUSTOMER ISSUE - IMMEDIATE RESPONSE NEEDED

CUSTOMER MESSAGE: "{customer_message}"

CONTEXT:
{self._build_context_string(context)}

This is an urgent issue requiring immediate attention. Provide:
1. Immediate acknowledgment
2. Urgent action plan
3. Escalation steps

Respond with JSON:
{{
    "urgency_level": "critical|high|medium",
    "immediate_response": "immediate response to customer",
    "urgent_actions": ["list of urgent actions needed"],
    "escalation_required": true/false,
    "estimated_resolution": "immediate|5 min|10 min|30 min",
    "internal_alert": "alert message for internal team"
}}
"""
            
            response = requests.post(
                url=f"{self.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self.app_url,
                    "X-Title": self.app_name,
                },
                data=json.dumps({
                    "model": "meta-llama/llama-3.2-3b-instruct:free",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an urgent customer support AI. Handle urgent issues with immediate, actionable responses. Always respond with valid JSON."
                        },
                        {
                            "role": "user",
                            "content": urgent_prompt
                        }
                    ],
                    "temperature": 0.5,
                    "max_tokens": 400
                })
            )
            
            if response.status_code == 200:
                response_data = response.json()
                ai_response = response_data['choices'][0]['message']['content'].strip()
                
                try:
                    urgent_response = json.loads(ai_response)
                    
                    return {
                        'success': True,
                        'customer_message': customer_message,
                        'urgent_response': urgent_response,
                        'context': context,
                        'timestamp': timezone.now().isoformat()
                    }
                    
                except json.JSONDecodeError:
                    return {
                        'error': 'Failed to parse urgent response',
                        'raw_response': ai_response
                    }
            else:
                return {'error': f'LLM API error: {response.status_code}'}
                
        except Exception as e:
            logger.error(f"Error handling urgent customer issue: {str(e)}")
            return {'error': str(e)}
