"""
Vendor ready service for handling when vendors are ready for pickup
"""
import logging
import re
from typing import Dict, Optional
from django.db.models import Q
from django.utils import timezone
from ..models import Order, VendorProfile, CourierProfile
from .courier_location_service import CourierLocationService
from .courier_notification_service import CourierNotificationService
from .proximity_courier_service import ProximityCourierService

logger = logging.getLogger(__name__)


class VendorReadyService:
    """
    Service for handling vendor ready notifications and courier assignment
    """
    
    def __init__(self):
        self.courier_location_service = CourierLocationService()
        self.courier_notification_service = CourierNotificationService()
        self.proximity_courier_service = ProximityCourierService()
    
    def process_vendor_ready_message(self, vendor_phone: str, message: str) -> Dict:
        """
        Process vendor ready message and assign courier
        
        Args:
            vendor_phone: Vendor's phone number
            message: WhatsApp message content
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Find vendor by phone number
            vendor = self._find_vendor_by_phone(vendor_phone)
            if not vendor:
                return {
                    'success': False,
                    'error': 'Vendor not found',
                    'vendor_phone': vendor_phone
                }
            
            # Check if message indicates vendor is ready
            if not self._is_ready_message(message):
                return {
                    'success': False,
                    'error': 'Message does not indicate vendor is ready',
                    'vendor_phone': vendor_phone,
                    'message': message
                }
            
            # Find pending orders for this vendor
            pending_orders = self._get_pending_orders_for_vendor(vendor)
            if not pending_orders:
                return {
                    'success': False,
                    'error': 'No pending orders found for vendor',
                    'vendor_id': vendor.id,
                    'vendor_phone': vendor_phone
                }
            
            # Process each pending order
            results = []
            for order in pending_orders:
                result = self._assign_courier_to_order(order, vendor)
                results.append(result)
            
            return {
                'success': True,
                'message': f'Processed {len(results)} orders for vendor {vendor.business_name}',
                'vendor_id': vendor.id,
                'vendor_phone': vendor_phone,
                'orders_processed': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error processing vendor ready message: {str(e)}")
            return {
                'success': False,
                'error': f'Processing failed: {str(e)}',
                'vendor_phone': vendor_phone
            }
    
    def process_vendor_ready_with_proximity(self, 
                                          vendor_phone: str, 
                                          message: str,
                                          order_id: int = None) -> Dict:
        """
        Process vendor ready message using proximity-based courier selection
        """
        try:
            # Check if vendor is ready
            if not self._is_vendor_ready(message):
                return {
                    'success': False,
                    'error': 'Vendor not ready',
                    'vendor_phone': vendor_phone,
                    'message': message
                }
            
            # Find vendor by phone
            vendor = VendorProfile.objects.filter(phone_number=vendor_phone).first()
            if not vendor:
                return {
                    'success': False,
                    'error': 'Vendor not found',
                    'vendor_phone': vendor_phone
                }
            
            # Get vendor's pending orders
            if order_id:
                orders = Order.objects.filter(
                    id=order_id,
                    vendor=vendor,
                    status__in=['preparing', 'pending']
                )
            else:
                orders = Order.objects.filter(
                    vendor=vendor,
                    status__in=['preparing', 'pending']
                )
            
            if not orders.exists():
                return {
                    'success': False,
                    'error': 'No pending orders found for vendor',
                    'vendor_id': vendor.id,
                    'vendor_phone': vendor_phone
                }
            
            results = []
            
            # Process each order
            for order in orders:
                # Find closest courier and notify
                courier_result = self.proximity_courier_service.notify_closest_courier(
                    vendor_id=vendor.id,
                    order_id=order.id,
                    notification_type='delivery_assignment'
                )
                
                if courier_result['success']:
                    # Update order status
                    order.status = 'ready'
                    order.save()
                    
                    results.append({
                        'order_id': order.id,
                        'status': 'success',
                        'courier_assigned': courier_result['courier_selected'],
                        'contact_info': courier_result['contact_info'],
                        'notification_result': courier_result['notification_result']
                    })
                else:
                    results.append({
                        'order_id': order.id,
                        'status': 'failed',
                        'error': courier_result.get('error', 'Unknown error')
                    })
            
            return {
                'success': True,
                'vendor_id': vendor.id,
                'vendor_phone': vendor_phone,
                'orders_processed': len(orders),
                'results': results,
                'vendor_contact_info': self.proximity_courier_service.get_vendor_contact_info(vendor.id)
            }
            
        except Exception as e:
            logger.error(f"Error processing vendor ready with proximity: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'vendor_phone': vendor_phone
            }
    
    def get_vendor_courier_contact_info(self, vendor_id: int, order_id: int = None) -> Dict:
        """
        Get comprehensive contact information for vendor and assigned courier
        """
        try:
            # Get vendor contact info
            vendor_contact = self.proximity_courier_service.get_vendor_contact_info(vendor_id)
            
            if not vendor_contact['success']:
                return vendor_contact
            
            # Get order information
            order_info = None
            if order_id:
                try:
                    order = Order.objects.get(id=order_id)
                    order_info = {
                        'order_id': order.id,
                        'status': order.status,
                        'total_price': order.total_price,
                        'delivery_address': order.delivery_address,
                        'order_placed_at': order.order_placed_at.isoformat(),
                        'courier_assigned': order.courier is not None,
                        'courier_id': order.courier.id if order.courier else None
                    }
                    
                    # Get courier contact info if assigned
                    courier_contact = None
                    if order.courier:
                        courier_contact = self.proximity_courier_service.get_courier_contact_info(order.courier.id)
                    
                    order_info['courier_contact'] = courier_contact
                    
                except Order.DoesNotExist:
                    order_info = {'error': 'Order not found'}
            
            return {
                'success': True,
                'vendor_contact': vendor_contact['contact_info'],
                'order_info': order_info,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting vendor courier contact info: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'vendor_id': vendor_id
            }
    
    def _find_vendor_by_phone(self, phone: str) -> Optional[VendorProfile]:
        """
        Find vendor by phone number
        """
        try:
            # Clean phone number
            clean_phone = re.sub(r'\D', '', phone)
            
            # Search for vendor by various phone fields
            vendor = VendorProfile.objects.filter(
                Q(contact_phone__icontains=clean_phone) |
                Q(whatsapp_number__icontains=clean_phone) |
                Q(user__phone__icontains=clean_phone)
            ).first()
            
            return vendor
            
        except Exception as e:
            logger.error(f"Error finding vendor by phone: {str(e)}")
            return None
    
    def _is_ready_message(self, message: str) -> bool:
        """
        Check if message indicates vendor is ready
        """
        try:
            if not message:
                return False
            
            message_lower = message.lower().strip()
            
            # Keywords that indicate vendor is ready
            ready_keywords = [
                'ready', 'done', 'finished', 'prepared', 'complete',
                'pickup', 'delivery ready', 'order ready', 'food ready',
                'am ready', 'i am ready', 'we are ready', 'its ready'
            ]
            
            # Check if message contains any ready keywords
            for keyword in ready_keywords:
                if keyword in message_lower:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking ready message: {str(e)}")
            return False
    
    def _get_pending_orders_for_vendor(self, vendor: VendorProfile) -> list:
        """
        Get pending orders for vendor that need courier assignment
        """
        try:
            # Get orders that are confirmed but not yet assigned to courier
            orders = Order.objects.filter(
                vendor=vendor,
                status__in=['confirmed', 'preparing', 'ready'],
                courier__isnull=True
            ).order_by('order_placed_at')
            
            return list(orders)
            
        except Exception as e:
            logger.error(f"Error getting pending orders: {str(e)}")
            return []
    
    def _assign_courier_to_order(self, order: Order, vendor: VendorProfile) -> Dict:
        """
        Assign courier to order and send notifications
        """
        try:
            # Prepare customer data
            customer_data = {
                'name': f"{order.user.first_name} {order.user.last_name}".strip(),
                'phone': getattr(order.user, 'phone', 'Not provided'),
                'email': order.user.email
            }
            
            # Find and assign courier
            assignment_result = self.courier_location_service.assign_courier_to_order(
                order, vendor, customer_data
            )
            
            if not assignment_result:
                return {
                    'success': False,
                    'order_id': order.id,
                    'error': 'No available courier found'
                }
            
            courier = assignment_result['courier']
            order_data = assignment_result['order_data']
            
            # Assign courier to order
            order.courier = courier
            order.status = 'assigned'
            order.save()
            
            # Send notifications to courier
            notification_result = self.courier_notification_service.send_delivery_assignment(
                courier, order_data
            )
            
            return {
                'success': True,
                'order_id': order.id,
                'courier_id': courier.id,
                'courier_name': f"{courier.user.first_name} {courier.user.last_name}".strip(),
                'courier_phone': courier.phone,
                'notifications': notification_result,
                'assignment_details': assignment_result['assignment_details']
            }
            
        except Exception as e:
            logger.error(f"Error assigning courier to order {order.id}: {str(e)}")
            return {
                'success': False,
                'order_id': order.id,
                'error': f'Assignment failed: {str(e)}'
            }
    
    def handle_whatsapp_webhook(self, webhook_data: Dict) -> Dict:
        """
        Handle WhatsApp webhook for vendor ready messages
        
        Args:
            webhook_data: WhatsApp webhook payload
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Extract message data from webhook
            message_data = self._extract_message_from_webhook(webhook_data)
            if not message_data:
                return {
                    'success': False,
                    'error': 'Could not extract message data from webhook'
                }
            
            vendor_phone = message_data.get('from')
            message_text = message_data.get('text', '')
            
            if not vendor_phone or not message_text:
                return {
                    'success': False,
                    'error': 'Missing vendor phone or message text'
                }
            
            # Process the vendor ready message
            result = self.process_vendor_ready_message(vendor_phone, message_text)
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling WhatsApp webhook: {str(e)}")
            return {
                'success': False,
                'error': f'Webhook processing failed: {str(e)}'
            }
    
    def _extract_message_from_webhook(self, webhook_data: Dict) -> Optional[Dict]:
        """
        Extract message data from WhatsApp webhook payload
        """
        try:
            # Handle different webhook formats
            if 'entry' in webhook_data:
                # Facebook webhook format
                entries = webhook_data.get('entry', [])
                if entries:
                    changes = entries[0].get('changes', [])
                    if changes:
                        value = changes[0].get('value', {})
                        messages = value.get('messages', [])
                        if messages:
                            message = messages[0]
                            return {
                                'from': message.get('from'),
                                'text': message.get('text', {}).get('body', ''),
                                'message_id': message.get('id'),
                                'timestamp': message.get('timestamp')
                            }
            
            elif 'message' in webhook_data:
                # Direct message format
                message = webhook_data['message']
                return {
                    'from': message.get('from'),
                    'text': message.get('text', ''),
                    'message_id': message.get('id'),
                    'timestamp': message.get('timestamp')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting message from webhook: {str(e)}")
            return None
    
    def get_vendor_ready_stats(self, vendor_id: int) -> Dict:
        """
        Get statistics for vendor ready processing
        
        Args:
            vendor_id: Vendor ID
            
        Returns:
            Dictionary with statistics
        """
        try:
            vendor = VendorProfile.objects.get(id=vendor_id)
            
            # Get order statistics
            total_orders = Order.objects.filter(vendor=vendor).count()
            pending_orders = Order.objects.filter(
                vendor=vendor,
                status__in=['confirmed', 'preparing', 'ready'],
                courier__isnull=True
            ).count()
            assigned_orders = Order.objects.filter(
                vendor=vendor,
                courier__isnull=False
            ).count()
            
            return {
                'vendor_id': vendor_id,
                'vendor_name': vendor.business_name,
                'total_orders': total_orders,
                'pending_orders': pending_orders,
                'assigned_orders': assigned_orders,
                'ready_for_courier': pending_orders > 0
            }
            
        except VendorProfile.DoesNotExist:
            return {
                'error': 'Vendor not found',
                'vendor_id': vendor_id
            }
        except Exception as e:
            logger.error(f"Error getting vendor ready stats: {str(e)}")
            return {
                'error': f'Stats retrieval failed: {str(e)}',
                'vendor_id': vendor_id
            }
