import logging
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import VendorProfile, UserProfile, CourierProfile, User
from bestyy.restaurant_features.order.models import Order
from .utils.websocket_notifications import send_admin_notification
import json
from django.db import models


logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


def send_activity_update(activity_data):
    """Send activity update to WebSocket group"""
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            'admin_activity',
            {
                'type': 'activity_update',
                'activity': activity_data
            }
        )


@receiver(post_save, sender=Order)
def order_created_handler(sender, instance, created, **kwargs):
    """Send real-time update when new order is created"""
    if created:
        # Handle both authenticated and anonymous users
        user_name = "Anonymous User"
        user_email = "N/A"
        user_id = None

        if instance.customer and instance.customer.is_authenticated:
            user_name = instance.customer.get_full_name() or instance.customer.username
            user_email = instance.customer.email
            user_id = instance.customer.id

        activity_data = {
            'id': f"order_{instance.id}",
            'type': 'order',
            'title': f"New Order #{instance.id}",
            'description': f"{user_name} ordered from {instance.vendor.business_name}",
            'amount': float(instance.total_amount),
            'status': instance.status,
            'user': {
                'id': user_id,
                'name': user_name,
                'email': user_email
            },
            'vendor': {
                'id': instance.vendor.id,
                'name': instance.vendor.business_name
            },
            'timestamp': instance.created_at.isoformat(),
            'icon': 'shopping-cart',
            'color': get_status_color(instance.status)
        }
        
        send_activity_update(activity_data)
        print(f"🔥 REAL-TIME UPDATE: New order #{instance.id} sent to admin dashboard")
        
        # Vendor analytics removed - using Order model for tracking

@receiver(pre_save, sender=Order)
def order_status_change_handler(sender, instance, **kwargs):
    """Send real-time update when order status changes"""
    if instance.pk:  # Only for existing orders
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                # Order status changed
                if instance.status == 'accepted':
                    # Vendor accepted the order
                    activity_data = {
                        'id': f"order_accepted_{instance.id}",
                        'type': 'order_accepted',
                        'title': f"Vendor Accepted Order #{instance.id}",
                        'description': f"Vendor '{instance.vendor.business_name}' accepted order #{instance.id}",
                        'amount': float(instance.total_price),
                        'status': instance.status,
                        'vendor': {
                            'id': instance.vendor.id,
                            'name': instance.vendor.business_name
                        },
                        'timestamp': timezone.now().isoformat(),
                        'icon': 'check-circle',
                        'color': '#10B981'
                    }
                    send_activity_update(activity_data)
                    print(f"🔥 REAL-TIME UPDATE: Order #{instance.id} accepted by vendor sent to admin dashboard")
                
                elif instance.status == 'completed':
                    # Order completed
                    activity_data = {
                        'id': f"order_completed_{instance.id}",
                        'type': 'order_completed',
                        'title': f"Order #{instance.id} Completed",
                        'description': f"Order #{instance.id} has been completed",
                        'amount': float(instance.total_price),
                        'status': instance.status,
                        'vendor': {
                            'id': instance.vendor.id,
                            'name': instance.vendor.business_name
                        },
                        'timestamp': timezone.now().isoformat(),
                        'icon': 'check-circle',
                        'color': '#059669'
                    }
                    send_activity_update(activity_data)
                    print(f"🔥 REAL-TIME UPDATE: Order #{instance.id} completed sent to admin dashboard")
        except Order.DoesNotExist:
            pass  # New order, skip

@receiver(pre_save, sender=Order)
def courier_order_completion_handler(sender, instance, **kwargs):
    """Send real-time update when courier completes an order"""
    if instance.pk and instance.courier:  # Only for existing orders with courier
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            if (old_instance.status != instance.status and 
                instance.status == 'delivered' and 
                old_instance.courier != instance.courier):
                # Courier completed the order
                activity_data = {
                    'id': f"courier_completed_{instance.id}",
                    'type': 'courier_completed',
                    'title': f"Courier Completed Order #{instance.id}",
                    'description': f"Courier '{instance.courier.user.get_full_name() or instance.courier.user.email}' completed order #{instance.id}",
                    'amount': float(instance.total_price),
                    'status': instance.status,
                    'courier': {
                        'id': instance.courier.id,
                        'name': instance.courier.user.get_full_name() or instance.courier.user.email
                    },
                    'vendor': {
                        'id': instance.vendor.id,
                        'name': instance.vendor.business_name
                    },
                    'timestamp': timezone.now().isoformat(),
                    'icon': 'truck',
                    'color': '#059669'
                }
                send_activity_update(activity_data)
                print(f"🔥 REAL-TIME UPDATE: Courier completed order #{instance.id} sent to admin dashboard")
        except Order.DoesNotExist:
            pass  # New order, skip


# Payment signals removed - using Order model for payment tracking


@receiver(post_save, sender=User)
def user_created_handler(sender, instance, created, **kwargs):
    """Send real-time update when new user is created"""
    if created:
        # Determine user type
        user_type = 'user'
        if hasattr(instance, 'vendor_profile'):
            user_type = 'vendor'
        elif hasattr(instance, 'courier_profile'):
            user_type = 'courier'
        
        activity_data = {
            'id': f"user_{instance.id}",
            'type': 'registration',
            'title': f"New {user_type.title()} Registration",
            'description': f"{instance.get_full_name() or instance.username} joined as {user_type}",
            'user': {
                'id': instance.id,
                'name': instance.get_full_name() or instance.username,
                'email': instance.email
            },
            'user_type': user_type,
            'timestamp': instance.date_joined.isoformat(),
            'icon': 'user-plus',
            'color': '#10B981'  # Green for new registrations
        }
        
        # Send to admin activity feed
        send_activity_update(activity_data)
        
        # Also send as a WebSocket notification
        try:
            send_admin_notification(
                notification_type='user.registered',
                data={
                    'user_id': str(instance.id),
                    'email': instance.email,
                    'username': instance.username,
                    'full_name': instance.get_full_name() or 'New User',
                    'is_staff': instance.is_staff,
                    'timestamp': instance.date_joined.isoformat()
                }
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error sending user registration notification: {str(e)}")
        print(f" REAL-TIME UPDATE: New user {instance.username} sent to admin dashboard")


@receiver(post_save, sender=VendorProfile)
def vendor_created_handler(sender, instance, created, **kwargs):
    """Send real-time update when new vendor is created"""
    if created:
        activity_data = {
            'id': f"vendor_{instance.id}",
            'type': 'vendor_application',
            'title': "New Vendor Application",
            'description': f"{instance.business_name} applied to become a vendor",
            'user': {
                'id': instance.user.id,
                'name': instance.user.get_full_name() or instance.user.username,
                'email': instance.user.email
            },
            'business_name': instance.business_name,
            'business_category': instance.business_category,
            'timestamp': instance.user.date_joined.isoformat(),
            'icon': 'store',
            'color': '#8B5CF6'  # Purple for vendor applications
        }
        
        send_activity_update(activity_data)
        print(f" REAL-TIME UPDATE: New vendor {instance.business_name} sent to admin dashboard")


def get_status_color(status):
    """Get color based on order status"""
    status_colors = {
        'pending': '#F59E0B',           # Yellow
        'payment_confirmed': '#10B981', # Green
        'processing': '#3B82F6',        # Blue
        'ready': '#8B5CF6',            # Purple
        'out_for_delivery': '#F97316',  # Orange
        'delivered': '#10B981',         # Green
        'completed': '#059669',         # Dark Green
        'cancelled': '#EF4444',         # Red
        'rejected': '#DC2626'           # Dark Red
    }
    return status_colors.get(status, '#6B7280')  # Default gray


def get_payment_status_color(status):
    """Get color based on payment status"""
    if status == 'completed':
        return 'success'
    elif status == 'pending':
        return 'warning'
    elif status == 'failed':
        return 'danger'
    return 'info'


@receiver(pre_save, sender=CourierProfile)
def set_courier_verification_status(sender, instance, **kwargs):
    """
    Set the verification status to 'pending' when a new courier profile is created.
    This ensures all new couriers must be verified by an admin before they can access
    courier-specific features.
    """
    if instance._state.adding:  # Only for new instances
        instance.verification_status = 'pending'

@receiver(post_save, sender=CourierProfile)
def courier_created_handler(sender, instance, created, **kwargs):
    """Send real-time update when new courier is created"""
    if created:
        activity_data = {
            'id': f"courier_{instance.id}",
            'type': 'courier_application',
            'title': "New Courier Application",
            'description': f"{instance.user.get_full_name() or instance.user.email} applied to become a courier",
            'user': {
                'id': instance.user.id,
                'name': instance.user.get_full_name() or instance.user.username,
                'email': instance.user.email
            },
            'timestamp': instance.created_at.isoformat(),
            'icon': 'truck',
            'color': '#3B82F6'  # Blue for courier applications
        }
        
        send_activity_update(activity_data)
        print(f"🔥 REAL-TIME UPDATE: New courier {instance.user.get_full_name() or instance.user.email} sent to admin dashboard")

@receiver(post_save, sender=User)
def create_all_user_profiles(sender, instance, created, **kwargs):
    """
    Ensure ALL relevant profiles exist for users with multiple roles.
    Only creates profiles for roles that are EXPLICITLY assigned via UserRole.
    Does NOT auto-create UserProfile unless user explicitly has 'user' role.
    """
    # Don't run in raw saves or migrations
    if kwargs.get('raw') or kwargs.get('update_fields') == ['last_login']:
        return

    # Get explicit roles from UserRole table (not the role field which defaults to 'user')
    if hasattr(instance, 'get_roles'):
        roles = instance.get_roles()
    else:
        # If get_roles doesn't exist or returns empty, check role field but don't default
        roles = []
        if hasattr(instance, 'role') and instance.role:
            roles = [instance.role]

    # Only create profiles for explicitly assigned roles
    from .models import UserProfile, VendorProfile, CourierProfile
    if 'user' in roles and not hasattr(instance, 'profile'):
        UserProfile.objects.get_or_create(user=instance)
    if 'vendor' in roles and not hasattr(instance, 'vendor_profile'):
        VendorProfile.objects.get_or_create(user=instance, defaults={'phone': getattr(instance, 'phone', '')})
    if 'courier' in roles and not hasattr(instance, 'courier_profile'):
        CourierProfile.objects.get_or_create(user=instance, defaults={'phone': getattr(instance, 'phone', '')})

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save the appropriate profile when the user is saved.
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()
    elif hasattr(instance, 'vendor_profile'):
        instance.vendor_profile.save()
    elif hasattr(instance, 'courier_profile'):
        instance.courier_profile.save()
        logger = logging.getLogger(__name__)
        logger.info(f"New courier profile created for user {instance.user_id}. Verification status set to 'pending'.")

# Vendor popularity tracking removed
