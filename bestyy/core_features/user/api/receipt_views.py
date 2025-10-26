"""
API views for payment receipts
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
import logging

from ..models import Order
from ..services.receipt_service import ReceiptService

logger = logging.getLogger(__name__)


class PaymentReceiptView(APIView):
    """
    Send payment receipt to user after successful payment
    
    POST /api/user/receipts/send/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Send payment receipt for an order"""
        try:
            order_id = request.data.get('order_id')
            
            if not order_id:
                return Response({
                    'success': False,
                    'error': 'order_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get order
            order = get_object_or_404(Order, id=order_id, user=request.user)
            
            # Check if payment is confirmed
            if not order.payment_confirmed:
                return Response({
                    'success': False,
                    'error': 'Payment not confirmed yet'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Send receipt
            result = ReceiptService.send_payment_receipt(order)
            
            if result['success']:
                return Response({
                    'success': True,
                    'message': result['message'],
                    'email_sent': result['email_sent'],
                    'whatsapp_sent': result['whatsapp_sent']
                })
            else:
                return Response({
                    'success': False,
                    'error': result['error']
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Order.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Order not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f"Error sending payment receipt: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReceiptPreviewView(APIView):
    """
    Preview payment receipt HTML
    
    GET /api/user/receipts/preview/{order_id}/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, order_id):
        """Preview receipt HTML for an order"""
        try:
            # Get order
            order = get_object_or_404(Order, id=order_id, user=request.user)
            
            # Generate receipt data
            receipt_data = ReceiptService.generate_receipt_data(order)
            if not receipt_data:
                return Response({
                    'success': False,
                    'error': 'Failed to generate receipt data'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Render HTML
            receipt_html = ReceiptService.render_receipt_html(receipt_data)
            if not receipt_html:
                return Response({
                    'success': False,
                    'error': 'Failed to render receipt HTML'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                'success': True,
                'receipt_html': receipt_html,
                'receipt_data': receipt_data
            })
            
        except Order.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Order not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f"Error previewing receipt: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


