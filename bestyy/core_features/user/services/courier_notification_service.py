"""
Courier notification service for sending notifications when orders are ready for delivery
"""
import requests
import logging
from django.conf import settings
from django.core.mail import send_mail
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from typing import Dict, List, Optional
import json
from .whatsapp_courier_service import WhatsAppCourierNotificationService

logger = logging.getLogger(__name__)


class CourierNotificationService:
    """
    Service for sending notifications to couriers via WhatsApp, Email, and WebSocket
    """
    
    @staticmethod
    def send_delivery_assignment(courier, order_data: Dict) -> Dict:
        """
        Send delivery assignment notification to courier via WhatsApp, Email, and WebSocket
        
        Args:
            courier: CourierProfile instance
            order_data: Dictionary containing order and delivery information
            
        Returns:
            Dictionary with notification results
        """
        if not courier:
            return {
                'success': False,
                'error': 'Missing courier data'
            }
        
        results = {
            'whatsapp': {'success': False, 'message': ''},
            'websocket': {'success': False, 'message': ''},
            'email': {'success': False, 'message': ''}
        }
        
        # Send WhatsApp notification
        try:
            whatsapp_service = WhatsAppCourierNotificationService()
            courier_phone = getattr(courier, 'phone', None)
            
            if courier_phone:
                whatsapp_result = whatsapp_service.send_delivery_assignment(courier_phone, order_data)
                results['whatsapp'] = whatsapp_result
            else:
                results['whatsapp'] = {
                    'success': False,
                    'message': 'Courier phone number not available'
                }
        except Exception as e:
            logger.error(f"WhatsApp courier notification failed: {str(e)}")
            results['whatsapp'] = {
                'success': False,
                'message': f'WhatsApp notification failed: {str(e)}'
            }
        
        # Send WebSocket notification
        try:
            websocket_result = CourierNotificationService._send_websocket_notification(courier, order_data, 'delivery_assigned')
            results['websocket'] = websocket_result
        except Exception as e:
            logger.error(f"WebSocket courier notification failed: {str(e)}")
            results['websocket'] = {
                'success': False,
                'message': f'WebSocket notification failed: {str(e)}'
            }
        
        # Send email notification to courier
        try:
            email_result = CourierNotificationService._send_email_notification(courier, order_data, 'delivery_assigned')
            results['email'] = email_result
        except Exception as e:
            logger.error(f"Email courier notification failed: {str(e)}")
            results['email'] = {
                'success': False,
                'message': f'Email notification failed: {str(e)}'
            }
        
        return results
    
    @staticmethod
    def send_delivery_update(courier, order_data: Dict, update_type: str) -> Dict:
        """
        Send delivery update notification to courier
        
        Args:
            courier: CourierProfile instance
            order_data: Dictionary containing order information
            update_type: Type of update (started, completed, failed, etc.)
            
        Returns:
            Dictionary with notification results
        """
        if not courier:
            return {
                'success': False,
                'error': 'Missing courier data'
            }
        
        results = {
            'whatsapp': {'success': False, 'message': ''},
            'websocket': {'success': False, 'message': ''},
            'email': {'success': False, 'message': ''}
        }
        
        # Send WhatsApp notification
        try:
            whatsapp_service = WhatsAppCourierNotificationService()
            courier_phone = getattr(courier, 'phone', None)
            
            if courier_phone:
                whatsapp_result = whatsapp_service.send_delivery_update(courier_phone, order_data, update_type)
                results['whatsapp'] = whatsapp_result
            else:
                results['whatsapp'] = {
                    'success': False,
                    'message': 'Courier phone number not available'
                }
        except Exception as e:
            logger.error(f"WhatsApp courier update notification failed: {str(e)}")
            results['whatsapp'] = {
                'success': False,
                'message': f'WhatsApp notification failed: {str(e)}'
            }
        
        # Send WebSocket notification
        try:
            websocket_result = CourierNotificationService._send_websocket_notification(courier, order_data, update_type)
            results['websocket'] = websocket_result
        except Exception as e:
            logger.error(f"WebSocket courier update notification failed: {str(e)}")
            results['websocket'] = {
                'success': False,
                'message': f'WebSocket notification failed: {str(e)}'
            }
        
        # Send email notification to courier
        try:
            email_result = CourierNotificationService._send_email_notification(courier, order_data, update_type)
            results['email'] = email_result
        except Exception as e:
            logger.error(f"Email courier update notification failed: {str(e)}")
            results['email'] = {
                'success': False,
                'message': f'Email notification failed: {str(e)}'
            }
        
        return results
    
    @staticmethod
    def _send_websocket_notification(courier, order_data: Dict, notification_type: str) -> Dict:
        """
        Send WebSocket notification to courier
        """
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                return {
                    'success': False,
                    'message': 'WebSocket channel layer not available'
                }
            
            # Prepare notification data
            notification_data = {
                'type': notification_type,
                'order_id': order_data.get('order', {}).get('id'),
                'vendor_name': order_data.get('vendor', {}).get('business_name', 'Unknown'),
                'customer_name': order_data.get('customer', {}).get('name', 'Unknown'),
                'pickup_location': order_data.get('pickup_location', ''),
                'delivery_location': order_data.get('delivery_location', ''),
                'estimated_earnings': order_data.get('estimated_earnings', 0),
                'timestamp': order_data.get('timestamp', ''),
                'message': CourierNotificationService._get_notification_message(notification_type, order_data)
            }
            
            # Send to courier-specific channel
            async_to_sync(channel_layer.group_send)(
                f"courier_{courier.id}",
                {
                    'type': 'courier_notification',
                    'data': notification_data
                }
            )
            
            return {
                'success': True,
                'message': f'WebSocket notification sent to courier {courier.id}',
                'courier_id': courier.id
            }
            
        except Exception as e:
            logger.error(f"WebSocket courier notification error: {str(e)}")
            return {
                'success': False,
                'message': f'WebSocket notification failed: {str(e)}'
            }
    
    @staticmethod
    def _send_email_notification(courier, order_data: Dict, notification_type: str) -> Dict:
        """
        Send email notification to courier
        """
        try:
            user = courier.user
            order = order_data.get('order', {})
            vendor = order_data.get('vendor', {})
            customer = order_data.get('customer', {})
            
            if notification_type == 'delivery_assigned':
                subject = f"🚚 New Delivery Assignment - Order #{order.get('id', 'N/A')}"
                
                message = f"""Hello {user.first_name or 'Courier'},

You have been assigned a new delivery!

📋 Order Details:
• Order ID: #{order.get('id', 'N/A')}
• Customer: {customer.get('name', 'Unknown')}
• Phone: {customer.get('phone', 'Not provided')}

🏪 Pickup Location:
• Vendor: {vendor.get('business_name', 'Unknown')}
• Address: {order_data.get('pickup_location', 'Not specified')}

📍 Delivery Location:
• Address: {order_data.get('delivery_location', 'Not specified')}

💰 Estimated Earnings: ₦{order_data.get('estimated_earnings', 0)}
📏 Distance: {order_data.get('estimated_distance', 'N/A')} km

🚀 Next Steps:
1. Head to the pickup location
2. Confirm pickup with the vendor
3. Deliver to the customer
4. Confirm delivery completion

Please check your courier dashboard for more details.

Best regards,
Bestyy Delivery Team"""
            
            elif notification_type == 'delivery_started':
                subject = f"🚚 Delivery Started - Order #{order.get('id', 'N/A')}"
                
                message = f"""Hello {user.first_name or 'Courier'},

Your delivery for Order #{order.get('id', 'N/A')} has been started.

👤 Customer: {customer.get('name', 'Unknown')}
📍 Delivery Address: {order_data.get('delivery_location', 'Not specified')}

Please deliver the order safely and confirm completion.

Best regards,
Bestyy Delivery Team"""
            
            elif notification_type == 'delivery_completed':
                subject = f"✅ Delivery Completed - Order #{order.get('id', 'N/A')}"
                
                message = f"""Hello {user.first_name or 'Courier'},

Congratulations! You have successfully completed delivery for Order #{order.get('id', 'N/A')}.

👤 Customer: {customer.get('name', 'Unknown')}
💰 Earnings: ₦{order_data.get('earnings', 0)}
🕐 Completed at: {order_data.get('completed_at', 'Now')}

Thank you for your excellent service!

Best regards,
Bestyy Delivery Team"""
            
            else:
                subject = f"📱 Delivery Update - Order #{order.get('id', 'N/A')}"
                message = f"""Hello {user.first_name or 'Courier'},

There's an update regarding your delivery for Order #{order.get('id', 'N/A')}.

{notification_type.title()}

Please check your courier dashboard for more details.

Best regards,
Bestyy Delivery Team"""
            
            # Send email
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False
            )
            
            return {
                'success': True,
                'message': f'Email sent to {user.email}',
                'courier_email': user.email
            }
            
        except Exception as e:
            logger.error(f"Email courier notification error: {str(e)}")
            return {
                'success': False,
                'message': f'Email notification failed: {str(e)}'
            }
    
    @staticmethod
    def _get_notification_message(notification_type: str, order_data: Dict) -> str:
        """
        Get appropriate notification message based on type
        """
        order_id = order_data.get('order', {}).get('id', 'N/A')
        customer_name = order_data.get('customer', {}).get('name', 'Unknown')
        
        if notification_type == 'delivery_assigned':
            return f"New delivery assignment for Order #{order_id} - Customer: {customer_name}"
        elif notification_type == 'delivery_started':
            return f"Delivery started for Order #{order_id} - Customer: {customer_name}"
        elif notification_type == 'delivery_completed':
            return f"Delivery completed for Order #{order_id} - Customer: {customer_name}"
        elif notification_type == 'delivery_failed':
            return f"Delivery failed for Order #{order_id} - Customer: {customer_name}"
        else:
            return f"Delivery update for Order #{order_id} - Customer: {customer_name}"
