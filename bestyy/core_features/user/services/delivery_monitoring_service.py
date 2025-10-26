"""
Delivery monitoring service with intelligent status tracking and customer updates
"""
import requests
import json
import logging
from typing import Dict, List, Optional
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from ..models import Order, VendorProfile, CourierProfile
from .whatsapp_courier_service import WhatsAppCourierNotificationService
from .whatsapp_vendor_service import WhatsAppVendorNotificationService

logger = logging.getLogger(__name__)


class DeliveryMonitoringService:
    """
    Service for monitoring delivery progress and providing real-time updates
    """
    
    def __init__(self):
        # OpenRouter LLM configuration
        self.openrouter_api_key = getattr(settings, 'OPENROUTER_API_KEY', None)
        self.openrouter_base_url = "https://openrouter.ai/api/v1"
        self.app_url = getattr(settings, 'OPENROUTER_APP_URL', 'https://bestyy.com')
        self.app_name = getattr(settings, 'OPENROUTER_APP_NAME', 'Bestyy Delivery Monitor')
        
        # Delivery targets
        self.target_delivery_time = 20  # minutes
        self.status_check_interval = 5  # minutes
        self.warning_threshold = 15  # minutes
        
        # Notification services
        self.courier_whatsapp = WhatsAppCourierNotificationService()
        self.vendor_whatsapp = WhatsAppVendorNotificationService()
    
    def monitor_active_deliveries(self) -> Dict:
        """
        Monitor all active deliveries and check their status
        """
        try:
            # Get all active deliveries
            active_orders = Order.objects.filter(
                status__in=['assigned', 'picked_up', 'out_for_delivery'],
                courier__isnull=False
            ).select_related('vendor', 'courier', 'user')
            
            results = {
                'total_orders': active_orders.count(),
                'status_checks': [],
                'warnings_sent': [],
                'updates_sent': []
            }
            
            for order in active_orders:
                # Check if status check is due
                if self._is_status_check_due(order):
                    status_result = self._check_delivery_status(order)
                    results['status_checks'].append(status_result)
                    
                    # Send warnings if needed
                    if self._should_send_warning(order):
                        warning_result = self._send_delivery_warning(order)
                        results['warnings_sent'].append(warning_result)
                    
                    # Update customer if needed
                    if self._should_update_customer(order):
                        update_result = self._update_customer_status(order)
                        results['updates_sent'].append(update_result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error monitoring active deliveries: {str(e)}")
            return {'error': str(e)}
    
    def _is_status_check_due(self, order: Order) -> bool:
        """
        Check if a status check is due for this order
        """
        try:
            # Get last status check time
            last_check = getattr(order, 'last_status_check', None)
            if not last_check:
                # First check - set initial time
                order.last_status_check = timezone.now()
                order.save()
                return True
            
            # Check if 5 minutes have passed
            time_since_check = timezone.now() - last_check
            return time_since_check >= timedelta(minutes=self.status_check_interval)
            
        except Exception as e:
            logger.error(f"Error checking status check due: {str(e)}")
            return False
    
    def _check_delivery_status(self, order: Order) -> Dict:
        """
        Check delivery status by querying vendor and courier
        """
        try:
            # Query vendor about order status
            vendor_status = self._query_vendor_status(order)
            
            # Query courier about delivery status
            courier_status = self._query_courier_status(order)
            
            # Analyze responses using LLM
            analysis = self._analyze_status_responses(order, vendor_status, courier_status)
            
            # Update order status if needed
            if analysis.get('status_changed'):
                order.status = analysis['new_status']
                order.save()
            
            # Update last check time
            order.last_status_check = timezone.now()
            order.save()
            
            return {
                'order_id': order.id,
                'vendor_status': vendor_status,
                'courier_status': courier_status,
                'analysis': analysis,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking delivery status for order {order.id}: {str(e)}")
            return {'error': str(e), 'order_id': order.id}
    
    def _query_vendor_status(self, order: Order) -> Dict:
        """
        Query vendor about order status using WhatsApp
        """
        try:
            vendor = order.vendor
            vendor_phone = getattr(vendor, 'whatsapp_number', None) or getattr(vendor, 'contact_phone', None)
            
            if not vendor_phone:
                return {'error': 'Vendor phone not available'}
            
            # Create status query message
            message = f"""📋 *ORDER STATUS CHECK*

Order #{order.id} - Customer: {order.user.first_name}

🕐 *Order Time:* {order.order_placed_at.strftime('%H:%M')}
⏰ *Elapsed Time:* {self._get_elapsed_time(order)} minutes

Please reply with your current status:
• "READY" - Order is ready for pickup
• "PREPARING" - Still preparing the order
• "DELAY" - Need more time (specify reason)
• "PROBLEM" - Having issues (specify problem)

This helps us keep customers informed. Thank you! 🙏

---
*Bestyy Delivery Monitor*"""
            
            # Send message to vendor
            result = self.vendor_whatsapp.send_order_notification(vendor_phone, {
                'order': order,
                'vendor': vendor,
                'message': message
            })
            
            return {
                'vendor_id': vendor.id,
                'vendor_phone': vendor_phone,
                'message_sent': result.get('success', False),
                'message': message
            }
            
        except Exception as e:
            logger.error(f"Error querying vendor status: {str(e)}")
            return {'error': str(e)}
    
    def _query_courier_status(self, order: Order) -> Dict:
        """
        Query courier about delivery status using WhatsApp
        """
        try:
            courier = order.courier
            courier_phone = getattr(courier, 'phone', None)
            
            if not courier_phone:
                return {'error': 'Courier phone not available'}
            
            # Create status query message
            message = f"""🚚 *DELIVERY STATUS CHECK*

Order #{order.id} - Customer: {order.user.first_name}

🕐 *Assigned Time:* {order.order_placed_at.strftime('%H:%M')}
⏰ *Elapsed Time:* {self._get_elapsed_time(order)} minutes
📍 *Delivery Address:* {order.delivery_address}

Please reply with your current status:
• "PICKED_UP" - Order picked up from vendor
• "ON_THE_WAY" - Heading to customer
• "ARRIVED" - Arrived at customer location
• "DELIVERED" - Successfully delivered
• "DELAY" - Running late (specify reason)
• "PROBLEM" - Having issues (specify problem)

This helps us keep customers informed. Thank you! 🙏

---
*Bestyy Delivery Monitor*"""
            
            # Send message to courier
            result = self.courier_whatsapp.send_delivery_update(courier_phone, {
                'order': order,
                'courier': courier,
                'message': message
            }, 'status_check')
            
            return {
                'courier_id': courier.id,
                'courier_phone': courier_phone,
                'message_sent': result.get('success', False),
                'message': message
            }
            
        except Exception as e:
            logger.error(f"Error querying courier status: {str(e)}")
            return {'error': str(e)}
    
    def _analyze_status_responses(self, order: Order, vendor_status: Dict, courier_status: Dict) -> Dict:
        """
        Use LLM to analyze vendor and courier responses
        """
        try:
            if not self.openrouter_api_key:
                return {'error': 'OpenRouter API key not configured'}
            
            # Prepare analysis prompt
            prompt = f"""
Analyze the delivery status for Order #{order.id}:

VENDOR STATUS: {vendor_status.get('message', 'No response')}
COURIER STATUS: {courier_status.get('message', 'No response')}

ELAPSED TIME: {self._get_elapsed_time(order)} minutes
TARGET DELIVERY TIME: {self.target_delivery_time} minutes

Please analyze and respond with JSON format:
{{
    "status_changed": true/false,
    "new_status": "preparing|ready|picked_up|out_for_delivery|delivered",
    "urgency_level": "low|medium|high|critical",
    "estimated_completion": "5-10 min|10-15 min|15-20 min|20+ min",
    "issues_detected": ["list of issues if any"],
    "recommendations": ["list of recommended actions"],
    "customer_message": "message to send to customer"
}}

Focus on:
1. Identifying delays or problems
2. Estimating delivery completion time
3. Detecting urgent situations
4. Providing clear customer updates
"""
            
            # Make request to OpenRouter
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
                            "content": "You are a delivery monitoring AI. Analyze delivery status and provide clear, actionable insights. Always respond with valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500
                })
            )
            
            if response.status_code == 200:
                response_data = response.json()
                ai_response = response_data['choices'][0]['message']['content'].strip()
                
                # Parse JSON response
                try:
                    analysis = json.loads(ai_response)
                    return analysis
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    return {
                        'status_changed': False,
                        'new_status': order.status,
                        'urgency_level': 'medium',
                        'estimated_completion': '15-20 min',
                        'issues_detected': [],
                        'recommendations': ['Continue monitoring'],
                        'customer_message': 'Your order is being prepared and will be delivered soon.'
                    }
            else:
                logger.error(f"OpenRouter API error: {response.status_code}")
                return {'error': 'LLM analysis failed'}
                
        except Exception as e:
            logger.error(f"Error analyzing status responses: {str(e)}")
            return {'error': str(e)}
    
    def _should_send_warning(self, order: Order) -> bool:
        """
        Check if a warning should be sent
        """
        elapsed_time = self._get_elapsed_time(order)
        return elapsed_time >= self.warning_threshold
    
    def _send_delivery_warning(self, order: Order) -> Dict:
        """
        Send warning to vendor and courier about delivery time
        """
        try:
            elapsed_time = self._get_elapsed_time(order)
            
            # Send warning to vendor
            vendor_warning = self._send_vendor_warning(order, elapsed_time)
            
            # Send warning to courier
            courier_warning = self._send_courier_warning(order, elapsed_time)
            
            return {
                'order_id': order.id,
                'elapsed_time': elapsed_time,
                'vendor_warning': vendor_warning,
                'courier_warning': courier_warning,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending delivery warning: {str(e)}")
            return {'error': str(e)}
    
    def _send_vendor_warning(self, order: Order, elapsed_time: int) -> Dict:
        """
        Send warning to vendor about delivery time
        """
        try:
            vendor = order.vendor
            vendor_phone = getattr(vendor, 'whatsapp_number', None) or getattr(vendor, 'contact_phone', None)
            
            if not vendor_phone:
                return {'error': 'Vendor phone not available'}
            
            message = f"""⚠️ *DELIVERY TIME WARNING*

Order #{order.id} - Customer: {order.user.first_name}

⏰ *Elapsed Time:* {elapsed_time} minutes
🎯 *Target Time:* {self.target_delivery_time} minutes

Please prioritize this order to meet our delivery target.

Current status needed:
• Is the order ready for pickup?
• Any delays or issues?

Thank you for your cooperation! 🙏

---
*Bestyy Delivery Monitor*"""
            
            result = self.vendor_whatsapp.send_order_notification(vendor_phone, {
                'order': order,
                'vendor': vendor,
                'message': message
            })
            
            return {
                'vendor_id': vendor.id,
                'message_sent': result.get('success', False),
                'message': message
            }
            
        except Exception as e:
            logger.error(f"Error sending vendor warning: {str(e)}")
            return {'error': str(e)}
    
    def _send_courier_warning(self, order: Order, elapsed_time: int) -> Dict:
        """
        Send warning to courier about delivery time
        """
        try:
            courier = order.courier
            courier_phone = getattr(courier, 'phone', None)
            
            if not courier_phone:
                return {'error': 'Courier phone not available'}
            
            message = f"""⚠️ *DELIVERY TIME WARNING*

Order #{order.id} - Customer: {order.user.first_name}

⏰ *Elapsed Time:* {elapsed_time} minutes
🎯 *Target Time:* {self.target_delivery_time} minutes

Please prioritize this delivery to meet our target time.

Current status needed:
• Have you picked up the order?
• What's your estimated delivery time?
• Any delays or issues?

Thank you for your cooperation! 🙏

---
*Bestyy Delivery Monitor*"""
            
            result = self.courier_whatsapp.send_delivery_update(courier_phone, {
                'order': order,
                'courier': courier,
                'message': message
            }, 'warning')
            
            return {
                'courier_id': courier.id,
                'message_sent': result.get('success', False),
                'message': message
            }
            
        except Exception as e:
            logger.error(f"Error sending courier warning: {str(e)}")
            return {'error': str(e)}
    
    def _should_update_customer(self, order: Order) -> bool:
        """
        Check if customer should be updated
        """
        # Update customer every 5 minutes or on status changes
        last_update = getattr(order, 'last_customer_update', None)
        if not last_update:
            return True
        
        time_since_update = timezone.now() - last_update
        return time_since_update >= timedelta(minutes=self.status_check_interval)
    
    def _update_customer_status(self, order: Order) -> Dict:
        """
        Update customer about delivery status
        """
        try:
            # This would integrate with your customer notification system
            # For now, return a placeholder
            return {
                'order_id': order.id,
                'customer_id': order.user.id,
                'update_sent': True,
                'message': 'Your order is being prepared and will be delivered soon.',
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating customer status: {str(e)}")
            return {'error': str(e)}
    
    def _get_elapsed_time(self, order: Order) -> int:
        """
        Get elapsed time since order was placed
        """
        elapsed = timezone.now() - order.order_placed_at
        return int(elapsed.total_seconds() / 60)  # Convert to minutes
    
    def process_vendor_response(self, order_id: int, vendor_phone: str, response_message: str) -> Dict:
        """
        Process vendor response to status query
        """
        try:
            order = Order.objects.get(id=order_id)
            
            # Analyze vendor response using LLM
            analysis = self._analyze_vendor_response(order, response_message)
            
            # Update order status if needed
            if analysis.get('status_changed'):
                order.status = analysis['new_status']
                order.save()
            
            # Send appropriate notifications
            if analysis.get('urgency_level') in ['high', 'critical']:
                self._handle_urgent_situation(order, analysis)
            
            return {
                'order_id': order_id,
                'vendor_response': response_message,
                'analysis': analysis,
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
        """
        try:
            order = Order.objects.get(id=order_id)
            
            # Analyze courier response using LLM
            analysis = self._analyze_courier_response(order, response_message)
            
            # Update order status if needed
            if analysis.get('status_changed'):
                order.status = analysis['new_status']
                order.save()
            
            # Send appropriate notifications
            if analysis.get('urgency_level') in ['high', 'critical']:
                self._handle_urgent_situation(order, analysis)
            
            return {
                'order_id': order_id,
                'courier_response': response_message,
                'analysis': analysis,
                'timestamp': timezone.now().isoformat()
            }
            
        except Order.DoesNotExist:
            return {'error': 'Order not found'}
        except Exception as e:
            logger.error(f"Error processing courier response: {str(e)}")
            return {'error': str(e)}
    
    def _analyze_vendor_response(self, order: Order, response: str) -> Dict:
        """
        Analyze vendor response using LLM
        """
        try:
            prompt = f"""
Analyze this vendor response for Order #{order.id}:

VENDOR RESPONSE: "{response}"
ELAPSED TIME: {self._get_elapsed_time(order)} minutes

Respond with JSON:
{{
    "status_changed": true/false,
    "new_status": "preparing|ready|picked_up",
    "urgency_level": "low|medium|high|critical",
    "issues_detected": ["list of issues"],
    "estimated_completion": "5-10 min|10-15 min|15-20 min|20+ min",
    "customer_message": "message to send to customer"
}}

Focus on detecting delays, problems, and readiness status.
"""
            
            return self._call_llm_for_analysis(prompt)
            
        except Exception as e:
            logger.error(f"Error analyzing vendor response: {str(e)}")
            return {'error': str(e)}
    
    def _analyze_courier_response(self, order: Order, response: str) -> Dict:
        """
        Analyze courier response using LLM
        """
        try:
            prompt = f"""
Analyze this courier response for Order #{order.id}:

COURIER RESPONSE: "{response}"
ELAPSED TIME: {self._get_elapsed_time(order)} minutes

Respond with JSON:
{{
    "status_changed": true/false,
    "new_status": "picked_up|out_for_delivery|delivered",
    "urgency_level": "low|medium|high|critical",
    "issues_detected": ["list of issues"],
    "estimated_completion": "5-10 min|10-15 min|15-20 min|20+ min",
    "customer_message": "message to send to customer"
}}

Focus on detecting delivery progress, delays, and completion status.
"""
            
            return self._call_llm_for_analysis(prompt)
            
        except Exception as e:
            logger.error(f"Error analyzing courier response: {str(e)}")
            return {'error': str(e)}
    
    def _call_llm_for_analysis(self, prompt: str) -> Dict:
        """
        Call OpenRouter LLM for analysis
        """
        try:
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
                            "content": "You are a delivery monitoring AI. Analyze responses and provide clear, actionable insights. Always respond with valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 300
                })
            )
            
            if response.status_code == 200:
                response_data = response.json()
                ai_response = response_data['choices'][0]['message']['content'].strip()
                
                try:
                    return json.loads(ai_response)
                except json.JSONDecodeError:
                    return {'error': 'Failed to parse LLM response'}
            else:
                return {'error': f'LLM API error: {response.status_code}'}
                
        except Exception as e:
            logger.error(f"Error calling LLM for analysis: {str(e)}")
            return {'error': str(e)}
    
    def _handle_urgent_situation(self, order: Order, analysis: Dict) -> None:
        """
        Handle urgent delivery situations
        """
        try:
            # Send urgent notifications
            # This would integrate with your notification system
            logger.warning(f"Urgent situation detected for order {order.id}: {analysis}")
            
        except Exception as e:
            logger.error(f"Error handling urgent situation: {str(e)}")
