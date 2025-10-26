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
        'vendor.Vendor',
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
    billing_address = models.TextField(blank=True, null=True)
    payment_method = models.CharField(max_length=50)
    payment_status = models.BooleanField(default=False)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
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
        return f"Order {self.order_number} - {self.get_status_display()}"

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
