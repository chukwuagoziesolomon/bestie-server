"""
Signals for the order app.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order, OrderItem


@receiver(pre_save, sender=Order)
def update_order_totals(sender, instance, **kwargs):
    """
    Update order totals before saving.
    """
    if instance.pk:
        # Calculate total amount from order items
        total = sum(item.price * item.quantity for item in instance.items.all())
        instance.total_amount = total


@receiver(post_save, sender=OrderItem)
def update_order_on_item_change(sender, instance, **kwargs):
    """
    Update the order total when an order item is saved.
    """
    if instance.order:
        instance.order.save()  # This will trigger the pre_save signal to update totals
