"""
API views for cryptocurrency payments via NOWPayments
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from decimal import Decimal
from typing import Dict
import logging
from rest_framework.throttling import UserRateThrottle

from bestyy.restaurant_features.order.models import Order
from ..services.crypto_payment_service import CryptoPaymentManager, CryptoRateService

logger = logging.getLogger(__name__)


class CryptoPaymentCreateView(APIView):
    """Create a new cryptocurrency payment for an order"""

    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        """Create crypto payment for order"""
        try:
            order_id = request.data.get('order_id')
            crypto_currency = request.data.get('crypto_currency', 'btc')

            if not order_id:
                return Response({
                    'success': False,
                    'error': 'order_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get order
            order = get_object_or_404(Order, id=order_id, user=request.user)

            # Crypto payments not implemented - return error
            return Response({
                'success': False,
                'error': 'Cryptocurrency payments are not currently available',
                'message': 'Please use Paystack for payment processing'
            }, status=status.HTTP_400_BAD_REQUEST)

        except Order.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Order not found'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Error creating crypto payment: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CryptoPaymentStatusView(APIView):
    """Get crypto payment status"""

    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request, payment_id):
        """Get payment status"""
        try:
            # Crypto payments not implemented
            return Response({
                'success': False,
                'error': 'Cryptocurrency payments are not currently available',
                'message': 'Please use Paystack for payment processing'
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error fetching payment status: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CryptoCurrenciesView(APIView):
    """Get available cryptocurrencies and exchange rates"""

    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        """Get supported cryptocurrencies with rates"""
        try:
            payment_manager = CryptoPaymentManager()
            currencies_response = payment_manager.get_supported_cryptocurrencies()

            if currencies_response["success"]:
                return Response({
                    'success': True,
                    'cryptocurrencies': currencies_response["cryptocurrencies"]
                })
            else:
                return Response(currencies_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Error fetching cryptocurrencies: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CryptoEstimateView(APIView):
    """Get crypto amount estimate for Naira amount"""

    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        """Calculate crypto amount for Naira amount"""
        try:
            naira_amount = request.data.get('naira_amount')
            crypto_currency = request.data.get('crypto_currency', 'btc')

            if not naira_amount:
                return Response({
                    'success': False,
                    'error': 'naira_amount is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                naira_amount = Decimal(str(naira_amount))
            except:
                return Response({
                    'success': False,
                    'error': 'Invalid naira_amount format'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Calculate crypto amount
            rate_service = CryptoRateService()
            crypto_data = rate_service.calculate_crypto_amount(naira_amount, crypto_currency)

            return Response({
                'success': True,
                'estimate': {
                    'naira_amount': float(naira_amount),
                    'crypto_amount': float(crypto_data['crypto_amount']),
                    'crypto_currency': crypto_data['crypto_currency'],
                    'exchange_rate': float(crypto_data['exchange_rate']),
                    'minimum_amount': float(crypto_data['minimum_amount'])
                }
            })

        except Exception as e:
            logger.error(f"Error calculating crypto estimate: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CryptoWebhookView(APIView):
    """Webhook endpoint for NOWPayments callbacks"""

    permission_classes = []  # No authentication for webhooks
    authentication_classes = []
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        """Process NOWPayments webhook"""
        try:
            # Get signature from headers
            signature = request.META.get('HTTP_X_NOWPAYMENTS_SIG', '')

            # Get webhook data
            webhook_data = request.data

            logger.info(f"Received crypto payment webhook: {webhook_data}")

            # Process webhook
            payment_manager = CryptoPaymentManager()
            success = payment_manager.process_webhook(webhook_data, signature)

            if success:
                return Response({'status': 'processed'})
            else:
                return Response(
                    {'error': 'Failed to process webhook'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            logger.error(f"Error processing crypto webhook: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CryptoPaymentListView(APIView):
    """List crypto payments for user"""

    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        """Get user's crypto payments"""
        try:
            # Crypto payments not implemented
            return Response({
                'success': False,
                'error': 'Cryptocurrency payments are not currently available',
                'message': 'Please use Paystack for payment processing',
                'payments': [],
                'pagination': {
                    'page': 1,
                    'page_size': 10,
                    'total_count': 0,
                    'total_pages': 0
                }
            })

        except Exception as e:
            logger.error(f"Error fetching crypto payments: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)