"""
Signals for the order app.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Order, OrderItem
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=OrderItem)
def update_order_on_item_change(sender, instance, **kwargs):
    """
    Update the order total when an order item is saved.
    """
    if instance.order:
        instance.order.save()  # This will trigger the pre_save signal to update totals


@receiver(pre_save, sender=Order)
def handle_order_updates(sender, instance, **kwargs):
    """
    Handle order updates including totals and stock management.
    Uses pre_save to detect changes before they're committed.
    
    - Update order totals from order items
    - When order is confirmed (payment_confirmed=True): Create stock reservations
    - When order is delivered: Fulfill stock reservations (deduct stock) and mark revenue as paid
    - When order is cancelled: Release stock reservations
    """
    from bestyy.core_features.user.cart_utils import (
        create_stock_reservations_for_order,
        fulfill_stock_reservations,
        release_stock_reservations
    )
    
    # Update order totals if order exists
    if instance.pk:
        try:
            # Calculate total amount from order items
            total = sum(item.price * item.quantity for item in instance.items.all())
            instance.total_amount = total
        except:
            pass  # In case items aren't loaded yet
    
    # Skip stock management if order is being created (no pk yet)
    if not instance.pk:
        return
    
    # Get the previous state from database to detect changes
    try:
        old_order = Order.objects.get(pk=instance.pk)
    except Order.DoesNotExist:
        return
    
    # Handle payment confirmation - create stock reservations
    if instance.payment_confirmed and not old_order.payment_confirmed:
        try:
            reservations = create_stock_reservations_for_order(instance)
            logger.info(f"Created {len(reservations)} stock reservations for order {instance.order_number}")
        except ValueError as e:
            logger.error(f"Failed to create stock reservations for order {instance.order_number}: {str(e)}")
            # Note: This happens before save, so you could raise an exception to prevent save if needed
    
    # Handle order delivery - fulfill reservations and mark revenue as paid
    if instance.status == 'delivered' and old_order.status != 'delivered':
        try:
            # Fulfill stock reservations (deduct stock)
            result = fulfill_stock_reservations(instance)
            logger.info(f"Fulfilled {result['fulfilled']} stock reservations for order {instance.order_number}")
            
            if result['failed'] > 0:
                logger.warning(f"Failed to fulfill {result['failed']} items for order {instance.order_number}: {result['failed_items']}")
            
            # Mark vendor and courier as paid (revenue tracking)
            if not instance.vendor_paid:
                instance.vendor_paid = True
                logger.info(f"Marked vendor as paid for order {instance.order_number}")
            
            if instance.courier and not instance.courier_paid:
                instance.courier_paid = True
                logger.info(f"Marked courier as paid for order {instance.order_number}")
            
            # Update delivered_at timestamp if not set
            if not instance.delivered_at:
                instance.delivered_at = timezone.now()
            
        except Exception as e:
            logger.error(f"Error fulfilling order {instance.order_number}: {str(e)}")
    
    # Handle order cancellation - release stock reservations
    cancelled_statuses = ['cancelled', 'rejected', 'failed']
    if instance.status in cancelled_statuses and old_order.status not in cancelled_statuses:
        try:
            released = release_stock_reservations(instance)
            logger.info(f"Released {released} stock reservations for cancelled order {instance.order_number}")
        except Exception as e:
            logger.error(f"Error releasing stock reservations for order {instance.order_number}: {str(e)}")
