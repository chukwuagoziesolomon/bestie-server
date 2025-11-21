"""
Test Payment Views - For development/testing only
Simulates payment verification without real transfers
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.utils import timezone
from bestyy.restaurant_features.order.models import Order
import logging

logger = logging.getLogger(__name__)


class TestPaymentVerificationView(APIView):
    """
    TEST ONLY - Simulate payment verification
    
    POST /api/user/payments/test/verify/
    Body: {
        "order_id": "uuid-of-order"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Only allow in DEBUG mode
        if not settings.DEBUG:
            return Response({
                'success': False,
                'error': 'Test endpoints only available in DEBUG mode'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            order_id = request.data.get('order_id')
            
            if not order_id:
                return Response({
                    'success': False,
                    'error': 'order_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Find the order
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'Order {order_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if already paid
            if order.payment_status:
                return Response({
                    'success': False,
                    'message': 'Order already marked as paid',
                    'order': {
                        'id': str(order.id),
                        'status': order.status,
                        'payment_status': order.payment_status
                    }
                }, status=status.HTTP_200_OK)
            
            # Simulate payment verification
            logger.info(f"🧪 TEST: Marking order {order.id} as PAID")
            
            order.payment_status = True
            order.payment_confirmed = True
            order.payment_confirmed_at = timezone.now()
            order.status = 'confirmed'
            order.confirmed_at = timezone.now()
            order.save()
            
            logger.info(f"✅ TEST: Order {order.id} marked as paid and confirmed")
            
            # Generate pickup OTP for courier
            import random
            pickup_otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            order.pickup_code = pickup_otp
            order.save()
            
            return Response({
                'success': True,
                'message': 'TEST: Payment verified successfully',
                'order': {
                    'id': str(order.id),
                    'order_number': order.order_number,
                    'status': order.status,
                    'payment_status': order.payment_status,
                    'payment_confirmed': order.payment_confirmed,
                    'total_amount': float(order.total_amount),
                    'pickup_code': pickup_otp,
                    'confirmed_at': order.confirmed_at.isoformat() if order.confirmed_at else None
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ TEST: Error verifying payment: {str(e)}")
            return Response({
                'success': False,
                'error': f'Internal error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestListPendingOrdersView(APIView):
    """
    TEST ONLY - List orders awaiting payment
    
    GET /api/user/payments/test/pending/
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        if not settings.DEBUG:
            return Response({
                'success': False,
                'error': 'Test endpoints only available in DEBUG mode'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            # Get orders with pending/confirmed status that haven't been paid
            pending_orders = Order.objects.filter(
                payment_status=False,
                status__in=['awaiting', 'pending', 'confirmed']
            ).order_by('-created_at')[:10]
            
            orders_list = []
            for order in pending_orders:
                orders_list.append({
                    'id': str(order.id),
                    'order_number': order.order_number,
                    'status': order.status,
                    'total_amount': float(order.total_amount),
                    'delivery_address': order.delivery_address,
                    'created_at': order.created_at.isoformat(),
                    'customer': order.customer.username if order.customer else 'N/A',
                    'vendor': order.vendor.business_name if order.vendor else 'N/A',
                    'items_count': order.items.count()
                })
            
            return Response({
                'success': True,
                'count': len(orders_list),
                'orders': orders_list
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error listing pending orders: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
