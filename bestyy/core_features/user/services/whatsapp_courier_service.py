"""
WhatsApp courier notification service using existing WhatsApp AI system
"""
import requests
import json
import logging
from django.conf import settings
from typing import Dict, Optional
import re

logger = logging.getLogger(__name__)


class WhatsAppCourierNotificationService:
    """
    Service for sending WhatsApp notifications to couriers
    - Uses Twilio for development
    - Uses WhatsApp Business API for production
    """
    
    def __init__(self):
        self.is_production = not getattr(settings, 'DEBUG', True)
        
        # WhatsApp Business API (Production)
        self.whatsapp_access_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)
        self.whatsapp_phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', None)
        self.whatsapp_api_url = f"https://graph.facebook.com/v18.0/{self.whatsapp_phone_number_id}/messages"
        
        # Twilio WhatsApp (Development)
        self.twilio_account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        self.twilio_auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        self.twilio_whatsapp_from = getattr(settings, 'TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')
        
        # Determine which service to use
        self.service_type = self._determine_service_type()
        self.environment = 'production' if self.is_production else 'development'
        logger.info(f"WhatsApp courier service initialized: {self.service_type} (Environment: {self.environment})")
    
    def _determine_service_type(self):
        """
        Determine which WhatsApp service to use based on available credentials
        """
        if self.whatsapp_access_token and self.whatsapp_phone_number_id:
            return 'whatsapp_business_api'
        elif self.twilio_account_sid and self.twilio_auth_token:
            return 'twilio'
        else:
            logger.warning("No WhatsApp service configured")
            return None
    
    def send_delivery_assignment(self, courier_phone: str, order_data: Dict) -> Dict:
        """
        Send delivery assignment notification to courier via WhatsApp
        
        Args:
            courier_phone: Courier's WhatsApp number
            order_data: Dictionary containing order and delivery information
            
        Returns:
            Dictionary with notification results
        """
        try:
            if not self.service_type:
                return {
                    'success': False,
                    'error': 'No WhatsApp service configured'
                }
            
            # Format phone number based on service type
            formatted_phone = self._format_phone_number(courier_phone, self.service_type)
            
            # Create message content
            message_text = self._create_delivery_assignment_message(order_data)
            
            # Send message using appropriate service
            if self.service_type == 'twilio':
                response = self._send_twilio_message(formatted_phone, message_text)
            elif self.service_type == 'whatsapp_business_api':
                response = self._send_whatsapp_business_message(formatted_phone, message_text)
            else:
                return {
                    'success': False,
                    'error': f'Unknown service type: {self.service_type}'
                }
            
            # Add service info to response
            response['service_used'] = self.service_type
            response['environment'] = 'production' if self.is_production else 'development'
            
            return response
            
        except Exception as e:
            logger.error(f"WhatsApp courier notification failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'service_used': self.service_type
            }
    
    def send_delivery_update(self, courier_phone: str, order_data: Dict, update_type: str) -> Dict:
        """
        Send delivery update notification to courier
        
        Args:
            courier_phone: Courier's WhatsApp number
            order_data: Dictionary containing order information
            update_type: Type of update (started, completed, failed, etc.)
            
        Returns:
            Dictionary with notification results
        """
        try:
            if not self.service_type:
                return {
                    'success': False,
                    'error': 'No WhatsApp service configured'
                }
            
            formatted_phone = self._format_phone_number(courier_phone, self.service_type)
            message_text = self._create_delivery_update_message(order_data, update_type)
            
            if self.service_type == 'twilio':
                response = self._send_twilio_message(formatted_phone, message_text)
            elif self.service_type == 'whatsapp_business_api':
                response = self._send_whatsapp_business_message(formatted_phone, message_text)
            else:
                return {
                    'success': False,
                    'error': f'Unknown service type: {self.service_type}'
                }
            
            response['service_used'] = self.service_type
            response['environment'] = 'production' if self.is_production else 'development'
            
            return response
            
        except Exception as e:
            logger.error(f"WhatsApp courier update notification failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'service_used': self.service_type
            }
    
    def _format_phone_number(self, phone: str, service_type: str) -> str:
        """
        Format phone number based on service type
        """
        # Remove any non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        
        if service_type == 'twilio':
            # Twilio format: whatsapp:+2348123456789
            if not digits_only.startswith('234'):
                if digits_only.startswith('0'):
                    digits_only = '234' + digits_only[1:]
                else:
                    digits_only = '234' + digits_only
            return f"whatsapp:+{digits_only}"
        
        elif service_type == 'whatsapp_business_api':
            # WhatsApp Business API format: 2348123456789
            if not digits_only.startswith('234'):
                if digits_only.startswith('0'):
                    digits_only = '234' + digits_only[1:]
                else:
                    digits_only = '234' + digits_only
            return digits_only
        
        else:
            return digits_only
    
    def _create_delivery_assignment_message(self, order_data: Dict) -> str:
        """
        Create WhatsApp message for delivery assignment
        """
        order = order_data.get('order')
        vendor = order_data.get('vendor')
        customer = order_data.get('customer', {})
        pickup_location = order_data.get('pickup_location', '')
        delivery_location = order_data.get('delivery_location', '')
        estimated_distance = order_data.get('estimated_distance', 'N/A')
        estimated_earnings = order_data.get('estimated_earnings', 0)
        
        message = f"""🚚 *NEW DELIVERY ASSIGNMENT*

📋 *Order Details:*
Order ID: #{order.id}
Customer: {customer.get('name', 'Unknown')}
Phone: {customer.get('phone', 'Not provided')}

🏪 *Pickup Location:*
{vendor.business_name}
{pickup_location}

📍 *Delivery Location:*
{delivery_location}

💰 *Earnings:* ₦{estimated_earnings}
📏 *Distance:* {estimated_distance} km
🕐 *Order Time:* {order.created_at.strftime('%Y-%m-%d %H:%M')}

📦 *Order Items:*"""
        
        order_items = order_data.get('order_items', [])
        for item in order_items:
            message += f"\n• {item.get('name', 'Unknown Item')} x{item.get('quantity', 1)}"
            
            # Add variants if any
            variants = item.get('variants', [])
            if variants:
                for variant in variants:
                    price_text = f" (+₦{variant.get('price_modifier', 0)})" if variant.get('price_modifier', 0) > 0 else ""
                    message += f"\n  - {variant.get('name', '')}{price_text}"
            
            # Add special instructions if any
            instructions = item.get('special_instructions', '')
            if instructions:
                message += f"\n  📝 Note: {instructions}"
        
        message += f"""

🚀 *Next Steps:*
1. Head to pickup location
2. Confirm pickup with vendor
3. Deliver to customer
4. Confirm delivery completion

💡 *Reply with:*
• "ACCEPT" to accept this delivery
• "DECLINE" to decline this delivery
• "MORE INFO" for additional details

---
*Bestyy Delivery System*"""
        
        return message
    
    def _create_delivery_update_message(self, order_data: Dict, update_type: str) -> str:
        """
        Create WhatsApp message for delivery updates
        """
        order = order_data.get('order')
        customer = order_data.get('customer', {})
        
        if update_type == 'started':
            return f"""🚚 *DELIVERY STARTED*

Order #{order.id} is now out for delivery.

👤 *Customer:* {customer.get('name', 'Unknown')}
📍 *Delivery Address:* {order_data.get('delivery_location', 'Not specified')}

🕐 *Started at:* {order_data.get('started_at', 'Now')}

Please deliver the order safely and confirm completion.

---
*Bestyy Delivery System*"""
        
        elif update_type == 'completed':
            return f"""✅ *DELIVERY COMPLETED*

Order #{order.id} has been successfully delivered!

👤 *Customer:* {customer.get('name', 'Unknown')}
🕐 *Completed at:* {order_data.get('completed_at', 'Now')}
💰 *Earnings:* ₦{order_data.get('earnings', 0)}

Thank you for completing this delivery!

---
*Bestyy Delivery System*"""
        
        elif update_type == 'failed':
            return f"""❌ *DELIVERY FAILED*

Order #{order.id} delivery could not be completed.

👤 *Customer:* {customer.get('name', 'Unknown')}
📍 *Delivery Address:* {order_data.get('delivery_location', 'Not specified')}
📝 *Reason:* {order_data.get('failure_reason', 'Not specified')}

Please contact support if you need assistance.

---
*Bestyy Delivery System*"""
        
        else:
            return f"""📱 *DELIVERY UPDATE*

Order #{order.id} status update.

{update_type.title()}

---
*Bestyy Delivery System*"""
    
    def _send_twilio_message(self, to_phone: str, message: str) -> Dict:
        """
        Send message via Twilio WhatsApp
        """
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"
            
            data = {
                'From': self.twilio_whatsapp_from,
                'To': to_phone,
                'Body': message
            }
            
            response = requests.post(
                url,
                data=data,
                auth=(self.twilio_account_sid, self.twilio_auth_token),
                timeout=30
            )
            
            if response.status_code == 201:
                response_data = response.json()
                return {
                    'success': True,
                    'message': f'WhatsApp message sent to {to_phone}',
                    'message_sid': response_data.get('sid'),
                    'courier_phone': to_phone
                }
            else:
                return {
                    'success': False,
                    'error': f'Twilio API error: {response.status_code} - {response.text}',
                    'courier_phone': to_phone
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Twilio request failed: {str(e)}',
                'courier_phone': to_phone
            }
    
    def _send_whatsapp_business_message(self, to_phone: str, message: str) -> Dict:
        """
        Send message via WhatsApp Business API
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.whatsapp_access_token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'messaging_product': 'whatsapp',
                'to': to_phone,
                'type': 'text',
                'text': {
                    'body': message
                }
            }
            
            response = requests.post(
                self.whatsapp_api_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                return {
                    'success': True,
                    'message': f'WhatsApp message sent to {to_phone}',
                    'message_id': response_data.get('messages', [{}])[0].get('id'),
                    'courier_phone': to_phone
                }
            else:
                return {
                    'success': False,
                    'error': f'WhatsApp Business API error: {response.status_code} - {response.text}',
                    'courier_phone': to_phone
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'WhatsApp Business API request failed: {str(e)}',
                'courier_phone': to_phone
            }
