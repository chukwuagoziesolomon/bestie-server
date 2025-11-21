"""
Paystack Pay with Transfer (PwT) API views
Handles bank transfer payment initialization and verification
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import requests
import logging

logger = logging.getLogger(__name__)


class PaystackPwTInitializeView(APIView):
    """
    Initialize Paystack Pay with Transfer charge
    Creates a temporary bank account for the customer to transfer to
    
    POST /api/user/payments/paystack/initialize/
    Body: {
        "amount": 10000,  # Amount in kobo (100 = ₦1)
        "email": "customer@example.com",
        "order_id": "order-uuid"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            # Get request data
            amount = request.data.get('amount')
            email = request.data.get('customer_email') or request.data.get('email')
            order_id = request.data.get('order_id')
            
            # Validate required fields
            if not amount or not email:
                return Response({
                    'success': False,
                    'error': 'Amount and email are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Convert amount to kobo if it's in naira
            amount_in_kobo = int(float(amount) * 100)
            
            # Set account expiry (8 hours from now - Paystack maximum)
            expiry_time = timezone.now() + timedelta(hours=8)
            expiry_iso = expiry_time.isoformat()
            
            # Call Paystack Charge API
            paystack_secret = getattr(settings, 'PAYSTACK_SECRET_KEY', None)
            
            if not paystack_secret:
                logger.error("PAYSTACK_SECRET_KEY not configured")
                return Response({
                    'success': False,
                    'error': 'Payment service not configured'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Prepare Paystack API request
            paystack_url = "https://api.paystack.co/charge"
            headers = {
                'Authorization': f'Bearer {paystack_secret}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'email': email,
                'amount': str(amount_in_kobo),
                'bank_transfer': {
                    'account_expires_at': expiry_iso
                },
                'metadata': {
                    'order_id': str(order_id),
                    'channel': 'whatsapp'
                }
            }
            
            logger.info(f"Initiating Paystack PwT for order {order_id}, amount: ₦{amount}")
            
            # Make API call to Paystack
            response = requests.post(paystack_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status'):
                    # Extract bank transfer details
                    charge_data = data.get('data', {})
                    display_text = charge_data.get('display_text', '')
                    
                    # Extract bank name from bank object
                    bank_data = charge_data.get('bank', {})
                    bank_name = bank_data.get('name', 'Wema Bank') if isinstance(bank_data, dict) else 'Wema Bank'
                    
                    # Parse bank account details from Paystack response
                    logger.info(f"✅ Paystack PwT created: {charge_data.get('account_number')} - {charge_data.get('account_name')}")
                    
                    return Response({
                        'success': True,
                        'reference': charge_data.get('reference'),
                        'account_number': charge_data.get('account_number'),
                        'account_name': charge_data.get('account_name', 'PAY-BESTYY'),
                        'bank_name': bank_name,
                        'amount': amount,
                        'expires_at': charge_data.get('account_expires_at') or expiry_iso,
                        'display_text': display_text,
                        'order_id': order_id
                    }, status=status.HTTP_200_OK)
                else:
                    logger.error(f"Paystack PwT failed: {data.get('message')}")
                    return Response({
                        'success': False,
                        'error': data.get('message', 'Failed to create payment')
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                logger.error(f"Paystack API error: {response.status_code} - {response.text}")
                return Response({
                    'success': False,
                    'error': f'Payment service error: {response.status_code}'
                }, status=status.HTTP_502_BAD_GATEWAY)
                
        except Exception as e:
            logger.error(f"Error initializing Paystack PwT: {str(e)}")
            return Response({
                'success': False,
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _extract_account_from_display(self, display_text):
        """Extract account number from Paystack display text"""
        try:
            # Paystack display_text usually contains account details
            # Format: "Transfer NGN... to Account:..."
            if 'Account:' in display_text:
                parts = display_text.split('Account:')
                if len(parts) > 1:
                    # Extract just the numbers
                    account_part = parts[1].strip()
                    account_number = ''.join(filter(str.isdigit, account_part.split()[0]))
                    return account_number
            return None
        except Exception as e:
            logger.error(f"Error extracting account from display text: {str(e)}")
            return None


class PaystackWebhookView(APIView):
    """
    Handle Paystack webhooks for payment verification
    Listens to charge.success and bank.transfer.rejected events
    
    POST /api/user/webhooks/paystack/
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            # Verify webhook signature
            signature = request.headers.get('X-Paystack-Signature')
            
            if not signature:
                logger.warning("Paystack webhook received without signature")
                return Response({'status': 'error', 'message': 'No signature'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            # Verify signature (important for production)
            # For now, we'll log and process
            
            event_type = request.data.get('event')
            event_data = request.data.get('data', {})
            
            logger.info(f"Paystack webhook received: {event_type}")
            
            if event_type == 'charge.success':
                return self._handle_charge_success(event_data)
            elif event_type == 'bank.transfer.rejected':
                return self._handle_transfer_rejected(event_data)
            else:
                logger.info(f"Unhandled webhook event: {event_type}")
                return Response({'status': 'ok'}, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Error processing Paystack webhook: {str(e)}")
            return Response({'status': 'error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _handle_charge_success(self, data):
        """Handle successful payment"""
        try:
            from bestyy.restaurant_features.order.models import Order
            
            reference = data.get('reference')
            amount = data.get('amount', 0) / 100  # Convert from kobo to naira
            metadata = data.get('metadata', {})
            order_id = metadata.get('order_id')
            
            logger.info(f"Payment successful - Reference: {reference}, Order: {order_id}, Amount: ₦{amount}")
            
            if order_id:
                try:
                    order = Order.objects.get(id=order_id)
                    order.status = 'confirmed'
                    order.payment_status = 'paid'
                    order.payment_reference = reference
                    order.save()
                    
                    logger.info(f"Order {order_id} marked as paid")
                    
                    # TODO: Send receipt to customer
                    # TODO: Generate OTP for courier
                    # TODO: Notify vendor
                    
                except Order.DoesNotExist:
                    logger.error(f"Order {order_id} not found for payment")
            
            return Response({'status': 'success'}, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error handling charge success: {str(e)}")
            return Response({'status': 'error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _handle_transfer_rejected(self, data):
        """Handle rejected transfer"""
        try:
            reference = data.get('reference')
            logger.warning(f"Payment rejected - Reference: {reference}")
            
            # TODO: Notify customer about rejected payment
            
            return Response({'status': 'success'}, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error handling transfer rejection: {str(e)}")
            return Response({'status': 'error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
