"""
Unified webhook endpoint for verification and order notifications
"""
import json
import logging
from datetime import datetime
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
import hmac
import hashlib

from .serializers import (
    VerificationWebhookSerializer,
    OrderWebhookSerializer,
    WebhookResponseSerializer
)
from ..models import VendorProfile, CourierProfile, Order
from ..utils.websocket_notifications import (
    send_vendor_notification,
    send_courier_notification,
    notify_vendor_approved,
    notify_vendor_rejected,
    notify_courier_approved,
    notify_courier_rejected
)
from ..services.courier_notification_service import CourierNotificationService
from ..services.vendor_ready_service import VendorReadyService
from ..services.delivery_monitoring_service import DeliveryMonitoringService
from ..services.intent_analysis_service import IntentAnalysisService
from ..services.customer_support_ai_service import CustomerSupportAIService
from ..services.status_tracking_system import StatusTrackingSystem
from ..services.user_type_identification_service import UserTypeIdentificationService

logger = logging.getLogger(__name__)


class UnifiedWebhookView(APIView):
    """
    Unified webhook endpoint for verification and order notifications
    
    This endpoint handles:
    - Verification status updates (vendor/courier approval/rejection)
    - Order status updates
    - Payment notifications
    - Delivery assignments
    """
    permission_classes = [AllowAny]
    
    def verify_webhook_signature(self, payload, signature, secret):
        """
        Verify webhook signature using HMAC-SHA256
        """
        if not secret:
            return True  # Skip verification if no secret is configured
        
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def get_webhook_secret(self):
        """Get webhook secret from settings"""
        return getattr(settings, 'WEBHOOK_SECRET', None)
    
    def post(self, request):
        """
        Handle incoming webhook notifications
        
        Expected payload structure:
        {
            "event_type": "verification.updated" | "order.updated" | "payment.completed" | "delivery.assigned",
            "user_type": "vendor" | "courier" | "customer",
            "user_id": 123,
            "data": {
                // Event-specific data
            },
            "timestamp": "2025-01-15T10:30:00Z"
        }
        """
        try:
            # Get raw payload for signature verification
            raw_payload = request.body
            
            # Verify webhook signature if configured
            webhook_secret = self.get_webhook_secret()
            if webhook_secret:
                signature = request.META.get('HTTP_X_WEBHOOK_SIGNATURE', '')
                if not self.verify_webhook_signature(raw_payload, signature, webhook_secret):
                    logger.warning("Invalid webhook signature")
                    return Response(
                        {"error": "Invalid signature"}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Parse and validate payload
            payload = request.data
            event_type = payload.get('event_type')
            user_type = payload.get('user_type')
            user_id = payload.get('user_id')
            data = payload.get('data', {})
            
            if not event_type:
                return Response(
                    {"error": "Missing event_type"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Route to appropriate handler
            if event_type.startswith('verification.'):
                return self._handle_verification_webhook(event_type, user_type, user_id, data)
            elif event_type.startswith('order.'):
                return self._handle_order_webhook(event_type, user_type, user_id, data)
            elif event_type.startswith('payment.'):
                return self._handle_payment_webhook(event_type, user_type, user_id, data)
            elif event_type.startswith('delivery.'):
                return self._handle_delivery_webhook(event_type, user_type, user_id, data)
            elif event_type == 'vendor.ready':
                return self._handle_vendor_ready_webhook(data)
            elif event_type == 'whatsapp.message':
                return self._handle_whatsapp_message_webhook(data)
            elif event_type == 'delivery.monitor':
                return self._handle_delivery_monitoring_webhook(data)
            elif event_type == 'vendor.response':
                return self._handle_vendor_response_webhook(data)
            elif event_type == 'courier.response':
                return self._handle_courier_response_webhook(data)
            elif event_type == 'customer.inquiry':
                return self._handle_customer_inquiry_webhook(data)
            elif event_type == 'message.analyze':
                return self._handle_message_analysis_webhook(data)
            elif event_type == 'vendor.ready.proximity':
                return self._handle_vendor_ready_proximity_webhook(data)
            elif event_type == 'courier.contact.info':
                return self._handle_courier_contact_info_webhook(data)
            elif event_type == 'vendor.contact.info':
                return self._handle_vendor_contact_info_webhook(data)
            else:
                return Response(
                    {"error": f"Unsupported event type: {event_type}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_verification_webhook(self, event_type, user_type, user_id, data):
        """Handle verification-related webhooks"""
        try:
            if user_type == 'vendor':
                try:
                    vendor = VendorProfile.objects.get(id=user_id)
                except VendorProfile.DoesNotExist:
                    return Response(
                        {"error": "Vendor not found"}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                if event_type == 'verification.approved':
                    vendor.verification_status = 'approved'
                    vendor.verification_date = timezone.now()
                    vendor.save()
                    
                    # Send notifications
                    notify_vendor_approved(vendor, None)
                    
                    return Response({
                        "success": True,
                        "message": "Vendor verification approved",
                        "vendor_id": vendor.id,
                        "status": "approved",
                        "timestamp": timezone.now().isoformat()
                    })
                
                elif event_type == 'verification.rejected':
                    vendor.verification_status = 'rejected'
                    vendor.verification_date = timezone.now()
                    vendor.verification_notes = data.get('reason', '')
                    vendor.save()
                    
                    # Send notifications
                    notify_vendor_rejected(vendor, None, data.get('reason', ''))
                    
                    return Response({
                        "success": True,
                        "message": "Vendor verification rejected",
                        "vendor_id": vendor.id,
                        "status": "rejected",
                        "reason": data.get('reason', ''),
                        "timestamp": timezone.now().isoformat()
                    })
            
            elif user_type == 'courier':
                try:
                    courier = CourierProfile.objects.get(id=user_id)
                except CourierProfile.DoesNotExist:
                    return Response(
                        {"error": "Courier not found"}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                if event_type == 'verification.approved':
                    courier.verification_status = 'approved'
                    courier.verification_date = timezone.now()
                    courier.save()
                    
                    # Send notifications
                    notify_courier_approved(courier, None)
                    
                    return Response({
                        "success": True,
                        "message": "Courier verification approved",
                        "courier_id": courier.id,
                        "status": "approved",
                        "timestamp": timezone.now().isoformat()
                    })
                
                elif event_type == 'verification.rejected':
                    courier.verification_status = 'rejected'
                    courier.verification_date = timezone.now()
                    courier.verification_notes = data.get('reason', '')
                    courier.save()
                    
                    # Send notifications
                    notify_courier_rejected(courier, None, data.get('reason', ''))
                    
                    return Response({
                        "success": True,
                        "message": "Courier verification rejected",
                        "courier_id": courier.id,
                        "status": "rejected",
                        "reason": data.get('reason', ''),
                        "timestamp": timezone.now().isoformat()
                    })
            
            return Response(
                {"error": f"Unsupported user_type for verification: {user_type}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Error handling verification webhook: {str(e)}")
            return Response(
                {"error": "Failed to process verification webhook"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_order_webhook(self, event_type, user_type, user_id, data):
        """Handle order-related webhooks"""
        try:
            order_id = data.get('order_id')
            if not order_id:
                return Response(
                    {"error": "Missing order_id"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                return Response(
                    {"error": "Order not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if event_type == 'order.updated':
                new_status = data.get('status')
                if new_status:
                    order.status = new_status
                    order.save()
                
                # Send notifications to relevant parties
                if order.vendor:
                    send_vendor_notification(
                        order.vendor.id, 
                        'order.updated', 
                        {
                            'order_id': order.id,
                            'status': new_status,
                            'message': data.get('message', 'Order status updated'),
                            'timestamp': timezone.now().isoformat()
                        }
                    )
                
                if order.courier:
                    send_courier_notification(
                        order.courier.id, 
                        'order.updated', 
                        {
                            'order_id': order.id,
                            'status': new_status,
                            'message': data.get('message', 'Order status updated'),
                            'timestamp': timezone.now().isoformat()
                        }
                    )
                
                return Response({
                    "success": True,
                    "message": "Order status updated",
                    "order_id": order.id,
                    "status": new_status,
                    "timestamp": timezone.now().isoformat()
                })
            
            elif event_type == 'order.assigned':
                courier_id = data.get('courier_id')
                if courier_id:
                    try:
                        courier = CourierProfile.objects.get(id=courier_id)
                        order.courier = courier
                        order.save()
                        
                        # Notify courier
                        send_courier_notification(
                            courier.id, 
                            'delivery.assigned', 
                            {
                                'order_id': order.id,
                                'pickup_location': str(order.vendor.business_address) if order.vendor else None,
                                'delivery_location': str(order.delivery_address),
                                'timestamp': timezone.now().isoformat()
                            }
                        )
                        
                        return Response({
                            "success": True,
                            "message": "Order assigned to courier",
                            "order_id": order.id,
                            "courier_id": courier.id,
                            "timestamp": timezone.now().isoformat()
                        })
                    except CourierProfile.DoesNotExist:
                        return Response(
                            {"error": "Courier not found"}, 
                            status=status.HTTP_404_NOT_FOUND
                        )
            
            return Response(
                {"error": f"Unsupported order event: {event_type}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Error handling order webhook: {str(e)}")
            return Response(
                {"error": "Failed to process order webhook"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_payment_webhook(self, event_type, user_type, user_id, data):
        """Handle payment-related webhooks"""
        try:
            if event_type == 'payment.completed':
                order_id = data.get('order_id')
                amount = data.get('amount')
                payment_method = data.get('payment_method')
                
                if order_id:
                    try:
                        order = Order.objects.get(id=order_id)
                        order.payment_status = 'completed'
                        order.save()
                        
                        # Notify vendor
                        if order.vendor:
                            send_vendor_notification(
                                order.vendor.id, 
                                'payment.received', 
                                {
                                    'order_id': order.id,
                                    'amount': amount,
                                    'payment_method': payment_method,
                                    'timestamp': timezone.now().isoformat()
                                }
                            )
                        
                        return Response({
                            "success": True,
                            "message": "Payment completed",
                            "order_id": order.id,
                            "amount": amount,
                            "timestamp": timezone.now().isoformat()
                        })
                    except Order.DoesNotExist:
                        return Response(
                            {"error": "Order not found"}, 
                            status=status.HTTP_404_NOT_FOUND
                        )
            
            return Response(
                {"error": f"Unsupported payment event: {event_type}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Error handling payment webhook: {str(e)}")
            return Response(
                {"error": "Failed to process payment webhook"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_delivery_webhook(self, event_type, user_type, user_id, data):
        """Handle delivery-related webhooks"""
        try:
            if event_type == 'delivery.assigned':
                order_id = data.get('order_id')
                courier_id = data.get('courier_id')
                
                if order_id and courier_id:
                    try:
                        order = Order.objects.get(id=order_id)
                        courier = CourierProfile.objects.get(id=courier_id)
                        
                        order.courier = courier
                        order.save()
                        
                        # Notify courier
                        send_courier_notification(
                            courier.id, 
                            'delivery.assigned', 
                            {
                                'order_id': order.id,
                                'pickup_location': str(order.vendor.business_address) if order.vendor else None,
                                'delivery_location': str(order.delivery_address),
                                'timestamp': timezone.now().isoformat()
                            }
                        )
                        
                        return Response({
                            "success": True,
                            "message": "Delivery assigned",
                            "order_id": order.id,
                            "courier_id": courier.id,
                            "timestamp": timezone.now().isoformat()
                        })
                    except (Order.DoesNotExist, CourierProfile.DoesNotExist) as e:
                        return Response(
                            {"error": f"Resource not found: {str(e)}"}, 
                            status=status.HTTP_404_NOT_FOUND
                        )
            
            return Response(
                {"error": f"Unsupported delivery event: {event_type}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Error handling delivery webhook: {str(e)}")
            return Response(
                {"error": "Failed to process delivery webhook"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_vendor_ready_webhook(self, data):
        """Handle vendor ready webhook"""
        try:
            vendor_phone = data.get('vendor_phone')
            message = data.get('message', '')
            
            if not vendor_phone:
                return Response(
                    {"error": "Missing vendor_phone"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process vendor ready message
            vendor_ready_service = VendorReadyService()
            result = vendor_ready_service.process_vendor_ready_message(vendor_phone, message)
            
            if result['success']:
                return Response({
                    "success": True,
                    "message": "Vendor ready processed successfully",
                    "vendor_id": result.get('vendor_id'),
                    "orders_processed": result.get('orders_processed', 0),
                    "results": result.get('results', []),
                    "timestamp": timezone.now().isoformat()
                })
            else:
                return Response({
                    "success": False,
                    "error": result.get('error'),
                    "vendor_phone": vendor_phone,
                    "timestamp": timezone.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error handling vendor ready webhook: {str(e)}")
            return Response(
                {"error": "Failed to process vendor ready webhook"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_whatsapp_message_webhook(self, data):
        """Handle WhatsApp message webhook"""
        try:
            # Process WhatsApp message for vendor ready
            vendor_ready_service = VendorReadyService()
            result = vendor_ready_service.handle_whatsapp_webhook(data)
            
            if result['success']:
                return Response({
                    "success": True,
                    "message": "WhatsApp message processed successfully",
                    "vendor_id": result.get('vendor_id'),
                    "orders_processed": result.get('orders_processed', 0),
                    "results": result.get('results', []),
                    "timestamp": timezone.now().isoformat()
                })
            else:
                return Response({
                    "success": False,
                    "error": result.get('error'),
                    "timestamp": timezone.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error handling WhatsApp message webhook: {str(e)}")
            return Response(
                {"error": "Failed to process WhatsApp message webhook"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_delivery_monitoring_webhook(self, data):
        """Handle delivery monitoring webhook"""
        try:
            order_id = data.get('order_id')
            action = data.get('action', 'monitor')
            
            if not order_id:
                return Response(
                    {"error": "Missing order_id"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Initialize status tracking system
            status_tracker = StatusTrackingSystem()
            
            if action == 'start_tracking':
                result = status_tracker.start_delivery_tracking(order_id)
            elif action == 'status_check':
                result = status_tracker.process_status_check(order_id)
            else:
                return Response(
                    {"error": f"Unsupported monitoring action: {action}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if result.get('success'):
                return Response({
                    "success": True,
                    "message": f"Delivery monitoring {action} completed",
                    "result": result,
                    "timestamp": timezone.now().isoformat()
                })
            else:
                return Response({
                    "success": False,
                    "error": result.get('error'),
                    "timestamp": timezone.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error handling delivery monitoring webhook: {str(e)}")
            return Response(
                {"error": "Failed to process delivery monitoring webhook"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_vendor_response_webhook(self, data):
        """Handle vendor response webhook"""
        try:
            order_id = data.get('order_id')
            vendor_phone = data.get('vendor_phone')
            response_message = data.get('response_message')
            
            if not all([order_id, vendor_phone, response_message]):
                return Response(
                    {"error": "Missing required fields: order_id, vendor_phone, response_message"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process vendor response
            status_tracker = StatusTrackingSystem()
            result = status_tracker.process_vendor_response(order_id, vendor_phone, response_message)
            
            if result.get('success'):
                return Response({
                    "success": True,
                    "message": "Vendor response processed successfully",
                    "result": result,
                    "timestamp": timezone.now().isoformat()
                })
            else:
                return Response({
                    "success": False,
                    "error": result.get('error'),
                    "timestamp": timezone.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error handling vendor response webhook: {str(e)}")
            return Response(
                {"error": "Failed to process vendor response webhook"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_courier_response_webhook(self, data):
        """Handle courier response webhook"""
        try:
            order_id = data.get('order_id')
            courier_phone = data.get('courier_phone')
            response_message = data.get('response_message')
            
            if not all([order_id, courier_phone, response_message]):
                return Response(
                    {"error": "Missing required fields: order_id, courier_phone, response_message"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process courier response
            status_tracker = StatusTrackingSystem()
            result = status_tracker.process_courier_response(order_id, courier_phone, response_message)
            
            if result.get('success'):
                return Response({
                    "success": True,
                    "message": "Courier response processed successfully",
                    "result": result,
                    "timestamp": timezone.now().isoformat()
                })
            else:
                return Response({
                    "success": False,
                    "error": result.get('error'),
                    "timestamp": timezone.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error handling courier response webhook: {str(e)}")
            return Response(
                {"error": "Failed to process courier response webhook"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_customer_inquiry_webhook(self, data):
        """Handle customer inquiry webhook"""
        try:
            customer_message = data.get('customer_message')
            customer_id = data.get('customer_id')
            order_id = data.get('order_id')
            
            if not all([customer_message, customer_id]):
                return Response(
                    {"error": "Missing required fields: customer_message, customer_id"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Handle customer inquiry
            status_tracker = StatusTrackingSystem()
            result = status_tracker.handle_customer_inquiry(customer_message, customer_id, order_id)
            
            if result.get('success'):
                return Response({
                    "success": True,
                    "message": "Customer inquiry handled successfully",
                    "result": result,
                    "timestamp": timezone.now().isoformat()
                })
            else:
                return Response({
                    "success": False,
                    "error": result.get('error'),
                    "timestamp": timezone.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error handling customer inquiry webhook: {str(e)}")
            return Response(
                {"error": "Failed to process customer inquiry webhook"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_message_analysis_webhook(self, data):
        """Handle message analysis webhook with auto-identification"""
        try:
            message = data.get('message')
            user_id = data.get('user_id')
            phone_number = data.get('phone_number')
            session_id = data.get('session_id')
            conversation_id = data.get('conversation_id')
            
            if not message:
                return Response(
                    {"error": "Missing required field: message"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get user object if user_id provided
            user = None
            if user_id:
                try:
                    from django.contrib.auth.models import User
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    pass
            
            # Perform auto-identification and intent analysis
            intent_analyzer = IntentAnalysisService()
            result = intent_analyzer.analyze_intent_with_auto_identification(
                message=message,
                user=user,
                phone_number=phone_number,
                session_id=session_id,
                conversation_id=conversation_id
            )
            
            if result.get('intent_analysis', {}).get('error'):
                return Response({
                    "success": False,
                    "error": result['intent_analysis']['error'],
                    "user_identification": result.get('user_identification', {}),
                    "timestamp": timezone.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                "success": True,
                "message": "Message analyzed successfully",
                "result": result,
                "timestamp": timezone.now().isoformat()
            })
                
        except Exception as e:
            logger.error(f"Error handling message analysis webhook: {str(e)}")
            return Response(
                {"error": "Failed to process message analysis webhook"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_vendor_ready_proximity_webhook(self, data):
        """Handle vendor ready webhook with proximity-based courier selection"""
        try:
            vendor_phone = data.get('vendor_phone')
            message = data.get('message', '')
            order_id = data.get('order_id')
            
            if not vendor_phone:
                return Response(
                    {"error": "Missing vendor_phone"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process vendor ready message with proximity-based courier selection
            vendor_ready_service = VendorReadyService()
            result = vendor_ready_service.process_vendor_ready_with_proximity(
                vendor_phone=vendor_phone,
                message=message,
                order_id=order_id
            )
            
            if result['success']:
                return Response({
                    "success": True,
                    "message": "Vendor ready processed with proximity-based courier selection",
                    "result": result,
                    "timestamp": timezone.now().isoformat()
                })
            else:
                return Response({
                    "success": False,
                    "error": result.get('error'),
                    "vendor_phone": vendor_phone,
                    "timestamp": timezone.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error handling vendor ready proximity webhook: {str(e)}")
            return Response(
                {"error": "Failed to process vendor ready proximity webhook"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_courier_contact_info_webhook(self, data):
        """Handle courier contact info webhook"""
        try:
            courier_id = data.get('courier_id')
            
            if not courier_id:
                return Response(
                    {"error": "Missing courier_id"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get courier contact information
            from ..services.proximity_courier_service import ProximityCourierService
            proximity_service = ProximityCourierService()
            result = proximity_service.get_courier_contact_info(courier_id)
            
            if result['success']:
                return Response({
                    "success": True,
                    "message": "Courier contact info retrieved successfully",
                    "contact_info": result['contact_info'],
                    "timestamp": timezone.now().isoformat()
                })
            else:
                return Response({
                    "success": False,
                    "error": result.get('error'),
                    "courier_id": courier_id,
                    "timestamp": timezone.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error handling courier contact info webhook: {str(e)}")
            return Response(
                {"error": "Failed to process courier contact info webhook"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_vendor_contact_info_webhook(self, data):
        """Handle vendor contact info webhook"""
        try:
            vendor_id = data.get('vendor_id')
            order_id = data.get('order_id')
            
            if not vendor_id:
                return Response(
                    {"error": "Missing vendor_id"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get vendor and courier contact information
            vendor_ready_service = VendorReadyService()
            result = vendor_ready_service.get_vendor_courier_contact_info(
                vendor_id=vendor_id,
                order_id=order_id
            )
            
            if result['success']:
                return Response({
                    "success": True,
                    "message": "Vendor and courier contact info retrieved successfully",
                    "result": result,
                    "timestamp": timezone.now().isoformat()
                })
            else:
                return Response({
                    "success": False,
                    "error": result.get('error'),
                    "vendor_id": vendor_id,
                    "timestamp": timezone.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error handling vendor contact info webhook: {str(e)}")
            return Response(
                {"error": "Failed to process vendor contact info webhook"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


