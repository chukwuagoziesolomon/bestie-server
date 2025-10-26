"""
Utility functions for sending WebSocket notifications.
"""
import json
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from bestyy.payment_analytics.analytics.models import Activity

logger = logging.getLogger(__name__)

def send_admin_notification(notification_type, data):
    """
    Send a notification to all connected admin users.
    
    Args:
        notification_type (str): Type of notification (e.g., 'vendor.registered')
        data (dict): Notification data
    """
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'admin_activity',
            {
                'type': notification_type,
                'data': {
                    **data,
                    'timestamp': timezone.now().isoformat()
                }
            }
        )
    except Exception as e:
        logger.error(f"Error sending admin notification: {str(e)}")


def record_activity(title, description='', *, icon='', color='', amount=None, actor=None, target_type='', target_id='', metadata=None):
    """Persist an activity and broadcast to admin dashboard."""
    try:
        activity = Activity.objects.create(
            title=title,
            description=description,
            icon=icon,
            color=color,
            amount=amount,
            actor=actor,
            target_type=target_type,
            target_id=str(target_id) if target_id else '',
            metadata=metadata or {},
        )

        # Broadcast via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'admin_activity',
            {
                'type': 'activity_update',
                'data': {
                    'id': activity.id,
                    'title': activity.title,
                    'description': activity.description,
                    'icon': activity.icon,
                    'color': activity.color,
                    'amount': float(activity.amount) if activity.amount is not None else None,
                    'timestamp': activity.created_at.isoformat(),
                }
            }
        )
        return activity
    except Exception as e:
        logger.error(f"Error recording activity: {str(e)}")
        return None

def send_vendor_notification(vendor_id, notification_type, data):
    """
    Send a notification to a specific vendor.
    
    Args:
        vendor_id (int): ID of the vendor to notify
        notification_type (str): Type of notification (e.g., 'status.updated')
        data (dict): Notification data
    """
    try:
        channel_layer = get_channel_layer()
        group_name = f'vendor_{vendor_id}'
        
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': notification_type,
                'data': {
                    **data,
                    'timestamp': timezone.now().isoformat()
                }
            }
        )
    except Exception as e:
        logger.error(f"Error sending vendor notification: {str(e)}")

def notify_vendor_registered(vendor):
    """Notify admins when a new vendor registers"""
    send_admin_notification(
        'vendor.registered',
        {
            'vendor_id': vendor.id,
            'business_name': vendor.business_name,
            'email': vendor.user.email,
            'timestamp': vendor.created_at.isoformat(),
            'message': f'New vendor registered: {vendor.business_name}'
        }
    )

def notify_vendor_approved(vendor, admin_user):
    """Notify vendor and admins when a vendor is approved"""
    # Notify admins
    send_admin_notification(
        'vendor.approved',
        {
            'vendor_id': vendor.id,
            'business_name': vendor.business_name,
            'approved_by': admin_user.get_full_name() or admin_user.email,
            'timestamp': vendor.verification_date.isoformat(),
            'message': f'Vendor approved: {vendor.business_name}'
        }
    )
    
    # Notify vendor
    send_vendor_notification(
        vendor.id,
        'verification.approved',
        {
            'status': 'approved',
            'message': 'Your vendor account has been approved!',
            'verification_date': vendor.verification_date.isoformat(),
            'next_steps': 'You can now access all vendor features.'
        }
    )

def notify_vendor_rejected(vendor, admin_user, reason):
    """Notify vendor and admins when a vendor is rejected"""
    # Notify admins
    send_admin_notification(
        'vendor.rejected',
        {
            'vendor_id': vendor.id,
            'business_name': vendor.business_name,
            'rejected_by': admin_user.get_full_name() or admin_user.email,
            'timestamp': vendor.verification_date.isoformat(),
            'reason': reason,
            'message': f'Vendor rejected: {vendor.business_name}'
        }
    )
    
    # Notify vendor
    send_vendor_notification(
        vendor.id,
        'verification.rejected',
        {
            'status': 'rejected',
            'message': 'Your vendor account has been rejected.',
            'reason': reason,
            'verification_date': vendor.verification_date.isoformat(),
            'next_steps': 'Please update your information and reapply.'
        }
    )

def send_courier_notification(courier_id, notification_type, data):
    """
    Send a notification to a specific courier.
    
    Args:
        courier_id (int): ID of the courier to notify
        notification_type (str): Type of notification (e.g., 'status.updated')
        data (dict): Notification data
    """
    try:
        channel_layer = get_channel_layer()
        group_name = f'courier_{courier_id}'
        
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': notification_type,
                'data': {
                    **data,
                    'timestamp': timezone.now().isoformat()
                }
            }
        )
    except Exception as e:
        logger.error(f"Error sending courier notification: {str(e)}")

def notify_courier_registered(courier):
    """Notify admins when a new courier registers"""
    send_admin_notification(
        'courier.registered',
        {
            'courier_id': courier.id,
            'full_name': courier.user.get_full_name() or courier.user.email,
            'email': courier.user.email,
            'timestamp': courier.created_at.isoformat(),
            'message': f'New courier registered: {courier.user.get_full_name() or courier.user.email}'
        }
    )

def notify_courier_approved(courier, admin_user):
    """Notify courier and admins when a courier is approved"""
    # Notify admins
    send_admin_notification(
        'courier.approved',
        {
            'courier_id': courier.id,
            'full_name': courier.user.get_full_name() or courier.user.email,
            'approved_by': admin_user.get_full_name() or admin_user.email,
            'timestamp': courier.verification_date.isoformat(),
            'message': f'Courier approved: {courier.user.get_full_name() or courier.user.email}'
        }
    )
    
    # Notify courier
    send_courier_notification(
        courier.id,
        'verification.approved',
        {
            'status': 'approved',
            'message': 'Your courier account has been approved!',
            'verification_date': courier.verification_date.isoformat(),
            'next_steps': 'You can now start accepting delivery requests.'
        }
    )

def notify_courier_rejected(courier, admin_user, reason):
    """Notify courier and admins when a courier is rejected"""
    # Notify admins
    send_admin_notification(
        'courier.rejected',
        {
            'courier_id': courier.id,
            'full_name': courier.user.get_full_name() or courier.user.email,
            'rejected_by': admin_user.get_full_name() or admin_user.email,
            'timestamp': courier.verification_date.isoformat(),
            'reason': reason,
            'message': f'Courier rejected: {courier.user.get_full_name() or courier.user.email}'
        }
    )
    
    # Notify courier
    send_courier_notification(
        courier.id,
        'verification.rejected',
        {
            'status': 'rejected',
            'message': 'Your courier account has been rejected.',
            'reason': reason,
            'verification_date': courier.verification_date.isoformat(),
            'next_steps': 'Please update your information and reapply.'
        }
    )

def notify_vendor_suspended(vendor, admin_user, reason, duration_days=None):
    """Notify vendor and admins when a vendor is suspended"""
    # Notify admins
    send_admin_notification(
        'vendor.suspended',
        {
            'vendor_id': vendor.id,
            'business_name': vendor.business_name,
            'suspended_by': admin_user.get_full_name() or admin_user.email,
            'timestamp': vendor.suspension_date.isoformat(),
            'reason': reason,
            'duration_days': duration_days,
            'message': f'Vendor suspended: {vendor.business_name}'
        }
    )
    
    # Notify vendor
    send_vendor_notification(
        vendor.id,
        'account.suspended',
        {
            'status': 'suspended',
            'reason': reason,
            'duration_days': duration_days,
            'suspension_date': vendor.suspension_date.isoformat(),
            'message': 'Your vendor account has been suspended.',
            'contact_support': 'Please contact support for more information.'
        }
    )

def notify_vendor_activated(vendor, admin_user, reason):
    """Notify vendor and admins when a vendor is activated"""
    # Notify admins
    send_admin_notification(
        'vendor.activated',
        {
            'vendor_id': vendor.id,
            'business_name': vendor.business_name,
            'activated_by': admin_user.get_full_name() or admin_user.email,
            'timestamp': vendor.activation_date.isoformat(),
            'reason': reason,
            'message': f'Vendor activated: {vendor.business_name}'
        }
    )
    
    # Notify vendor
    send_vendor_notification(
        vendor.id,
        'account.activated',
        {
            'status': 'active',
            'reason': reason,
            'activation_date': vendor.activation_date.isoformat(),
            'message': 'Your vendor account has been reactivated!',
            'next_steps': 'You can now continue operating your business.'
        }
    )

def notify_courier_suspended(courier, admin_user, reason, duration_days=None):
    """Notify courier and admins when a courier is suspended"""
    # Notify admins
    send_admin_notification(
        'courier.suspended',
        {
            'courier_id': courier.id,
            'full_name': courier.user.get_full_name() or courier.user.email,
            'suspended_by': admin_user.get_full_name() or admin_user.email,
            'timestamp': courier.suspension_date.isoformat(),
            'reason': reason,
            'duration_days': duration_days,
            'message': f'Courier suspended: {courier.user.get_full_name() or courier.user.email}'
        }
    )
    
    # Notify courier
    send_courier_notification(
        courier.id,
        'account.suspended',
        {
            'status': 'suspended',
            'reason': reason,
            'duration_days': duration_days,
            'suspension_date': courier.suspension_date.isoformat(),
            'message': 'Your courier account has been suspended.',
            'contact_support': 'Please contact support for more information.'
        }
    )

def notify_courier_activated(courier, admin_user, reason):
    """Notify courier and admins when a courier is activated"""
    # Notify admins
    send_admin_notification(
        'courier.activated',
        {
            'courier_id': courier.id,
            'full_name': courier.user.get_full_name() or courier.user.email,
            'activated_by': admin_user.get_full_name() or admin_user.email,
            'timestamp': courier.activation_date.isoformat(),
            'reason': reason,
            'message': f'Courier activated: {courier.user.get_full_name() or courier.user.email}'
        }
    )
    
    # Notify courier
    send_courier_notification(
        courier.id,
        'account.activated',
        {
            'status': 'active',
            'reason': reason,
            'activation_date': courier.activation_date.isoformat(),
            'message': 'Your courier account has been reactivated!',
            'next_steps': 'You can now start accepting delivery requests again.'
        }
    )
