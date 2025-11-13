"""
User subscription API views for Paystack integration
"""
import hmac
import hashlib
import json
import logging
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from bestyy.core_features.user.models import User
from bestyy.core_features.user.services.paystack_service import PaystackService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """
    Paystack webhook endpoint for user subscription events.
    Handles subscription lifecycle events to update user featured status.
    """
    try:
        # Get the raw body and signature
        payload = request.body
        paystack_signature = request.headers.get('X-Paystack-Signature')

        if not paystack_signature:
            logger.warning("Paystack webhook received without signature")
            return JsonResponse({'error': 'Missing signature'}, status=400)

        # Verify webhook signature
        secret = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
        computed_signature = hmac.new(secret, payload, hashlib.sha512).hexdigest()

        if not hmac.compare_digest(computed_signature, paystack_signature):
            logger.warning("Paystack webhook signature verification failed")
            return JsonResponse({'error': 'Invalid signature'}, status=400)

        # Parse webhook data
        try:
            webhook_data = json.loads(payload.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error("Failed to parse Paystack webhook payload")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        event = webhook_data.get('event')
        data = webhook_data.get('data', {})

        logger.info(f"Paystack webhook received: {event}")

        # Extract customer email to identify user
        customer_email = None
        if 'customer' in data:
            customer_email = data['customer'].get('email')
        elif 'email' in data:
            customer_email = data['email']

        if not customer_email:
            logger.warning(f"Paystack webhook {event} received without customer email")
            return JsonResponse({'error': 'No customer email'}, status=400)

        # Find user by email
        try:
            user = User.objects.get(email=customer_email)
        except User.DoesNotExist:
            logger.warning(f"Paystack webhook for unknown user: {customer_email}")
            return JsonResponse({'error': 'User not found'}, status=400)

        # Handle different webhook events
        if event == 'subscription.create':
            # User successfully subscribed
            subscription_code = data.get('subscription_code')
            user.is_featured = True
            user.subscription_code = subscription_code
            user.subscription_status = 'active'
            user.save()

            logger.info(f"User {user.email} subscription activated: {subscription_code}")

        elif event == 'charge.success':
            # Recurring subscription payment successful
            # Ensure user remains featured
            if user.subscription_code:
                user.is_featured = True
                user.subscription_status = 'active'
                user.save()

            logger.info(f"User {user.email} recurring payment successful")

        elif event == 'subscription.disable':
            # Subscription cancelled
            user.is_featured = False
            user.subscription_status = 'cancelled'
            user.save()

            logger.info(f"User {user.email} subscription cancelled")

        elif event == 'subscription.not_renew':
            # Subscription expired
            user.is_featured = False
            user.subscription_status = 'expired'
            user.save()

            logger.info(f"User {user.email} subscription expired")

        else:
            logger.info(f"Unhandled Paystack webhook event: {event}")

        return JsonResponse({'status': 'success'}, status=200)

    except Exception as e:
        logger.error(f"Paystack webhook error: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_subscription_payment(request):
    """
    Verify subscription payment with Paystack and upgrade user.
    Called by frontend after Paystack payment success callback.
    """
    try:
        reference = request.data.get('reference')
        subscription_code = request.data.get('subscription_code')

        if not reference:
            return Response({
                'success': False,
                'error': 'Payment reference is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify payment with Paystack
        paystack_service = PaystackService()
        result = paystack_service.verify_transaction(reference)

        if not result.get('success'):
            return Response({
                'success': False,
                'error': result.get('error', 'Payment verification failed')
            }, status=status.HTTP_400_BAD_REQUEST)

        data = result.get('data', {})
        transaction_status = data.get('status')

        if transaction_status != 'success':
            return Response({
                'success': False,
                'error': f'Payment status: {transaction_status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Payment successful - upgrade user
        user = request.user
        user.is_featured = True
        user.subscription_status = 'active'

        # Save subscription code if provided
        if subscription_code:
            user.subscription_code = subscription_code

        user.save()

        logger.info(f"User {user.email} upgraded to featured via payment verification")

        return Response({
            'success': True,
            'message': 'Subscription activated successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'is_featured': user.is_featured,
                'subscription_status': user.subscription_status
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Subscription verification error: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def subscription_success_page(request):
    """
    Render the subscription success page.
    This page is shown after successful subscription payment.
    """
    return render(request, 'subscription_success.html')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_subscription_status(request):
    """
    Get current user's subscription status.
    """
    user = request.user

    return Response({
        'success': True,
        'subscription': {
            'is_featured': user.is_featured,
            'subscription_code': user.subscription_code,
            'subscription_status': user.subscription_status
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initialize_subscription_payment(request):
    """
    Initialize subscription payment with Paystack.
    Creates a subscription transaction for the user.
    """
    try:
        # For now, we'll use a fixed amount. In production, you might want
        # different subscription tiers
        amount = 500000  # ₦5000 in kobo (5000 * 100)
        plan_name = "Featured User Subscription"

        paystack_service = PaystackService()

        # Create customer if not exists
        customer_result = paystack_service.create_customer(request.user)
        if not customer_result.get('success'):
            return Response({
                'success': False,
                'error': f"Failed to create customer: {customer_result.get('error')}"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create subscription plan (or reuse existing)
        plan_result = paystack_service.create_plan(
            name=plan_name,
            interval='monthly',
            amount=amount,
            description="Monthly featured user subscription"
        )

        if not plan_result.get('success'):
            return Response({
                'success': False,
                'error': f"Failed to create plan: {plan_result.get('error')}"
            }, status=status.HTTP_400_BAD_REQUEST)

        plan_code = plan_result['plan_code']

        # Initialize subscription transaction
        transaction_result = paystack_service.initialize_subscription_transaction(
            email=request.user.email,
            plan_code=plan_code,
            amount=amount
        )

        if not transaction_result.get('success'):
            return Response({
                'success': False,
                'error': f"Failed to initialize subscription: {transaction_result.get('error')}"
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': True,
            'message': 'Subscription payment initialized',
            'payment': {
                'authorization_url': transaction_result['authorization_url'],
                'reference': transaction_result.get('reference'),
                'amount': amount / 100,  # Convert back to naira for display
                'currency': 'NGN'
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Subscription initialization error: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)