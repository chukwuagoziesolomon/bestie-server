"""
Notification service for sending WhatsApp and WebSocket notifications to vendors
"""
import requests
import logging
from django.conf import settings
from django.core.mail import send_mail
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from typing import Dict, List, Optional
import json
from .whatsapp_vendor_service import WhatsAppVendorNotificationService

logger = logging.getLogger(__name__)


class VendorNotificationService:
    """
    Service for sending notifications to vendors via WhatsApp and WebSocket
    """
    
    @staticmethod
    def send_order_notification(order_data: Dict) -> Dict:
        """
        Send order notification to vendor via WhatsApp and WebSocket
        
        Args:
            order_data: Dictionary containing order information
            
        Returns:
            Dictionary with notification results
        """
        vendor = order_data.get('vendor')
        order = order_data.get('order')
        
        if not vendor or not order:
            return {
                'success': False,
                'error': 'Missing vendor or order data'
            }
        
        results = {
            'whatsapp': {'success': False, 'message': ''},
            'websocket': {'success': False, 'message': ''},
            'email': {'success': False, 'message': ''}
        }
        
        # Send WhatsApp notification using existing WhatsApp system
        try:
            whatsapp_service = WhatsAppVendorNotificationService()
            vendor_phone = getattr(vendor, 'whatsapp_number', None) or getattr(vendor, 'contact_phone', None)
            
            if vendor_phone:
                whatsapp_result = whatsapp_service.send_order_notification(vendor_phone, order_data)
                results['whatsapp'] = whatsapp_result
            else:
                results['whatsapp'] = {
                    'success': False,
                    'message': 'Vendor WhatsApp number not available'
                }
        except Exception as e:
            logger.error(f"WhatsApp notification failed: {str(e)}")
            results['whatsapp'] = {
                'success': False,
                'message': f'WhatsApp notification failed: {str(e)}'
            }
        
        # Send WebSocket notification
        try:
            websocket_result = VendorNotificationService._send_websocket_notification(order_data)
            results['websocket'] = websocket_result
        except Exception as e:
            logger.error(f"WebSocket notification failed: {str(e)}")
            results['websocket'] = {
                'success': False,
                'message': f'WebSocket notification failed: {str(e)}'
            }
        
        # Send email notification to vendor
        try:
            email_result = VendorNotificationService._send_email_notification(order_data)
            results['email'] = email_result
        except Exception as e:
            logger.error(f"Email notification failed: {str(e)}")
            results['email'] = {
                'success': False,
                'message': f'Email notification failed: {str(e)}'
            }
        
        return results
    
    @staticmethod
    def _send_whatsapp_notification(order_data: Dict) -> Dict:
        """
        Send WhatsApp notification to vendor
        """
        vendor = order_data.get('vendor')
        order = order_data.get('order')
        order_items = order_data.get('order_items', [])
        
        # Get vendor's WhatsApp number
        whatsapp_number = getattr(vendor, 'whatsapp_number', None)
        if not whatsapp_number:
            return {
                'success': False,
                'message': 'Vendor WhatsApp number not available'
            }
        
        # Format WhatsApp number (remove + and spaces)
        whatsapp_number = whatsapp_number.replace('+', '').replace(' ', '').replace('-', '')
        
        # Create order summary message
        message = VendorNotificationService._create_whatsapp_message(order_data)
        
        # Send via WhatsApp API (using WhatsApp Business API or Twilio)
        try:
            # Using Twilio WhatsApp API
            from twilio.rest import Client
            
            account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
            auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
            whatsapp_from = getattr(settings, 'TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')
            
            if not all([account_sid, auth_token, whatsapp_from]):
                return {
                    'success': False,
                    'message': 'WhatsApp configuration not available'
                }
            
            client = Client(account_sid, auth_token)
            
            message_response = client.messages.create(
                body=message,
                from_=whatsapp_from,
                to=f'whatsapp:+{whatsapp_number}'
            )
            
            return {
                'success': True,
                'message': 'WhatsApp notification sent successfully',
                'message_id': message_response.sid
            }
            
        except Exception as e:
            logger.error(f"Twilio WhatsApp API error: {str(e)}")
            return {
                'success': False,
                'message': f'WhatsApp API error: {str(e)}'
            }
    
    @staticmethod
    def _send_websocket_notification(order_data: Dict) -> Dict:
        """
        Send WebSocket notification to vendor
        """
        vendor = order_data.get('vendor')
        order = order_data.get('order')
        
        try:
            # Get channel layer
            channel_layer = get_channel_layer()
            if not channel_layer:
                return {
                    'success': False,
                    'message': 'WebSocket channel layer not available'
                }
            
            # Prepare notification data
            notification_data = {
                'type': 'order.new',
                'order_id': order.id,
                'order_number': f"#{order.id}",
                'customer': order_data.get('customer', {}),
                'items': order_data.get('order_items', []),
                'total_amount': order_data.get('total_amount', 0),
                'delivery_address': VendorNotificationService._get_delivery_address_data(order),
                'special_instructions': order_data.get('special_instructions', ''),
                'order_time': order.created_at.isoformat(),
                'estimated_delivery': VendorNotificationService._calculate_estimated_delivery(order),
                'timestamp': order.created_at.isoformat()
            }
            
            # Send to vendor's WebSocket group
            vendor_group_name = f'vendor_{vendor.id}'
            
            async_to_sync(channel_layer.group_send)(
                vendor_group_name,
                {
                    'type': 'order_notification',
                    'data': notification_data
                }
            )
            
            return {
                'success': True,
                'message': 'WebSocket notification sent successfully'
            }
            
        except Exception as e:
            logger.error(f"WebSocket notification error: {str(e)}")
            return {
                'success': False,
                'message': f'WebSocket notification failed: {str(e)}'
            }
    
    @staticmethod
    def _get_delivery_address_data(order):
        """Get delivery address data for notifications"""
        if hasattr(order, 'delivery_address') and order.delivery_address:
            return {
                'street': order.delivery_address.street,
                'city': order.delivery_address.city,
                'state': order.delivery_address.state,
                'postal_code': order.delivery_address.postal_code,
                'landmark': order.delivery_address.landmark,
            }
        return {}
    
    @staticmethod
    def _calculate_estimated_delivery(order):
        """Calculate estimated delivery time"""
        from datetime import timedelta
        base_time = timedelta(minutes=30)
        estimated_delivery = order.created_at + base_time
        return estimated_delivery.isoformat()
    
    @staticmethod
    def _create_whatsapp_message(order_data: Dict) -> str:
        """
        Create WhatsApp message content for order notification
        """
        vendor = order_data.get('vendor')
        order = order_data.get('order')
        order_items = order_data.get('order_items', [])
        customer = order_data.get('customer')
        total_amount = order_data.get('total_amount')
        
        message = f"""🍽️ *NEW ORDER NOTIFICATION*

📋 *Order Details:*
Order ID: #{order.id}
Customer: {customer.get('name', 'Unknown') if customer else 'Unknown'}
Phone: {customer.get('phone', 'Not provided') if customer else 'Not provided'}

🏪 *Vendor:* {vendor.business_name}
📍 *Address:* {vendor.business_address}

📦 *Order Items:*
"""
        
        for item in order_items:
            message += f"• {item.get('name', 'Unknown Item')} x{item.get('quantity', 1)} - ₦{item.get('total_price', 0)}\n"
            
            # Add variants if any
            variants = item.get('variants', [])
            if variants:
                for variant in variants:
                    message += f"  - {variant.get('name', '')} (+₦{variant.get('price_modifier', 0)})\n"
            
            # Add special instructions if any
            instructions = item.get('special_instructions', '')
            if instructions:
                message += f"  📝 Note: {instructions}\n"
        
        message += f"""
💰 *Total Amount:* ₦{total_amount}
🕐 *Order Time:* {order.created_at.strftime('%Y-%m-%d %H:%M')}
🚚 *Delivery Time:* {vendor.delivery_time if hasattr(vendor, 'delivery_time') else '30-40 min'}

Please prepare this order and confirm when ready for delivery.

Thank you! 🙏"""
        
        return message
    
    @staticmethod
    def _send_email_notification(order_data: Dict) -> Dict:
        """
        Send email notification to vendor about new order
        """
        try:
            vendor = order_data.get('vendor')
            order = order_data.get('order')
            order_items = order_data.get('order_items', [])
            customer = order_data.get('customer', {})
            total_amount = order_data.get('total_amount', 0)
            
            if not vendor or not order:
                return {
                    'success': False,
                    'message': 'Missing vendor or order data'
                }
            
            # Get vendor email from user account
            vendor_email = getattr(vendor, 'email', None) or getattr(vendor, 'contact_email', None) or getattr(vendor.user, 'email', None)
            if not vendor_email:
                return {
                    'success': False,
                    'message': 'Vendor email not available'
                }
            
            # Create email subject and content
            subject = f"New Order - {vendor.business_name}"
            
            # Create email body
            body = f"""
Dear {vendor.business_name},

You have received a new order!

ORDER SUMMARY:
==============
Customer: {customer.get('name', 'N/A')}
Total Amount: ₦{total_amount:,.2f}
Order Time: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}

ORDER CONTENTS:
===============
"""
            
            for item in order_items:
                body += f"""
• {item['name']} x{item['quantity']}
  Base Price: ₦{item['base_price']:,.2f}
  Total: ₦{item['total_price']:,.2f}"""
                
                if item.get('variants'):
                    body += "\n  Customizations:"
                    for variant in item['variants']:
                        body += f"\n    - {variant.get('name', 'N/A')} (+₦{variant.get('price', 0):,.2f})"
                
                if item.get('special_instructions'):
                    body += f"\n  Special Instructions: {item['special_instructions']}"
                
                body += "\n"
            
            # Add delivery information if available
            if hasattr(order, 'delivery_address') and order.delivery_address:
                body += f"""
DELIVERY ADDRESS:
================
{order.delivery_address.street}
{order.delivery_address.city}, {order.delivery_address.state}
{order.delivery_address.postal_code}
"""
                if order.delivery_address.landmark:
                    body += f"Landmark: {order.delivery_address.landmark}\n"
            
            if hasattr(order, 'delivery_instructions') and order.delivery_instructions:
                body += f"\nDelivery Instructions: {order.delivery_instructions}\n"
            
            body += f"""
PAYMENT METHOD: {getattr(order, 'payment_method', 'Cash on Delivery')}

Please prepare this order and confirm when ready for delivery.

Best regards,
Bestyy Team

---
This is an automated notification. Please do not reply to this email.
For support, contact us through the Bestyy platform.
"""
            
            # Send email
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[vendor_email],
                fail_silently=False,
            )
            
            logger.info(f"Email notification sent to vendor {vendor.id} for order {order.id}")
            
            return {
                'success': True,
                'message': f'Email sent to {vendor_email}',
                'vendor_email': vendor_email
            }
            
        except Exception as e:
            logger.error(f"Email notification failed: {str(e)}")
            return {
                'success': False,
                'message': f'Email notification failed: {str(e)}'
            }


class AutomaticVendorReplyService:
    """
    Service for sending automatic replies to vendors about upcoming orders
    """
    
    @staticmethod
    def send_automatic_reply(order_data: Dict, reply_type: str = 'order_confirmation') -> Dict:
        """
        Send automatic reply to vendor
        
        Args:
            order_data: Dictionary containing order information
            reply_type: Type of automatic reply ('order_confirmation', 'order_reminder', 'order_update')
            
        Returns:
            Dictionary with reply results
        """
        vendor = order_data.get('vendor')
        order = order_data.get('order')
        
        if not vendor or not order:
            return {
                'success': False,
                'error': 'Missing vendor or order data'
            }
        
        results = {
            'whatsapp': {'success': False, 'message': ''},
            'websocket': {'success': False, 'message': ''}
        }
        
        # Send WhatsApp automatic reply using existing WhatsApp system
        try:
            whatsapp_service = WhatsAppVendorNotificationService()
            vendor_phone = getattr(vendor, 'whatsapp_number', None) or getattr(vendor, 'contact_phone', None)
            
            if vendor_phone:
                whatsapp_result = whatsapp_service.send_automatic_reply(vendor_phone, order_data, reply_type)
                results['whatsapp'] = whatsapp_result
            else:
                results['whatsapp'] = {
                    'success': False,
                    'message': 'Vendor WhatsApp number not available'
                }
        except Exception as e:
            logger.error(f"WhatsApp automatic reply failed: {str(e)}")
            results['whatsapp'] = {
                'success': False,
                'message': f'WhatsApp automatic reply failed: {str(e)}'
            }
        
        # Send WebSocket automatic reply
        try:
            websocket_result = AutomaticVendorReplyService._send_websocket_automatic_reply(order_data, reply_type)
            results['websocket'] = websocket_result
        except Exception as e:
            logger.error(f"WebSocket automatic reply failed: {str(e)}")
            results['websocket'] = {
                'success': False,
                'message': f'WebSocket automatic reply failed: {str(e)}'
            }
        
        return results
    
    @staticmethod
    def _send_whatsapp_automatic_reply(order_data: Dict, reply_type: str) -> Dict:
        """
        Send automatic WhatsApp reply to vendor
        """
        vendor = order_data.get('vendor')
        order = order_data.get('order')
        
        # Get vendor's WhatsApp number
        whatsapp_number = getattr(vendor, 'whatsapp_number', None)
        if not whatsapp_number:
            return {
                'success': False,
                'message': 'Vendor WhatsApp number not available'
            }
        
        # Format WhatsApp number
        whatsapp_number = whatsapp_number.replace('+', '').replace(' ', '').replace('-', '')
        
        # Create automatic reply message
        message = AutomaticVendorReplyService._create_automatic_reply_message(order_data, reply_type)
        
        # Send via WhatsApp API
        try:
            from twilio.rest import Client
            
            account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
            auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
            whatsapp_from = getattr(settings, 'TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')
            
            if not all([account_sid, auth_token, whatsapp_from]):
                return {
                    'success': False,
                    'message': 'WhatsApp configuration not available'
                }
            
            client = Client(account_sid, auth_token)
            
            message_response = client.messages.create(
                body=message,
                from_=whatsapp_from,
                to=f'whatsapp:+{whatsapp_number}'
            )
            
            return {
                'success': True,
                'message': 'Automatic WhatsApp reply sent successfully',
                'message_id': message_response.sid
            }
            
        except Exception as e:
            logger.error(f"Twilio WhatsApp API error for automatic reply: {str(e)}")
            return {
                'success': False,
                'message': f'WhatsApp API error: {str(e)}'
            }
    
    @staticmethod
    def _send_websocket_automatic_reply(order_data: Dict, reply_type: str) -> Dict:
        """
        Send automatic WebSocket reply to vendor
        """
        vendor = order_data.get('vendor')
        order = order_data.get('order')
        
        try:
            # Get channel layer
            channel_layer = get_channel_layer()
            if not channel_layer:
                return {
                    'success': False,
                    'message': 'WebSocket channel layer not available'
                }
            
            # Prepare automatic reply data
            reply_data = {
                'type': f'automatic_reply.{reply_type}',
                'order_id': order.id,
                'order_number': f"#{order.id}",
                'reply_type': reply_type,
                'message': AutomaticVendorReplyService._get_automatic_reply_message(reply_type),
                'timestamp': order.created_at.isoformat()
            }
            
            # Send to vendor's WebSocket group
            vendor_group_name = f'vendor_{vendor.id}'
            
            async_to_sync(channel_layer.group_send)(
                vendor_group_name,
                {
                    'type': 'automatic_reply',
                    'data': reply_data
                }
            )
            
            return {
                'success': True,
                'message': 'Automatic WebSocket reply sent successfully'
            }
            
        except Exception as e:
            logger.error(f"WebSocket automatic reply error: {str(e)}")
            return {
                'success': False,
                'message': f'WebSocket automatic reply failed: {str(e)}'
            }
    
    @staticmethod
    def _create_automatic_reply_message(order_data: Dict, reply_type: str) -> str:
        """
        Create automatic reply message content
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

        elif reply_type == 'order_update':
            return f"""📢 *ORDER UPDATE*

Order #{order.id} status has been updated.

🔄 *Current Status:* {order.status.title()}
👤 *Customer:* {customer.get('name', 'Unknown')}

Check your dashboard for the latest details.

---
*Bestyy Order Management System*"""

        else:
            return f"""🤖 *AUTOMATIC REPLY*

Order #{order.id} notification received.

Thank you for using Bestyy!

---
*Bestyy Order Management System*"""
    
    @staticmethod
    def _get_automatic_reply_message(reply_type: str) -> str:
        """
        Get automatic reply message for WebSocket
        """
        messages = {
            'order_confirmation': 'Order automatically confirmed and queued',
            'order_reminder': 'Order reminder - please confirm',
            'order_update': 'Order status updated',
            'default': 'Automatic reply sent'
        }
        return messages.get(reply_type, messages['default'])


class OrderNotificationService:
    """
    Service for handling order-related notifications
    """
    
    @staticmethod
    def send_order_placed_notification(order):
        """
        Send notification when order is placed
        """
        try:
            # Prepare order data
            order_data = {
                'vendor': order.vendor,
                'order': order,
                'order_items': OrderNotificationService._get_order_items_data(order),
                'customer': {
                    'name': f"{order.user.first_name} {order.user.last_name}".strip(),
                    'email': order.user.email,
                    'phone': getattr(order.user, 'phone', 'Not provided')
                },
                'total_amount': float(order.total_amount)
            }
            
            # Send notifications
            results = VendorNotificationService.send_order_notification(order_data)
            
            # Log results
            logger.info(f"Order {order.id} notifications: {results}")
            
            return results
            
        except Exception as e:
            logger.error(f"Order notification failed for order {order.id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _get_order_items_data(order):
        """
        Get order items data for notifications
        """
        order_items = []
        
        # Assuming you have an OrderItem model
        # This might need to be adjusted based on your actual order structure
        if hasattr(order, 'items'):
            for item in order.items.all():
                order_items.append({
                    'name': item.menu_item.name,
                    'quantity': item.quantity,
                    'base_price': float(item.base_price),
                    'variants': item.variants,
                    'special_instructions': item.special_instructions,
                    'total_price': float(item.total_price)
                })
        
        return order_items


# WhatsApp template for order notifications
WHATSAPP_ORDER_TEMPLATE = """
🍽️ *NEW ORDER NOTIFICATION*

📋 *Order Details:*
Order ID: #{order_id}
Customer: {customer_name}
Phone: {customer_phone}

🏪 *Vendor:* {vendor_name}
📍 *Address:* {vendor_address}

📦 *Order Items:*
{order_items}

💰 *Total Amount:* ₦{total_amount}
🕐 *Order Time:* {order_time}
🚚 *Delivery Time:* {delivery_time}

Please prepare this order and confirm when ready for delivery.

Thank you! 🙏
"""
