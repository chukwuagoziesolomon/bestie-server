"""
Service for generating and sending payment receipts to users
"""
import logging
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from typing import Dict, List, Optional
from decimal import Decimal

from ..models import Order, User

logger = logging.getLogger(__name__)


class ReceiptService:
    """Service for generating and sending payment receipts"""
    
    @staticmethod
    def generate_receipt_data(order: Order) -> Dict:
        """Generate receipt data from order"""
        try:
            # Get order items
            items = []
            for item in order.items.all():
                items.append({
                    'name': item.dish_name,
                    'description': item.item_description or '',
                    'quantity': 1,  # Since we use M2M, quantity is 1 per item
                    'unit_price': float(item.price),
                    'total_price': float(item.price),
                    'image_url': item.image.url if item.image else None
                })
            
            # Calculate totals
            subtotal = sum(item['total_price'] for item in items)
            delivery_fee = float(getattr(order, 'delivery_fee', 0) or 0)
            service_fee = 0  # Add service fee logic if needed
            discount = 0  # Add discount logic if needed
            total_amount = subtotal + delivery_fee + service_fee - discount
            
            # Format delivery address
            delivery_address = order.delivery_address
            if hasattr(order, 'delivery_address') and hasattr(order.delivery_address, 'street'):
                # If delivery_address is an Address model instance
                delivery_address = f"{order.delivery_address.street}, {order.delivery_address.city}, {order.delivery_address.state} {order.delivery_address.postal_code}"
            
            # Estimate delivery time
            estimated_delivery = None
            if hasattr(order.vendor, 'delivery_time'):
                estimated_delivery = order.vendor.delivery_time
            
            return {
                'order_id': order.id,
                'order_date': order.created_at.strftime('%B %d, %Y at %I:%M %p'),
                'customer_name': f"{order.user.first_name} {order.user.last_name}".strip() or order.user.email,
                'vendor_name': order.vendor.business_name,
                'items': items,
                'subtotal': float(order.total_amount),
                'delivery_fee': delivery_fee,
                'service_fee': service_fee,
                'discount': discount,
                'total_amount': float(order.total_amount + order.delivery_fee),
                'payment_method': getattr(order, 'payment_method', 'Unknown'),
                'payment_reference': getattr(order, 'payment_reference', None),
                'delivery_address': delivery_address,
                'estimated_delivery': estimated_delivery
            }
            
        except Exception as e:
            logger.error(f"Error generating receipt data for order {order.id}: {str(e)}")
            return {}
    
    @staticmethod
    def render_receipt_html(receipt_data: Dict) -> str:
        """Render receipt HTML template"""
        try:
            return render_to_string('receipt_template.html', receipt_data)
        except Exception as e:
            logger.error(f"Error rendering receipt HTML: {str(e)}")
            return ""
    
    @staticmethod
    def send_receipt_email(user: User, order: Order, receipt_html: str) -> bool:
        """Send receipt via email"""
        try:
            subject = f"Payment Receipt - Order #{order.id} - Bestyy"
            
            # Send email
            send_mail(
                subject=subject,
                message="",  # Empty message since we're using HTML
                html_message=receipt_html,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@bestyy.com'),
                recipient_list=[user.email],
                fail_silently=False
            )
            
            logger.info(f"Receipt email sent successfully to {user.email} for order {order.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending receipt email to {user.email} for order {order.id}: {str(e)}")
            return False
    
    @staticmethod
    def send_receipt_whatsapp(user: User, order: Order, receipt_data: Dict) -> bool:
        """Send receipt via WhatsApp (if phone number available)"""
        try:
            from .whatsapp_vendor_service import WhatsAppVendorNotificationService
            
            phone_number = getattr(user, 'phone', None)
            if not phone_number:
                logger.warning(f"No phone number available for user {user.id}")
                return False
            
            # Create WhatsApp message
            message = f"""
🎉 *Payment Successful!*

*Order #{order.id}*
📅 {receipt_data['order_date']}
🏪 {receipt_data['vendor_name']}

*Items Ordered:*
"""
            
            for item in receipt_data['items']:
                message += f"• {item['name']} - ₦{item['total_price']:.2f}\n"
            
            message += f"""
💰 *Total: ₦{receipt_data['total_amount']:.2f}*
💳 Paid via {receipt_data['payment_method']}

📍 *Delivery Address:*
{receipt_data['delivery_address']}

Thank you for choosing Bestyy! 🚀
            """
            
            # Send WhatsApp message
            whatsapp_service = WhatsAppVendorNotificationService()
            result = whatsapp_service.send_message(phone_number, message)
            
            if result.get('success'):
                logger.info(f"WhatsApp receipt sent successfully to {phone_number} for order {order.id}")
                return True
            else:
                logger.error(f"Failed to send WhatsApp receipt: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp receipt for order {order.id}: {str(e)}")
            return False
    
    @staticmethod
    def send_payment_receipt(order: Order) -> Dict:
        """Send payment receipt via email and WhatsApp"""
        try:
            # Generate receipt data
            receipt_data = ReceiptService.generate_receipt_data(order)
            if not receipt_data:
                return {
                    'success': False,
                    'error': 'Failed to generate receipt data'
                }
            
            # Render HTML receipt
            receipt_html = ReceiptService.render_receipt_html(receipt_data)
            if not receipt_html:
                return {
                    'success': False,
                    'error': 'Failed to render receipt HTML'
                }
            
            # Send via email
            email_sent = ReceiptService.send_receipt_email(order.user, order, receipt_html)
            
            # Send via WhatsApp
            whatsapp_sent = ReceiptService.send_receipt_whatsapp(order.user, order, receipt_data)

            # Send receipt images to all parties
            image_sent = ReceiptService.send_receipt_images(order, receipt_data)

            return {
                'success': True,
                'email_sent': email_sent,
                'whatsapp_sent': whatsapp_sent,
                'image_sent': image_sent,
                'receipt_data': receipt_data,
                'message': f"Receipt sent via {'email' if email_sent else 'failed'}, {'WhatsApp' if whatsapp_sent else 'failed'}, {'images' if image_sent else 'failed'}"
            }
            
        except Exception as e:
            logger.error(f"Error sending payment receipt for order {order.id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


