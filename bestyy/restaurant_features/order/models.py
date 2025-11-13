"""
Order models for the Bestyy application.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal


class OrderStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    PROCESSING = 'processing', 'Processing'
    SHIPPED = 'shipped', 'Shipped'
    DELIVERED = 'delivered', 'Delivered'
    CANCELLED = 'cancelled', 'Cancelled'
    REFUNDED = 'refunded', 'Refunded'


class Order(models.Model):
    """
    Model representing an order placed by a customer.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='customer_orders'
    )
    vendor = models.ForeignKey(
        'user.VendorProfile',
        on_delete=models.SET_NULL,
        null=True,
        related_name='vendor_orders'
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    shipping_address = models.TextField()
    delivery_address = models.TextField(default='')
    billing_address = models.TextField(blank=True, null=True)
    payment_method = models.CharField(max_length=50)
    payment_status = models.BooleanField(default=False)
    payment_confirmed = models.BooleanField(default=False)
    payment_confirmed_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    delivery_otp = models.CharField(max_length=6, blank=True, null=True)
    pickup_code = models.CharField(max_length=6, blank=True, null=True)
    delivery_distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    courier = models.ForeignKey(
        'user.CourierProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_orders'
    )
    vendor_paid = models.BooleanField(default=False)
    courier_paid = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    preparing_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    out_for_delivery_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)
    delivery_notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['customer']),
            models.Index(fields=['vendor']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Order {self.order_number} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    def _generate_order_number(self):
        """Generate a unique order number."""
        prefix = 'ORD'
        timestamp = timezone.now().strftime('%Y%m%d')
        last_order = Order.objects.order_by('-created_at').first()
        
        if last_order and last_order.order_number:
            try:
                last_num = int(last_order.order_number.split('-')[-1])
                new_num = f"{prefix}-{timestamp}-{last_num + 1:05d}"
            except (IndexError, ValueError):
                new_num = f"{prefix}-{timestamp}-00001"
        else:
            new_num = f"{prefix}-{timestamp}-00001"
            
        return new_num

    @property
    def customer_name(self):
        """Return the full name of the customer."""
        if self.customer:
            return f"{self.customer.first_name} {self.customer.last_name}"
        return ""

    @property
    def vendor_name(self):
        """Return the name of the vendor."""
        return self.vendor.business_name if self.vendor else ""

    @property
    def item_count(self):
        """Return the total number of items in the order."""
        return self.items.count()

    def calculate_distance_and_fee(self):
        """Calculate delivery distance and fee using Google Maps."""
        from bestyy.core_features.user.services.google_maps_service import GoogleMapsService

        if not self.vendor or not self.delivery_address:
            return None

        try:
            # Get vendor location
            vendor_lat = getattr(self.vendor, 'business_latitude', None)
            vendor_lng = getattr(self.vendor, 'business_longitude', None)

            if not vendor_lat or not vendor_lng:
                return None

            vendor_location = f"{vendor_lat},{vendor_lng}"

            # Use Google Maps to calculate distance
            maps_service = GoogleMapsService()
            distance_result = maps_service.get_distance_and_price(
                origin=vendor_location,
                destination=self.delivery_address,
                mode='driving'
            )

            if distance_result:
                # Store distance and fee (you might want to add fields to store these)
                self.delivery_distance_km = distance_result.get('distance_km', 0)
                self.delivery_fee = distance_result.get('delivery_price', 0)
                self.save()
                return distance_result

        except Exception as e:
            # Log error but don't fail the order
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error calculating distance and fee for order {self.id}: {str(e)}")

        return None

    def calculate_payouts(self):
        """Calculate payout amounts for vendor, courier, and platform."""
        from decimal import Decimal

        # Use default commission rate (5%)
        platform_commission_rate = Decimal('0.05')
        courier_fee_rate = Decimal('0.15')  # 15% for courier (configurable)

        subtotal = self.total_amount
        platform_commission = subtotal * platform_commission_rate

        # Calculate courier fee (15% of subtotal)
        courier_amount = subtotal * courier_fee_rate

        # Vendor gets the rest
        vendor_amount = subtotal - platform_commission - courier_amount

        return {
            'vendor_amount': max(vendor_amount, Decimal('0')),
            'courier_amount': courier_amount,
            'platform_commission': platform_commission,
            'subtotal': subtotal
        }

    def trigger_vendor_payout(self):
        """Trigger payout to vendor (placeholder implementation)."""
        if self.vendor_paid:
            return False

        try:
            # Here you would integrate with your payment processor
            # For now, just mark as paid
            self.vendor_paid = True
            self.save()
            return True
        except Exception:
            return False

    def trigger_courier_payout(self):
        """Trigger payout to courier (placeholder implementation)."""
        if self.courier_paid:
            return False

        try:
            # Here you would integrate with your payment processor
            # For now, just mark as paid
            self.courier_paid = True
            self.save()
            return True
        except Exception:
            return False

    def generate_pickup_code(self):
        """Generate a unique pickup code for the vendor."""
        import random
        import string

        if self.pickup_code:
            return self.pickup_code

        # Generate 6-character alphanumeric code
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self.pickup_code = code
        self.save()
        return code

    def generate_delivery_otp(self):
        """Generate a unique delivery OTP for the customer."""
        import random

        if self.delivery_otp:
            return self.delivery_otp

        # Generate 6-digit numeric OTP
        otp = ''.join(random.choices('0123456789', k=6))
        self.delivery_otp = otp
        self.save()
        return otp

    def verify_pickup_code(self, code):
        """Verify the pickup code entered by vendor."""
        return self.pickup_code and self.pickup_code == code

    def verify_delivery_otp(self, otp):
        """Verify the delivery OTP entered by courier."""
        return self.delivery_otp and self.delivery_otp == otp

    def mark_as_delivered(self):
        """Mark the order as delivered."""
        from django.utils import timezone

        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save()


class OrderItem(models.Model):
    """
    Model representing an item within an order.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'product.Product',
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return f"{self.quantity}x {self.product.name if self.product else 'Product'}"

    @property
    def total_price(self):
        """Calculate the total price for this order item."""
        return self.quantity * self.price
