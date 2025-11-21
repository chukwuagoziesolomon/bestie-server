"""
Service to notify vendors when they receive new orders after payment confirmation.
This service sends WhatsApp notifications to vendors when orders are confirmed and paid.
"""
from django.utils import timezone
from bestyy.restaurant_features.order.models import Order, OrderItem
from bestyy.core_features.user.models import VendorProfile
import logging

logger = logging.getLogger(__name__)


class VendorOrderNotificationService:
    """
    Service to handle vendor notifications for new confirmed orders.
    """

    @staticmethod
    def notify_vendor_new_order(order: Order):
        """
        Notify vendor about a new confirmed order.

        Args:
            order: The Order instance that has been confirmed and paid
        """
        try:
            if not order.vendor or not order.vendor.user:
                logger.warning(f"Order {order.id} has no vendor assigned")
                return False

            vendor = order.vendor
            user = vendor.user

            # Build notification message
            message = VendorOrderNotificationService._build_new_order_message(order)

            # Send WhatsApp notification
            success = VendorOrderNotificationService._send_whatsapp_notification(user, message)

            if success:
                logger.info(f"New order notification sent to vendor {vendor.id} for order {order.id}")
                return True
            else:
                logger.error(f"Failed to send new order notification to vendor {vendor.id}")
                return False

        except Exception as e:
            logger.error(f"Error notifying vendor about new order {order.id}: {str(e)}")
            return False

    @staticmethod
    def _build_new_order_message(order: Order) -> str:
        """
        Build the new order notification message for vendor.
        """
        customer_name = order.customer.get_full_name() if order.customer else "Customer"
        delivery_address = order.delivery_address or order.shipping_address or "Pickup"

        # Get order items summary
        items_summary = VendorOrderNotificationService._get_order_items_summary(order)

        message = f"""🍽️ *NEW ORDER RECEIVED* - Bestyy

📦 Order #*{order.order_number}*
👤 Customer: {customer_name}
📍 Delivery: {delivery_address}

*Order Items:*
{items_summary}

💰 *Payment Details:*
Total: ₦{order.total_amount:,.0f}
Status: ✅ Paid & Confirmed
Pickup Code: *{order.pickup_code or 'Pending'}*

━━━━━━━━━━━━━━━━━━━
⚡ *PLEASE RESPOND:*

✅ Reply *ACCEPT* to start preparing
❌ Reply *REJECT* if you can't fulfill

Once accepted:
1️⃣ Prepare the order
2️⃣ Reply *READY* when food is ready
3️⃣ Courier will be notified automatically
4️⃣ Give pickup code to courier

⏰ Expected prep time: 30-45 minutes

Reply 'ACCEPT' or 'REJECT' now."""

        return message

    @staticmethod
    def _get_order_items_summary(order: Order) -> str:
        """
        Get a summary of order items for the notification.
        """
        items_text = ""
        order_items = order.items.all()[:5]  # Limit to first 5 items
        for item in order_items:
            quantity = item.quantity
            item_name = item.product.name if item.product else "Menu Item"
            price = float(item.price)
            items_text += f"• {quantity}x {item_name} - ₦{price:.2f}\n"

        # Add ellipsis if there are more items
        total_items_count = order.items.count()
        if total_items_count > 5:
            items_text += f"... and {total_items_count - 5} more items"

        return items_text.strip()

    @staticmethod
    def _send_whatsapp_notification(user, message: str) -> bool:
        """
        Send WhatsApp notification to vendor.

        Args:
            user: The User instance (vendor)
            message: The message to send

        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Import here to avoid circular imports
            from bestyy.communication.whatsapp.services.meta_whatsapp_service import MetaWhatsAppService

            if not user.phone:
                logger.warning(f"Vendor {user.id} has no phone number")
                return False

            meta_service = MetaWhatsAppService()
            result = meta_service.send_message(
                to=user.phone,
                message=message
            )

            return result.get('success', False)

        except Exception as e:
            logger.error(f"Error sending WhatsApp notification to vendor {user.id}: {str(e)}")
            return False

    @staticmethod
    def notify_multiple_vendors(orders):
        """
        Notify multiple vendors about their new orders.

        Args:
            orders: QuerySet or list of Order instances
        """
        notified_count = 0
        failed_count = 0

        for order in orders:
            if VendorOrderNotificationService.notify_vendor_new_order(order):
                notified_count += 1
            else:
                failed_count += 1

        logger.info(f"Vendor notifications completed: {notified_count} sent, {failed_count} failed")
        return notified_count, failed_count