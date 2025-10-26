"""
Status tracking system for real-time delivery monitoring and customer updates
"""
import logging
from typing import Dict, List, Optional
from django.utils import timezone
from datetime import timedelta
from ..models import Order, VendorProfile, CourierProfile
from .delivery_monitoring_service import DeliveryMonitoringService
from .intent_analysis_service import IntentAnalysisService
from .customer_support_ai_service import CustomerSupportAIService

logger = logging.getLogger(__name__)


class StatusTrackingSystem:
    """
    Comprehensive status tracking system for delivery monitoring
    """
    
    def __init__(self):
        self.delivery_monitor = DeliveryMonitoringService()
        self.intent_analyzer = IntentAnalysisService()
        self.customer_support = CustomerSupportAIService()
        
        # Tracking intervals
        self.status_check_interval = 5  # minutes
        self.customer_update_interval = 5  # minutes
        self.warning_threshold = 15  # minutes
        self.critical_threshold = 25  # minutes
    
    def start_delivery_tracking(self, order_id: int) -> Dict:
        """
        Start tracking a delivery order
        
        Args:
            order_id: Order ID to track
            
        Returns:
            Dictionary with tracking status
        """
        try:
            order = Order.objects.get(id=order_id)
            
            # Initialize tracking data
            tracking_data = {
                'order_id': order_id,
                'start_time': timezone.now(),
                'last_status_check': None,
                'last_customer_update': None,
                'status_history': [],
                'warnings_sent': 0,
                'customer_updates_sent': 0
            }
            
            # Log initial status
            self._log_status_change(order, 'tracking_started', tracking_data)
            
            return {
                'success': True,
                'order_id': order_id,
                'tracking_started': True,
                'tracking_data': tracking_data,
                'timestamp': timezone.now().isoformat()
            }
            
        except Order.DoesNotExist:
            return {'error': 'Order not found'}
        except Exception as e:
            logger.error(f"Error starting delivery tracking: {str(e)}")
            return {'error': str(e)}
    
    def process_status_check(self, order_id: int) -> Dict:
        """
        Process a status check for an order
        
        Args:
            order_id: Order ID to check
            
        Returns:
            Dictionary with status check results
        """
        try:
            order = Order.objects.get(id=order_id)
            
            # Check if status check is due
            if not self._is_status_check_due(order):
                return {
                    'success': True,
                    'order_id': order_id,
                    'status': 'check_not_due',
                    'message': 'Status check not due yet'
                }
            
            # Perform status check
            status_result = self.delivery_monitor._check_delivery_status(order)
            
            # Analyze the results
            analysis = self._analyze_status_result(order, status_result)
            
            # Update tracking data
            self._update_tracking_data(order, status_result, analysis)
            
            # Send notifications if needed
            notifications = self._send_appropriate_notifications(order, analysis)
            
            return {
                'success': True,
                'order_id': order_id,
                'status_result': status_result,
                'analysis': analysis,
                'notifications': notifications,
                'timestamp': timezone.now().isoformat()
            }
            
        except Order.DoesNotExist:
            return {'error': 'Order not found'}
        except Exception as e:
            logger.error(f"Error processing status check: {str(e)}")
            return {'error': str(e)}
    
    def process_vendor_response(self, order_id: int, vendor_phone: str, response_message: str) -> Dict:
        """
        Process vendor response to status query
        
        Args:
            order_id: Order ID
            vendor_phone: Vendor's phone number
            response_message: Vendor's response message
            
        Returns:
            Dictionary with processing results
        """
        try:
            order = Order.objects.get(id=order_id)
            
            # Analyze vendor intent
            intent_analysis = self.intent_analyzer.analyze_vendor_intent(
                response_message, 
                {
                    'order_id': order_id,
                    'customer_name': f"{order.user.first_name} {order.user.last_name}".strip(),
                    'order_time': order.order_placed_at.isoformat(),
                    'elapsed_time': self._get_elapsed_time(order)
                }
            )
            
            # Process the response
            processing_result = self.delivery_monitor.process_vendor_response(
                order_id, vendor_phone, response_message
            )
            
            # Update customer if needed
            customer_update = None
            if self._should_update_customer(order, intent_analysis):
                customer_update = self._update_customer_with_vendor_info(order, intent_analysis)
            
            return {
                'success': True,
                'order_id': order_id,
                'vendor_response': response_message,
                'intent_analysis': intent_analysis,
                'processing_result': processing_result,
                'customer_update': customer_update,
                'timestamp': timezone.now().isoformat()
            }
            
        except Order.DoesNotExist:
            return {'error': 'Order not found'}
        except Exception as e:
            logger.error(f"Error processing vendor response: {str(e)}")
            return {'error': str(e)}
    
    def process_courier_response(self, order_id: int, courier_phone: str, response_message: str) -> Dict:
        """
        Process courier response to status query
        
        Args:
            order_id: Order ID
            courier_phone: Courier's phone number
            response_message: Courier's response message
            
        Returns:
            Dictionary with processing results
        """
        try:
            order = Order.objects.get(id=order_id)
            
            # Analyze courier intent
            intent_analysis = self.intent_analyzer.analyze_courier_intent(
                response_message,
                {
                    'order_id': order_id,
                    'customer_name': f"{order.user.first_name} {order.user.last_name}".strip(),
                    'pickup_location': order.vendor.business_address,
                    'delivery_location': order.delivery_address,
                    'elapsed_time': self._get_elapsed_time(order)
                }
            )
            
            # Process the response
            processing_result = self.delivery_monitor.process_courier_response(
                order_id, courier_phone, response_message
            )
            
            # Update customer if needed
            customer_update = None
            if self._should_update_customer(order, intent_analysis):
                customer_update = self._update_customer_with_courier_info(order, intent_analysis)
            
            return {
                'success': True,
                'order_id': order_id,
                'courier_response': response_message,
                'intent_analysis': intent_analysis,
                'processing_result': processing_result,
                'customer_update': customer_update,
                'timestamp': timezone.now().isoformat()
            }
            
        except Order.DoesNotExist:
            return {'error': 'Order not found'}
        except Exception as e:
            logger.error(f"Error processing courier response: {str(e)}")
            return {'error': str(e)}
    
    def handle_customer_inquiry(self, customer_message: str, customer_id: int, order_id: int = None) -> Dict:
        """
        Handle customer inquiry with real-time status information
        
        Args:
            customer_message: Customer's message
            customer_id: Customer ID
            order_id: Order ID (optional)
            
        Returns:
            Dictionary with AI response and current status
        """
        try:
            # Get current order status
            current_status = None
            if order_id:
                try:
                    order = Order.objects.get(id=order_id)
                    current_status = self._get_current_order_status(order)
                except Order.DoesNotExist:
                    pass
            
            # Handle customer inquiry with AI
            ai_response = self.customer_support.handle_customer_inquiry(
                customer_message, customer_id, order_id
            )
            
            # Add real-time status information
            if current_status:
                ai_response['current_status'] = current_status
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error handling customer inquiry: {str(e)}")
            return {'error': str(e)}
    
    def _is_status_check_due(self, order: Order) -> bool:
        """
        Check if status check is due for order
        """
        try:
            last_check = getattr(order, 'last_status_check', None)
            if not last_check:
                return True
            
            time_since_check = timezone.now() - last_check
            return time_since_check >= timedelta(minutes=self.status_check_interval)
            
        except Exception as e:
            logger.error(f"Error checking status check due: {str(e)}")
            return False
    
    def _analyze_status_result(self, order: Order, status_result: Dict) -> Dict:
        """
        Analyze status check result
        """
        try:
            elapsed_time = self._get_elapsed_time(order)
            
            analysis = {
                'elapsed_time': elapsed_time,
                'urgency_level': 'low',
                'action_required': 'none',
                'customer_message': '',
                'internal_notes': ''
            }
            
            # Determine urgency based on elapsed time
            if elapsed_time >= self.critical_threshold:
                analysis['urgency_level'] = 'critical'
                analysis['action_required'] = 'immediate_intervention'
                analysis['customer_message'] = f"We apologize for the delay. Your order is {elapsed_time} minutes overdue. We're taking immediate action to resolve this."
            elif elapsed_time >= self.warning_threshold:
                analysis['urgency_level'] = 'high'
                analysis['action_required'] = 'escalate'
                analysis['customer_message'] = f"Your order is taking longer than expected ({elapsed_time} minutes). We're monitoring the situation closely."
            elif elapsed_time >= 10:
                analysis['urgency_level'] = 'medium'
                analysis['action_required'] = 'monitor'
                analysis['customer_message'] = f"Your order is being prepared. Current time: {elapsed_time} minutes."
            else:
                analysis['urgency_level'] = 'low'
                analysis['action_required'] = 'none'
                analysis['customer_message'] = f"Your order is being prepared. Current time: {elapsed_time} minutes."
            
            # Check for issues in status result
            if 'error' in status_result:
                analysis['urgency_level'] = 'high'
                analysis['action_required'] = 'investigate'
                analysis['internal_notes'] = f"Status check error: {status_result['error']}"
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing status result: {str(e)}")
            return {'error': str(e)}
    
    def _update_tracking_data(self, order: Order, status_result: Dict, analysis: Dict) -> None:
        """
        Update tracking data for order
        """
        try:
            # Update last status check time
            order.last_status_check = timezone.now()
            
            # Update order status if changed
            if analysis.get('status_changed'):
                order.status = analysis['new_status']
            
            order.save()
            
            # Log status change
            self._log_status_change(order, 'status_updated', {
                'status_result': status_result,
                'analysis': analysis
            })
            
        except Exception as e:
            logger.error(f"Error updating tracking data: {str(e)}")
    
    def _send_appropriate_notifications(self, order: Order, analysis: Dict) -> Dict:
        """
        Send appropriate notifications based on analysis
        """
        try:
            notifications = {
                'customer_notified': False,
                'vendor_notified': False,
                'courier_notified': False,
                'admin_notified': False
            }
            
            urgency = analysis.get('urgency_level', 'low')
            action_required = analysis.get('action_required', 'none')
            
            # Send customer notification
            if urgency in ['high', 'critical'] or action_required in ['escalate', 'immediate_intervention']:
                customer_message = analysis.get('customer_message', '')
                if customer_message:
                    # This would integrate with your customer notification system
                    notifications['customer_notified'] = True
            
            # Send vendor notification
            if urgency in ['high', 'critical']:
                # Send urgent notification to vendor
                notifications['vendor_notified'] = True
            
            # Send courier notification
            if urgency in ['high', 'critical'] and order.courier:
                # Send urgent notification to courier
                notifications['courier_notified'] = True
            
            # Send admin notification
            if urgency == 'critical' or action_required == 'immediate_intervention':
                # Send alert to admin
                notifications['admin_notified'] = True
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}")
            return {'error': str(e)}
    
    def _should_update_customer(self, order: Order, intent_analysis: Dict) -> bool:
        """
        Check if customer should be updated
        """
        try:
            # Check if last customer update is due
            last_update = getattr(order, 'last_customer_update', None)
            if not last_update:
                return True
            
            time_since_update = timezone.now() - last_update
            if time_since_update >= timedelta(minutes=self.customer_update_interval):
                return True
            
            # Check if intent analysis indicates urgent update needed
            urgency = intent_analysis.get('urgency_level', 'low')
            if urgency in ['high', 'critical']:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking customer update: {str(e)}")
            return False
    
    def _update_customer_with_vendor_info(self, order: Order, intent_analysis: Dict) -> Dict:
        """
        Update customer with vendor information
        """
        try:
            # Generate customer message based on vendor intent
            customer_message = self._generate_vendor_customer_message(order, intent_analysis)
            
            # Update last customer update time
            order.last_customer_update = timezone.now()
            order.save()
            
            return {
                'success': True,
                'customer_message': customer_message,
                'update_type': 'vendor_info',
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating customer with vendor info: {str(e)}")
            return {'error': str(e)}
    
    def _update_customer_with_courier_info(self, order: Order, intent_analysis: Dict) -> Dict:
        """
        Update customer with courier information
        """
        try:
            # Generate customer message based on courier intent
            customer_message = self._generate_courier_customer_message(order, intent_analysis)
            
            # Update last customer update time
            order.last_customer_update = timezone.now()
            order.save()
            
            return {
                'success': True,
                'customer_message': customer_message,
                'update_type': 'courier_info',
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating customer with courier info: {str(e)}")
            return {'error': str(e)}
    
    def _generate_vendor_customer_message(self, order: Order, intent_analysis: Dict) -> str:
        """
        Generate customer message based on vendor intent analysis
        """
        try:
            intent = intent_analysis.get('primary_intent', 'unknown')
            urgency = intent_analysis.get('urgency_level', 'low')
            extracted_info = intent_analysis.get('extracted_info', {})
            
            if intent == 'ready':
                return f"""✅ *Order Update - Order #{order.id}*

Great news! Your order from {order.vendor.business_name} is ready for pickup.

🚚 *Next Step:* Our courier will pick it up shortly and deliver it to you.

Thank you for your patience! 🙏

---
*Bestyy Delivery Team*"""
            
            elif intent == 'delay':
                reason = extracted_info.get('reason', 'preparation taking longer than expected')
                return f"""⏰ *Order Update - Order #{order.id}*

Your order from {order.vendor.business_name} is taking a bit longer to prepare.

📝 *Reason:* {reason}

We're working to get your order ready as soon as possible. Thank you for your patience!

---
*Bestyy Delivery Team*"""
            
            elif intent == 'problem':
                issues = extracted_info.get('issues', ['technical issue'])
                return f"""⚠️ *Order Update - Order #{order.id}*

We're experiencing a minor issue with your order from {order.vendor.business_name}.

🔧 *Issue:* {', '.join(issues)}

Our team is working to resolve this quickly. We'll keep you updated.

---
*Bestyy Delivery Team*"""
            
            else:
                return f"""📱 *Order Update - Order #{order.id}*

Your order from {order.vendor.business_name} is being prepared.

We'll keep you updated on the progress. Thank you for your patience!

---
*Bestyy Delivery Team*"""
                
        except Exception as e:
            logger.error(f"Error generating vendor customer message: {str(e)}")
            return "Your order is being prepared. We'll keep you updated."
    
    def _generate_courier_customer_message(self, order: Order, intent_analysis: Dict) -> str:
        """
        Generate customer message based on courier intent analysis
        """
        try:
            intent = intent_analysis.get('primary_intent', 'unknown')
            urgency = intent_analysis.get('urgency_level', 'low')
            extracted_info = intent_analysis.get('extracted_info', {})
            
            if intent == 'picked_up':
                return f"""🚚 *Order Update - Order #{order.id}*

Your order has been picked up from {order.vendor.business_name} and is on its way to you!

📍 *Delivery Address:* {order.delivery_address}

We'll notify you when our courier arrives. Thank you for your patience!

---
*Bestyy Delivery Team*"""
            
            elif intent == 'on_the_way':
                estimated_time = extracted_info.get('estimated_delivery', '5-10 minutes')
                return f"""🚚 *Order Update - Order #{order.id}*

Your order is on its way to you!

⏰ *Estimated Arrival:* {estimated_time}
📍 *Delivery Address:* {order.delivery_address}

Our courier will arrive shortly. Thank you for your patience!

---
*Bestyy Delivery Team*"""
            
            elif intent == 'arrived':
                return f"""🚚 *Order Update - Order #{order.id}*

Our courier has arrived at your location!

📍 *Delivery Address:* {order.delivery_address}

Please be ready to receive your order. Thank you!

---
*Bestyy Delivery Team*"""
            
            elif intent == 'delivered':
                return f"""✅ *Order Delivered - Order #{order.id}*

Your order has been successfully delivered!

🍽️ *Enjoy your meal from {order.vendor.business_name}!*

Thank you for choosing Bestyy! 🙏

---
*Bestyy Delivery Team*"""
            
            elif intent == 'delay':
                reason = extracted_info.get('reason', 'traffic delay')
                return f"""⏰ *Order Update - Order #{order.id}*

Your delivery is experiencing a slight delay.

📝 *Reason:* {reason}

We're working to get your order to you as soon as possible. Thank you for your patience!

---
*Bestyy Delivery Team*"""
            
            else:
                return f"""📱 *Order Update - Order #{order.id}*

Your order is being delivered.

We'll keep you updated on the progress. Thank you for your patience!

---
*Bestyy Delivery Team*"""
                
        except Exception as e:
            logger.error(f"Error generating courier customer message: {str(e)}")
            return "Your order is being delivered. We'll keep you updated."
    
    def _get_elapsed_time(self, order: Order) -> int:
        """
        Get elapsed time since order was placed
        """
        try:
            elapsed = timezone.now() - order.order_placed_at
            return int(elapsed.total_seconds() / 60)
        except Exception as e:
            logger.error(f"Error getting elapsed time: {str(e)}")
            return 0
    
    def _get_current_order_status(self, order: Order) -> Dict:
        """
        Get current order status information
        """
        try:
            elapsed_time = self._get_elapsed_time(order)
            
            return {
                'order_id': order.id,
                'status': order.status,
                'elapsed_time': elapsed_time,
                'vendor_name': order.vendor.business_name,
                'courier_assigned': order.courier is not None,
                'courier_name': f"{order.courier.user.first_name} {order.courier.user.last_name}".strip() if order.courier else None,
                'delivery_address': order.delivery_address,
                'urgency_level': self._determine_urgency_level(elapsed_time),
                'estimated_completion': self._estimate_completion_time(order, elapsed_time)
            }
            
        except Exception as e:
            logger.error(f"Error getting current order status: {str(e)}")
            return {'error': str(e)}
    
    def _determine_urgency_level(self, elapsed_time: int) -> str:
        """
        Determine urgency level based on elapsed time
        """
        if elapsed_time >= 25:
            return 'critical'
        elif elapsed_time >= 20:
            return 'high'
        elif elapsed_time >= 15:
            return 'medium'
        else:
            return 'low'
    
    def _estimate_completion_time(self, order: Order, elapsed_time: int) -> str:
        """
        Estimate completion time based on order status and elapsed time
        """
        if order.status == 'delivered':
            return 'Completed'
        elif order.status == 'out_for_delivery':
            return '5-10 minutes'
        elif order.status == 'picked_up':
            return '10-15 minutes'
        elif order.status == 'ready':
            return '10-15 minutes'
        elif order.status == 'preparing':
            return '15-20 minutes'
        else:
            return '15-20 minutes'
    
    def _log_status_change(self, order: Order, change_type: str, data: Dict) -> None:
        """
        Log status change for tracking
        """
        try:
            # This would integrate with your logging system
            logger.info(f"Order {order.id} status change: {change_type} - {data}")
        except Exception as e:
            logger.error(f"Error logging status change: {str(e)}")
