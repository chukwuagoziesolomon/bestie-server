"""
WhatsApp notification testing API
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404

from bestyy.core_features.user.models import VendorProfile
from bestyy.restaurant_features.order.models import Order
from bestyy.core_features.user.services.whatsapp_vendor_service import WhatsAppVendorNotificationService


class WhatsAppTestView(APIView):
    """
    Test WhatsApp notifications for vendors
    
    POST /api/user/whatsapp/test/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Test WhatsApp notification"""
        try:
            vendor_id = request.data.get('vendor_id')
            phone_number = request.data.get('phone_number')
            message_type = request.data.get('message_type', 'order_notification')
            
            if not vendor_id and not phone_number:
                return Response({
                    'success': False,
                    'error': 'Either vendor_id or phone_number is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get vendor if vendor_id provided
            vendor = None
            if vendor_id:
                vendor = get_object_or_404(VendorProfile, id=vendor_id)
                phone_number = phone_number or getattr(vendor, 'whatsapp_number', None) or getattr(vendor, 'contact_phone', None)
            
            if not phone_number:
                return Response({
                    'success': False,
                    'error': 'No phone number available'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create test order data
            test_order_data = self._create_test_order_data(vendor, message_type)
            
            # Send WhatsApp notification
            whatsapp_service = WhatsAppVendorNotificationService()
            
            if message_type == 'order_notification':
                result = whatsapp_service.send_order_notification(phone_number, test_order_data)
            elif message_type == 'automatic_reply':
                result = whatsapp_service.send_automatic_reply(phone_number, test_order_data, 'order_confirmation')
            else:
                return Response({
                    'success': False,
                    'error': 'Invalid message_type. Use "order_notification" or "automatic_reply"'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'success': True,
                'message': f'WhatsApp {message_type} sent successfully',
                'phone_number': phone_number,
                'vendor': {
                    'id': vendor.id if vendor else None,
                    'business_name': vendor.business_name if vendor else 'Test Vendor'
                },
                'result': result,
                'service_info': {
                    'service_used': result.get('service_used', 'unknown'),
                    'environment': result.get('environment', 'unknown')
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _create_test_order_data(self, vendor, message_type):
        """Create test order data for WhatsApp notifications"""
        from datetime import datetime, timezone
        
        # Create mock vendor if none provided
        if not vendor:
            class MockVendor:
                id = 999
                business_name = "Test Burger Palace"
                business_address = "123 Test Street, Test City"
                delivery_time = "15-25 min"
            
            vendor = MockVendor()
        
        # Create mock order
        class MockOrder:
            id = 12345
            created_at = datetime.now(timezone.utc)
            total_price = 4500.00
        
        order = MockOrder()
        
        # Create test order data
        order_data = {
            'vendor': vendor,
            'order': order,
            'order_items': [
                {
                    'name': 'Classic Beef Burger',
                    'quantity': 1,
                    'base_price': 2500,
                    'variants': [
                        {'name': 'Regular', 'price_modifier': 0},
                        {'name': 'Extra Cheese', 'price_modifier': 1500}
                    ],
                    'special_instructions': 'No onions, extra spicy',
                    'total_price': 4000
                },
                {
                    'name': 'French Fries',
                    'quantity': 1,
                    'base_price': 500,
                    'variants': [],
                    'special_instructions': '',
                    'total_price': 500
                }
            ],
            'customer': {
                'name': 'John Doe',
                'email': 'john.doe@example.com',
                'phone': '+234-123-456-7890'
            },
            'total_amount': 4500
        }
        
        return order_data


class WhatsAppConfigView(APIView):
    """
    Get WhatsApp configuration status
    
    GET /api/user/whatsapp/config/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get WhatsApp configuration status"""
        try:
            from django.conf import settings
            
            config = {
                'whatsapp_business_api': {
                    'access_token_configured': bool(getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)),
                    'phone_number_id_configured': bool(getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', None)),
                    'verify_token_configured': bool(getattr(settings, 'WHATSAPP_VERIFY_TOKEN', None))
                },
                'twilio_whatsapp': {
                    'account_sid_configured': bool(getattr(settings, 'TWILIO_ACCOUNT_SID', None)),
                    'auth_token_configured': bool(getattr(settings, 'TWILIO_AUTH_TOKEN', None)),
                    'whatsapp_from_configured': bool(getattr(settings, 'TWILIO_WHATSAPP_FROM', None))
                }
            }
            
            # Determine which service is available
            whatsapp_business_available = all([
                config['whatsapp_business_api']['access_token_configured'],
                config['whatsapp_business_api']['phone_number_id_configured']
            ])
            
            twilio_whatsapp_available = all([
                config['twilio_whatsapp']['account_sid_configured'],
                config['twilio_whatsapp']['auth_token_configured'],
                config['twilio_whatsapp']['whatsapp_from_configured']
            ])
            
            # Determine current service being used
            is_production = not getattr(settings, 'DEBUG', True)
            current_service = None
            
            if is_production:
                if whatsapp_business_available:
                    current_service = 'whatsapp_business_api'
                elif twilio_whatsapp_available:
                    current_service = 'twilio'
            else:
                if twilio_whatsapp_available:
                    current_service = 'twilio'
                elif whatsapp_business_available:
                    current_service = 'whatsapp_business_api'
            
            return Response({
                'success': True,
                'configuration': config,
                'environment': {
                    'is_production': is_production,
                    'debug_mode': getattr(settings, 'DEBUG', True)
                },
                'available_services': {
                    'whatsapp_business_api': whatsapp_business_available,
                    'twilio_whatsapp': twilio_whatsapp_available
                },
                'current_service': current_service,
                'service_preference': {
                    'development': 'twilio',
                    'production': 'whatsapp_business_api'
                },
                'recommended_service': 'whatsapp_business_api' if whatsapp_business_available else 'twilio_whatsapp' if twilio_whatsapp_available else None
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
