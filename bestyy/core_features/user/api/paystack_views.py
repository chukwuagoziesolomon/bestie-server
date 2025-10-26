from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404
from bestyy.core_features.user.models import User, VendorSubscription, SubscriptionPlan
from bestyy.core_features.user.services.paystack_service import PaystackService
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_dedicated_account(request):
    """
    Create a dedicated virtual account for the authenticated user
    """
    user = request.user
    preferred_bank = request.data.get('preferred_bank', 'titan-paystack')

    # Check if user already has a DVA
    if hasattr(user, 'dedicated_account') and user.dedicated_account.is_active:
        return Response({
            'error': 'User already has an active dedicated virtual account',
            'account': {
                'account_number': user.dedicated_account.account_number,
                'account_name': user.dedicated_account.account_name,
                'bank_name': user.dedicated_account.bank_name
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    paystack_service = PaystackService()

    # Try single-step assignment first (recommended)
    result = paystack_service.assign_dedicated_account(user, preferred_bank)

    if result['success']:
        account = result['account']
        return Response({
            'success': True,
            'message': 'Dedicated virtual account created successfully',
            'account': {
                'account_number': account.account_number,
                'account_name': account.account_name,
                'bank_name': account.bank_name,
                'bank_slug': account.bank_slug,
                'is_active': account.is_active
            }
        })

    # If single-step fails, try multi-step
    logger.warning(f"Single-step DVA creation failed for user {user.id}: {result.get('error')}")
    result = paystack_service.create_dedicated_account(user, preferred_bank)

    if result['success']:
        account = result['account']
        return Response({
            'success': True,
            'message': 'Dedicated virtual account created successfully',
            'account': {
                'account_number': account.account_number,
                'account_name': account.account_name,
                'bank_name': account.bank_name,
                'bank_slug': account.bank_slug,
                'is_active': account.is_active
            }
        })

    return Response({
        'error': result.get('error', 'Failed to create dedicated virtual account')
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dedicated_account(request):
    """
    Get the user's dedicated virtual account details
    """
    user = request.user

    try:
        account = user.dedicated_account
        if not account.is_active:
            return Response({
                'error': 'Dedicated virtual account is not active'
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'account_number': account.account_number,
            'account_name': account.account_name,
            'bank_name': account.bank_name,
            'bank_slug': account.bank_slug,
            'is_active': account.is_active,
            'is_assigned': account.is_assigned
        })

    except DedicatedVirtualAccount.DoesNotExist:
        return Response({
            'error': 'No dedicated virtual account found. Please create one first.'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def requery_account(request):
    """
    Requery the user's dedicated account for pending transactions
    """
    user = request.user
    date = request.data.get('date')  # Optional: YYYY-MM-DD format

    try:
        account = user.dedicated_account
        if not account.is_active:
            return Response({
                'error': 'Dedicated virtual account is not active'
            }, status=status.HTTP_400_BAD_REQUEST)

        paystack_service = PaystackService()
        transactions = paystack_service.requery_account(
            account.account_number,
            account.bank_slug,
            date
        )

        return Response({
            'success': True,
            'transactions': transactions
        })

    except DedicatedVirtualAccount.DoesNotExist:
        return Response({
            'error': 'No dedicated virtual account found'
        }, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# SUBSCRIPTION PAYMENT ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_subscription_plans(request):
    """
    Get available subscription plans for vendor featured status
    """
    from ..models import SubscriptionPlan

    plans = SubscriptionPlan.get_active_plans()
    plans_data = []

    for plan in plans:
        plans_data.append({
            'id': plan.plan_type,
            'name': plan.name,
            'duration_days': plan.duration_days,
            'price': float(plan.price),
            'description': plan.description or f'Get featured for {plan.duration_days} days - appear first in recommendations',
            'featured_priority': plan.featured_priority
        })

    return Response({
        'success': True,
        'plans': plans_data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_subscription(request):
    """
    Purchase a subscription plan for vendor featured status
    """
    user = request.user
    plan_id = request.data.get('plan_id')

    if not plan_id:
        return Response({
            'success': False,
            'error': 'plan_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check if user is a vendor
    if not user.has_role('vendor'):
        return Response({
            'success': False,
            'error': 'Only vendors can purchase featured subscriptions'
        }, status=status.HTTP_403_FORBIDDEN)

    # Get vendor profile
    try:
        vendor_profile = user.vendor_profile
    except:
        return Response({
            'success': False,
            'error': 'Vendor profile not found'
        }, status=status.HTTP_404_NOT_FOUND)

    # Get the subscription plan
    try:
        plan = SubscriptionPlan.objects.get(plan_type=plan_id, is_active=True)
    except SubscriptionPlan.DoesNotExist:
        return Response({
            'success': False,
            'error': f'Invalid or inactive plan: {plan_id}'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check if vendor already has an active subscription
    active_subscription = VendorSubscription.objects.filter(
        vendor=vendor_profile,
        status='active',
        end_date__gt=timezone.now()
    ).first()

    if active_subscription:
        return Response({
            'success': False,
            'error': 'You already have an active featured subscription',
            'current_subscription': {
                'plan_type': active_subscription.plan_type,
                'end_date': active_subscription.end_date.isoformat(),
                'days_remaining': (active_subscription.end_date - timezone.now()).days
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    # Create subscription record (pending payment)
    subscription = VendorSubscription.objects.create(
        vendor=vendor_profile,
        plan=plan,
        status='pending',
        amount_paid=plan.price,
        start_date=timezone.now(),
        end_date=timezone.now() + timedelta(days=plan.duration_days)
    )

    # Initialize Paystack payment
    paystack_service = PaystackService()

    # Create payment reference
    reference = f"sub_{subscription.id}_{int(timezone.now().timestamp())}"

    # Initialize transaction
    payment_data = {
        'email': user.email,
        'amount': int(plan.price * 100),  # Convert to kobo
        'reference': reference,
        'callback_url': f"{request.build_absolute_uri('/')}api/user/subscription/callback/",
        'metadata': {
            'subscription_id': subscription.id,
            'plan_id': plan_id,
            'vendor_id': vendor_profile.id,
            'user_id': user.id
        }
    }

    result = paystack_service.initialize_transaction(payment_data)

    if result['success']:
        # Update subscription with payment reference
        subscription.payment_reference = reference
        subscription.save()

        return Response({
            'success': True,
            'message': f'Subscription payment initialized for {plan.name} plan',
            'subscription': {
                'id': subscription.id,
                'plan_type': plan_id,
                'amount': float(plan.price),
                'duration_days': plan.duration_days,
                'status': 'pending_payment'
            },
            'payment': {
                'reference': reference,
                'authorization_url': result['authorization_url'],
                'access_code': result['access_code'],
                'amount': float(plan.price),
                'currency': 'NGN',
                'available_payment_methods': [
                    {
                        'id': 'card',
                        'name': 'Debit/Credit Card',
                        'description': 'Visa, Mastercard, Verve',
                        'icon': '💳',
                        'processing_time': 'Instant'
                    },
                    {
                        'id': 'bank_transfer',
                        'name': 'Bank Transfer',
                        'description': 'Direct bank transfer',
                        'icon': '🏦',
                        'processing_time': '5-15 minutes'
                    },
                    {
                        'id': 'ussd',
                        'name': 'USSD',
                        'description': 'Dial *737* or *833*',
                        'icon': '📱',
                        'processing_time': 'Instant'
                    },
                    {
                        'id': 'qr',
                        'name': 'QR Code',
                        'description': 'Scan with banking app',
                        'icon': '📱',
                        'processing_time': 'Instant'
                    }
                ]
            }
        })

    # Clean up failed subscription
    subscription.delete()

    return Response({
        'success': False,
        'error': result.get('error', 'Failed to initialize payment')
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_subscription_status(request):
    """
    Get current subscription status for vendor
    """
    user = request.user

    if not user.has_role('vendor'):
        return Response({
            'success': False,
            'error': 'Only vendors can check subscription status'
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        vendor_profile = user.vendor_profile
    except:
        return Response({
            'success': False,
            'error': 'Vendor profile not found'
        }, status=status.HTTP_404_NOT_FOUND)

    # Get current subscription
    subscription = VendorSubscription.objects.filter(
        vendor=vendor_profile
    ).order_by('-created_at').first()

    if not subscription:
        return Response({
            'success': True,
            'has_subscription': False,
            'message': 'No subscription found'
        })

    # Check if subscription is active
    is_active = (
        subscription.status == 'active' and
        subscription.end_date and
        subscription.end_date > timezone.now()
    )

    response_data = {
        'success': True,
        'has_subscription': True,
        'subscription': {
            'id': subscription.id,
            'plan_type': subscription.plan_type,
            'status': subscription.status,
            'amount_paid': float(subscription.amount_paid),
            'start_date': subscription.start_date.isoformat() if subscription.start_date else None,
            'end_date': subscription.end_date.isoformat() if subscription.end_date else None,
            'is_featured': subscription.is_featured,
            'featured_priority': subscription.featured_priority,
            'payment_reference': subscription.payment_reference
        },
        'is_active': is_active
    }

    if is_active and subscription.end_date:
        response_data['days_remaining'] = (subscription.end_date - timezone.now()).days

    return Response(response_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """
    Cancel an active subscription (effective immediately)
    """
    user = request.user

    if not user.has_role('vendor'):
        return Response({
            'success': False,
            'error': 'Only vendors can cancel subscriptions'
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        vendor_profile = user.vendor_profile
    except:
        return Response({
            'success': False,
            'error': 'Vendor profile not found'
        }, status=status.HTTP_404_NOT_FOUND)

    # Get active subscription
    subscription = VendorSubscription.objects.filter(
        vendor=vendor_profile,
        status='active',
        end_date__gt=timezone.now()
    ).first()

    if not subscription:
        return Response({
            'success': False,
            'error': 'No active subscription found'
        }, status=status.HTTP_404_NOT_FOUND)

    # Cancel subscription
    subscription.status = 'cancelled'
    subscription.end_date = timezone.now()  # End immediately
    subscription.is_featured = False
    subscription.featured_priority = 0
    subscription.save()

    return Response({
        'success': True,
        'message': 'Subscription cancelled successfully',
        'subscription': {
            'id': subscription.id,
            'status': 'cancelled',
            'end_date': subscription.end_date.isoformat()
        }
    })


@api_view(['POST'])
@permission_classes([])  # No authentication for webhook
def subscription_payment_webhook(request):
    """
    Handle Paystack webhook for subscription payments
    """
    # Verify webhook signature (implement in production)
    # For now, process the webhook

    event = request.data.get('event')
    data = request.data.get('data', {})

    if event == 'charge.success':
        reference = data.get('reference', '')

        # Check if this is a subscription payment
        if reference.startswith('sub_'):
            try:
                # Extract subscription ID from reference
                parts = reference.split('_')
                if len(parts) >= 2:
                    subscription_id = int(parts[1])

                    subscription = VendorSubscription.objects.get(id=subscription_id)

                    # Activate subscription
                    subscription.status = 'active'
                    subscription.is_featured = True
                    subscription.featured_priority = subscription.plan.featured_priority
                    subscription.featured_expiry = subscription.end_date
                    subscription.save()

                    # Update vendor profile directly for immediate effect
                    vendor_profile = subscription.vendor
                    vendor_profile.is_featured = True
                    vendor_profile.featured_priority = subscription.plan.featured_priority
                    vendor_profile.featured_expiry = subscription.end_date
                    vendor_profile.save()

                    logger.info(f"Subscription {subscription_id} activated for vendor {vendor_profile.business_name}")

                    # Send notification to vendor
                    try:
                        message = f"🎉 Congratulations! Your featured subscription has been activated. You now appear first in search results and recommendations for {subscription.plan.duration_days} days."

                        # Send via WhatsApp if available
                        if hasattr(vendor_profile.user, 'phone') and vendor_profile.user.phone:
                            from whatsapp_ai.services.whatsapp_service import WhatsAppService
                            whatsapp_service = WhatsAppService()
                            whatsapp_service.send_message(
                                to=vendor_profile.user.phone,
                                message=message,
                                message_type='subscription_activated'
                            )

                        # Send via email
                        from django.core.mail import send_mail
                        from django.conf import settings

                        email_subject = "Featured Subscription Activated! 🎉"
                        email_html = f"""
                        <html>
                        <body>
                            <h2>Featured Status Activated!</h2>
                            <p>Dear {vendor_profile.business_name},</p>
                            <p>{message}</p>
                            <p><strong>Plan Details:</strong></p>
                            <ul>
                                <li>Duration: {subscription.plan.duration_days} days</li>
                                <li>Priority Level: {subscription.plan.featured_priority}</li>
                                <li>Expires: {subscription.end_date.strftime('%B %d, %Y')}</li>
                            </ul>
                            <p>You will now appear prominently in search results and recommendations.</p>
                            <p>Best regards,<br>Bestyy Team</p>
                        </body>
                        </html>
                        """

                        send_mail(
                            subject=email_subject,
                            message=message,  # Plain text version
                            html_message=email_html,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[vendor_profile.user.email],
                            fail_silently=True
                        )

                    except Exception as e:
                        logger.error(f"Failed to send activation notification: {str(e)}")

            except (ValueError, VendorSubscription.DoesNotExist) as e:
                logger.error(f"Failed to process subscription webhook: {str(e)}")

    return Response({'status': 'success'})


@api_view(['GET'])
@permission_classes([])  # Public endpoint
def subscription_payment_callback(request):
    """
    Handle payment callback from Paystack
    """
    reference = request.GET.get('reference')

    if not reference or not reference.startswith('sub_'):
        return Response({
            'error': 'Invalid payment reference'
        }, status=status.HTTP_400_BAD_REQUEST)

    # In production, verify payment with Paystack
    # For now, redirect to success page

    return Response({
        'success': True,
        'message': 'Payment completed. Subscription will be activated shortly.',
        'reference': reference
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_transfer_recipient(request):
    """
    Create a transfer recipient for vendor or courier payouts
    """
    user = request.user
    recipient_type = request.data.get('recipient_type')  # 'vendor' or 'courier'
    account_number = request.data.get('account_number')
    account_name = request.data.get('account_name')
    bank_code = request.data.get('bank_code')
    bank_name = request.data.get('bank_name')

    if not all([recipient_type, account_number, account_name, bank_code, bank_name]):
        return Response({
            'error': 'recipient_type, account_number, account_name, bank_code, and bank_name are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    if recipient_type not in ['vendor', 'courier']:
        return Response({
            'error': 'recipient_type must be either "vendor" or "courier"'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check if user already has a transfer recipient
    if hasattr(user, 'transfer_recipient'):
        return Response({
            'error': f'User already has a {recipient_type} transfer recipient'
        }, status=status.HTTP_400_BAD_REQUEST)

    paystack_service = PaystackService()

    # Create recipient on Paystack
    result = paystack_service.create_transfer_recipient(
        recipient_type='nuban',  # Nigerian bank account
        name=account_name,
        account_number=account_number,
        bank_code=bank_code,
        currency='NGN'
    )

    if result['success']:
        # Create local record
        from bestyy.core_features.user.models import TransferRecipient
        recipient = TransferRecipient.objects.create(
            user=user,
            recipient_type=recipient_type,
            paystack_recipient_code=result['recipient_code'],
            account_number=account_number,
            account_name=account_name,
            bank_code=bank_code,
            bank_name=bank_name
        )

        return Response({
            'success': True,
            'message': f'{recipient_type.title()} transfer recipient created successfully',
            'recipient': {
                'id': recipient.id,
                'recipient_code': recipient.paystack_recipient_code,
                'account_number': recipient.account_number,
                'account_name': recipient.account_name,
                'bank_name': recipient.bank_name
            }
        })

    return Response({
        'error': result.get('error', 'Failed to create transfer recipient')
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_transfer_recipient(request):
    """
    Get user's transfer recipient details
    """
    user = request.user

    try:
        recipient = user.transfer_recipient
        return Response({
            'recipient_type': recipient.recipient_type,
            'account_number': recipient.account_number,
            'account_name': recipient.account_name,
            'bank_name': recipient.bank_name,
            'bank_code': recipient.bank_code,
            'is_active': recipient.is_active
        })

    except:
        return Response({
            'error': 'No transfer recipient found. Please create one first.'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_transfers(request):
    """
    List user's transfer history
    """
    user = request.user

    try:
        recipient = user.transfer_recipient
        transfers = recipient.transfers.order_by('-initiated_at')[:50]  # Last 50 transfers

        transfer_data = []
        for transfer in transfers:
            transfer_data.append({
                'id': transfer.id,
                'order_id': transfer.order.id,
                'amount': float(transfer.amount),
                'reference': transfer.paystack_reference,
                'status': transfer.status,
                'reason': transfer.reason,
                'initiated_at': transfer.initiated_at.isoformat(),
                'completed_at': transfer.completed_at.isoformat() if transfer.completed_at else None
            })

        return Response({
            'transfers': transfer_data
        })

    except:
        return Response({
            'error': 'No transfer recipient found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_system_settings(request):
    """
    Get current system settings for commissions and fees
    """
    from bestyy.core_features.user.models import SystemSettings

    settings = SystemSettings.get_active_settings()

    return Response({
        'vendor_commission_percentage': float(settings.vendor_commission_percentage),
        'base_delivery_fee': float(settings.base_delivery_fee),
        'delivery_fee_per_km': float(settings.delivery_fee_per_km),
        'rider_base_fee': float(settings.rider_base_fee),
        'rider_fee_per_km': float(settings.rider_fee_per_km),
        'service_fee_percentage': float(settings.service_fee_percentage)
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@permission_required('is_staff', raise_exception=True)
def update_system_settings(request):
    """
    Update system settings (admin only)
    """
    from bestyy.core_features.user.models import SystemSettings

    settings = SystemSettings.get_active_settings()

    # Update fields if provided
    if 'vendor_commission_percentage' in request.data:
        settings.vendor_commission_percentage = request.data['vendor_commission_percentage']
    if 'base_delivery_fee' in request.data:
        settings.base_delivery_fee = request.data['base_delivery_fee']
    if 'delivery_fee_per_km' in request.data:
        settings.delivery_fee_per_km = request.data['delivery_fee_per_km']
    if 'rider_base_fee' in request.data:
        settings.rider_base_fee = request.data['rider_base_fee']
    if 'rider_fee_per_km' in request.data:
        settings.rider_fee_per_km = request.data['rider_fee_per_km']
    if 'service_fee_percentage' in request.data:
        settings.service_fee_percentage = request.data['service_fee_percentage']

    settings.created_by = request.user
    settings.save()

    return Response({
        'success': True,
        'message': 'System settings updated successfully',
        'settings': {
            'vendor_commission_percentage': float(settings.vendor_commission_percentage),
            'base_delivery_fee': float(settings.base_delivery_fee),
            'delivery_fee_per_km': float(settings.delivery_fee_per_km),
            'rider_base_fee': float(settings.rider_base_fee),
            'rider_fee_per_km': float(settings.rider_fee_per_km),
            'service_fee_percentage': float(settings.service_fee_percentage)
        }
    })


@api_view(['GET'])
@permission_classes([])
def get_supported_banks(request):
    """
    Get list of supported banks for dedicated virtual accounts
    """
    paystack_service = PaystackService()
    banks = paystack_service.get_supported_banks()

    return Response({
        'banks': banks
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_split_payment(request):
    """
    Add split payment configuration to user's dedicated account
    """
    user = request.user
    subaccount_code = request.data.get('subaccount_code')
    split_code = request.data.get('split_code')

    if not subaccount_code and not split_code:
        return Response({
            'error': 'Either subaccount_code or split_code is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        account = user.dedicated_account
        if not account.is_active:
            return Response({
                'error': 'Dedicated virtual account is not active'
            }, status=status.HTTP_400_BAD_REQUEST)

        paystack_service = PaystackService()
        result = paystack_service.add_split_payment(
            account.account_number,
            subaccount_code,
            split_code
        )

        if result['success']:
            # Update local record
            if subaccount_code:
                account.subaccount_code = subaccount_code
            if split_code:
                account.split_code = split_code
            account.save()

            return Response({
                'success': True,
                'message': 'Split payment configuration added successfully'
            })

        return Response({
            'error': result.get('error', 'Failed to add split payment')
        }, status=status.HTTP_400_BAD_REQUEST)

    except DedicatedVirtualAccount.DoesNotExist:
        return Response({
            'error': 'No dedicated virtual account found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_split_payment(request):
    """
    Remove split payment configuration from user's dedicated account
    """
    user = request.user

    try:
        account = user.dedicated_account
        if not account.is_active:
            return Response({
                'error': 'Dedicated virtual account is not active'
            }, status=status.HTTP_400_BAD_REQUEST)

        paystack_service = PaystackService()
        result = paystack_service.remove_split_payment(account.account_number)

        if result['success']:
            # Update local record
            account.subaccount_code = None
            account.split_code = None
            account.save()

            return Response({
                'success': True,
                'message': 'Split payment configuration removed successfully'
            })

        return Response({
            'error': result.get('error', 'Failed to remove split payment')
        }, status=status.HTTP_400_BAD_REQUEST)

    except DedicatedVirtualAccount.DoesNotExist:
        return Response({
            'error': 'No dedicated virtual account found'
        }, status=status.HTTP_404_NOT_FOUND)