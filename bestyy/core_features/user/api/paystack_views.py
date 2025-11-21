from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404
from bestyy.core_features.user.models import User
from bestyy.core_features.user.services.paystack_service import PaystackService
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)












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
        'vendor_commission_percentage': float(settings['vendor_commission_percentage']),
        'base_delivery_fee': float(settings['base_delivery_fee']),
        'delivery_fee_per_km': float(settings['delivery_fee_per_km']),
        'rider_base_fee': float(settings['rider_base_fee']),
        'rider_fee_per_km': float(settings['rider_fee_per_km']),
        'service_fee_percentage': float(settings['service_fee_percentage'])
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@permission_required('is_staff', raise_exception=True)
def update_system_settings(request):
    """
    Update system settings (admin only)
    """
    from bestyy.core_features.user.models import SystemSettings

    # Update individual settings using the set_setting method
    updated_settings = {}
    if 'vendor_commission_percentage' in request.data:
        SystemSettings.set_setting('vendor_commission_percentage', request.data['vendor_commission_percentage'], user=request.user)
        updated_settings['vendor_commission_percentage'] = request.data['vendor_commission_percentage']
    if 'base_delivery_fee' in request.data:
        SystemSettings.set_setting('base_delivery_fee', request.data['base_delivery_fee'], user=request.user)
        updated_settings['base_delivery_fee'] = request.data['base_delivery_fee']
    if 'delivery_fee_per_km' in request.data:
        SystemSettings.set_setting('delivery_fee_per_km', request.data['delivery_fee_per_km'], user=request.user)
        updated_settings['delivery_fee_per_km'] = request.data['delivery_fee_per_km']
    if 'rider_base_fee' in request.data:
        SystemSettings.set_setting('rider_base_fee', request.data['rider_base_fee'], user=request.user)
        updated_settings['rider_base_fee'] = request.data['rider_base_fee']
    if 'rider_fee_per_km' in request.data:
        SystemSettings.set_setting('rider_fee_per_km', request.data['rider_fee_per_km'], user=request.user)
        updated_settings['rider_fee_per_km'] = request.data['rider_fee_per_km']
    if 'service_fee_percentage' in request.data:
        SystemSettings.set_setting('service_fee_percentage', request.data['service_fee_percentage'], user=request.user)
        updated_settings['service_fee_percentage'] = request.data['service_fee_percentage']

    # Get updated settings for response
    settings = SystemSettings.get_active_settings()

    return Response({
        'success': True,
        'message': 'System settings updated successfully',
        'settings': {
            'vendor_commission_percentage': float(settings.get('vendor_commission_percentage', 0)),
            'base_delivery_fee': float(settings.get('base_delivery_fee', 0)),
            'delivery_fee_per_km': float(settings.get('delivery_fee_per_km', 0)),
            'rider_base_fee': float(settings.get('rider_base_fee', 0)),
            'rider_fee_per_km': float(settings.get('rider_fee_per_km', 0)),
            'service_fee_percentage': float(settings.get('service_fee_percentage', 0))
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




