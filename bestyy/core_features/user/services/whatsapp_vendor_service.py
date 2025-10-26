"""
WhatsApp vendor notification service using existing WhatsApp AI system
"""
import requests
import json
import logging
from django.conf import settings
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class WhatsAppVendorNotificationService:
    """
    Service for sending WhatsApp notifications to vendors
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
        logger.info(f"WhatsApp service initialized: {self.service_type} (Environment: {self.environment})")
    
    def _determine_service_type(self):
        """Determine which WhatsApp service to use based on environment and configuration"""
        whatsapp_business_available = all([
            self.whatsapp_access_token,
            self.whatsapp_phone_number_id
        ])
        
        twilio_available = all([
            self.twilio_account_sid,
            self.twilio_auth_token,
            self.twilio_whatsapp_from
        ])
        
        if self.is_production:
            if whatsapp_business_available:
                return 'whatsapp_business_api'
            elif twilio_available:
                logger.warning("Using Twilio for production (WhatsApp Business API not configured)")
                return 'twilio'
            else:
                logger.error("No WhatsApp service configured for production")
                return None
        else:
            # Development: prefer Twilio, fallback to WhatsApp Business API
            if twilio_available:
                return 'twilio'
            elif whatsapp_business_available:
                logger.warning("Using WhatsApp Business API for development (Twilio not configured)")
                return 'whatsapp_business_api'
            else:
                logger.error("No WhatsApp service configured for development")
                return None
    
    def send_order_notification(self, vendor_phone: str, order_data: Dict) -> Dict:
        """
        Send order notification to vendor via WhatsApp
        
        Args:
            vendor_phone: Vendor's WhatsApp number
            order_data: Dictionary containing order information
            
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
            formatted_phone = self._format_phone_number(vendor_phone, self.service_type)
            
            # Create message content
            message_text = self._create_order_notification_message(order_data)
            
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
            logger.error(f"WhatsApp vendor notification failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'service_used': self.service_type
            }
    
    def send_automatic_reply(self, vendor_phone: str, order_data: Dict, reply_type: str = 'order_confirmation') -> Dict:
        """
        Send automatic reply to vendor via WhatsApp
        
        Args:
            vendor_phone: Vendor's WhatsApp number
            order_data: Dictionary containing order information
            reply_type: Type of automatic reply
            
        Returns:
            Dictionary with reply results
        """
        try:
            if not self.service_type:
                return {
                    'success': False,
                    'error': 'No WhatsApp service configured'
                }
            
            # Format phone number based on service type
            formatted_phone = self._format_phone_number(vendor_phone, self.service_type)
            
            # Create automatic reply message
            message_text = self._create_automatic_reply_message(order_data, reply_type)
            
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
            logger.error(f"WhatsApp automatic reply failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'service_used': self.service_type
            }
    
    def _send_whatsapp_business_message(self, to_phone: str, message_text: str) -> Dict:
        """
        Send WhatsApp message using Business API
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.whatsapp_access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'messaging_product': 'whatsapp',
                'to': to_phone,
                'type': 'text',
                'text': {
                    'body': message_text
                }
            }
            
            response = requests.post(self.whatsapp_api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                response_data = response.json()
                return {
                    'success': True,
                    'message': 'WhatsApp Business API message sent successfully',
                    'message_id': response_data.get('messages', [{}])[0].get('id'),
                    'whatsapp_message_id': response_data.get('messages', [{}])[0].get('id')
                }
            else:
                logger.error(f"WhatsApp Business API error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'WhatsApp Business API error: {response.status_code}',
                    'details': response.text
                }
                
        except Exception as e:
            logger.error(f"WhatsApp Business API message sending error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_twilio_message(self, to_phone: str, message_text: str) -> Dict:
        """
        Send WhatsApp message using Twilio
        """
        try:
            from twilio.rest import Client
            
            client = Client(self.twilio_account_sid, self.twilio_auth_token)
            
            message_response = client.messages.create(
                body=message_text,
                from_=self.twilio_whatsapp_from,
                to=f'whatsapp:+{to_phone}'
            )
            
            return {
                'success': True,
                'message': 'Twilio WhatsApp message sent successfully',
                'message_id': message_response.sid,
                'twilio_message_id': message_response.sid
            }
            
        except Exception as e:
            logger.error(f"Twilio WhatsApp message sending error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _format_phone_number(self, phone: str, service_type: str) -> str:
        """
        Format phone number for WhatsApp API based on service type
        """
        # Remove all non-digit characters
        digits_only = ''.join(filter(str.isdigit, phone))
        
        # Add country code if not present (assuming Nigeria +234)
        if not digits_only.startswith('234'):
            if digits_only.startswith('0'):
                # Remove leading 0 and add 234
                digits_only = '234' + digits_only[1:]
            else:
                # Add 234 if no country code
                digits_only = '234' + digits_only
        
        # Return format based on service type
        if service_type == 'twilio':
            return digits_only  # Twilio expects just the digits
        elif service_type == 'whatsapp_business_api':
            return digits_only  # WhatsApp Business API also expects just digits
        else:
            return digits_only
    
    def _create_order_notification_message(self, order_data: Dict) -> str:
        """
        Create WhatsApp message for order notification
        """
        vendor = order_data.get('vendor')
        order = order_data.get('order')
        order_items = order_data.get('order_items', [])
        customer = order_data.get('customer', {})
        total_amount = order_data.get('total_amount', 0)
        
        message = f"""🍽️ *NEW ORDER NOTIFICATION*

📋 *Order Details:*
Order ID: #{order.id}
Customer: {customer.get('name', 'Unknown')}
Phone: {customer.get('phone', 'Not provided')}

🏪 *Vendor:* {vendor.business_name}
📍 *Address:* {vendor.business_address}

📦 *Order Items:*"""
        
        for item in order_items:
            message += f"\n• {item.get('name', 'Unknown Item')} x{item.get('quantity', 1)} - ₦{item.get('total_price', 0)}"
            
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

💰 *Total Amount:* ₦{total_amount}
🕐 *Order Time:* {order.created_at.strftime('%Y-%m-%d %H:%M')}
🚚 *Delivery Time:* {vendor.delivery_time if hasattr(vendor, 'delivery_time') else '30-40 min'}

Please prepare this order and confirm when ready for delivery.

Thank you! 🙏"""
        
        return message
    
    def _create_automatic_reply_message(self, order_data: Dict, reply_type: str) -> str:
        """
        Create automatic reply message for vendor
        """
        vendor = order_data.get('vendor')
        order = order_data.get('order')
        customer = order_data.get('customer', {})
        
        if reply_type == 'order_confirmation':
            return f"""🤖 *AUTOMATIC REPLY - ORDER CONFIRMATION*

✅ Order #{order.id} has been automatically confirmed and added to your queue.

📋 *Quick Summary:*
• Customer: {customer.get('name', 'Unknown')}
• Total: ₦{order_data.get('total_amount', 0)}
• Items: {len(order_data.get('order_items', []))} item(s)
• Time: {order.created_at.strftime('%H:%M')}

🚀 *Next Steps:*
1. Check your vendor dashboard for full details
2. Start preparing the order
3. Update status when ready

💡 *Tip:* Reply with "READY" when order is prepared, or "DELAY" if you need more time.

---
*This is an automatic message from Bestyy Order Management System*"""

        elif reply_type == 'order_reminder':
            return f"""⏰ *ORDER REMINDER*

Order #{order.id} is still pending your confirmation.

🕐 *Order Time:* {order.created_at.strftime('%H:%M')}
👤 *Customer:* {customer.get('name', 'Unknown')}
💰 *Total:* ₦{order_data.get('total_amount', 0)}

Please confirm this order or let us know if you cannot fulfill it.

---
*Bestyy Order Management System*"""

        else:
            return f"""🤖 *AUTOMATIC REPLY*

Order #{order.id} notification received.

Thank you for using Bestyy!

---
*Bestyy Order Management System*"""


# Alternative: Simple SMS-style WhatsApp using Twilio
class TwilioWhatsAppVendorService:
    """
    Alternative WhatsApp service using Twilio (if you prefer Twilio over WhatsApp Business API)
    """
    
    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        self.whatsapp_from = getattr(settings, 'TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')
        
        if not all([self.account_sid, self.auth_token, self.whatsapp_from]):
            logger.warning("Twilio WhatsApp configuration not complete")
    
    def send_order_notification(self, vendor_phone: str, order_data: Dict) -> Dict:
        """
        Send order notification using Twilio WhatsApp
        """
        try:
            if not all([self.account_sid, self.auth_token, self.whatsapp_from]):
                return {
                    'success': False,
                    'error': 'Twilio WhatsApp configuration not available'
                }
            
            from twilio.rest import Client
            
            client = Client(self.account_sid, self.auth_token)
            
            # Format phone number
            formatted_phone = self._format_phone_number(vendor_phone)
            
            # Create message
            message_text = self._create_order_notification_message(order_data)
            
            # Send message
            message_response = client.messages.create(
                body=message_text,
                from_=self.whatsapp_from,
                to=f'whatsapp:+{formatted_phone}'
            )
            
            return {
                'success': True,
                'message': 'WhatsApp message sent successfully via Twilio',
                'message_id': message_response.sid
            }
            
        except Exception as e:
            logger.error(f"Twilio WhatsApp notification failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _format_phone_number(self, phone: str) -> str:
        """Format phone number for Twilio WhatsApp"""
        # Remove all non-digit characters
        digits_only = ''.join(filter(str.isdigit, phone))
        
        # Add country code if not present
        if not digits_only.startswith('234'):
            if digits_only.startswith('0'):
                digits_only = '234' + digits_only[1:]
            else:
                digits_only = '234' + digits_only
        
        return digits_only
    
    def _create_order_notification_message(self, order_data: Dict) -> str:
        """Create message text for order notification"""
        # Same as WhatsAppVendorNotificationService._create_order_notification_message
        vendor = order_data.get('vendor')
        order = order_data.get('order')
        order_items = order_data.get('order_items', [])
        customer = order_data.get('customer', {})
        total_amount = order_data.get('total_amount', 0)
        
        message = f"""🍽️ NEW ORDER NOTIFICATION

📋 Order Details:
Order ID: #{order.id}
Customer: {customer.get('name', 'Unknown')}
Phone: {customer.get('phone', 'Not provided')}

🏪 Vendor: {vendor.business_name}
📍 Address: {vendor.business_address}

📦 Order Items:"""
        
        for item in order_items:
            message += f"\n• {item.get('name', 'Unknown Item')} x{item.get('quantity', 1)} - ₦{item.get('total_price', 0)}"
            
            variants = item.get('variants', [])
            if variants:
                for variant in variants:
                    price_text = f" (+₦{variant.get('price_modifier', 0)})" if variant.get('price_modifier', 0) > 0 else ""
                    message += f"\n  - {variant.get('name', '')}{price_text}"
            
            instructions = item.get('special_instructions', '')
            if instructions:
                message += f"\n  📝 Note: {instructions}"
        
        message += f"""

💰 Total Amount: ₦{total_amount}
🕐 Order Time: {order.created_at.strftime('%Y-%m-%d %H:%M')}
🚚 Delivery Time: {vendor.delivery_time if hasattr(vendor, 'delivery_time') else '30-40 min'}

Please prepare this order and confirm when ready for delivery.

Thank you! 🙏"""
        
        return message
