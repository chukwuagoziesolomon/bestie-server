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
    
    # Pickup and delivery codes with verification tracking
    delivery_otp = models.CharField(max_length=20, blank=True, null=True, help_text="Format: DL-XXXXXX")
    delivery_otp_verified = models.BooleanField(default=False, help_text="True when customer confirms delivery")
    pickup_code = models.CharField(max_length=20, blank=True, null=True, help_text="Format: PK-XXXXXX")
    pickup_code_verified = models.BooleanField(default=False, help_text="True when courier picks up order")
    
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
    vendor_paid_at = models.DateTimeField(null=True, blank=True)
    vendor_transfer_code = models.CharField(max_length=50, blank=True, null=True, help_text='Paystack transfer code for vendor payment')
    vendor_transfer_reference = models.CharField(max_length=50, blank=True, null=True, unique=True, help_text='Unique reference for vendor transfer')
    vendor_transfer_status = models.CharField(max_length=20, default='pending', choices=[('pending', 'Pending'), ('processing', 'Processing'), ('success', 'Success'), ('failed', 'Failed'), ('reversed', 'Reversed')])
    
    courier_paid = models.BooleanField(default=False)
    courier_paid_at = models.DateTimeField(null=True, blank=True)
    courier_transfer_code = models.CharField(max_length=50, blank=True, null=True, help_text='Paystack transfer code for courier payment')
    courier_transfer_reference = models.CharField(max_length=50, blank=True, null=True, unique=True, help_text='Unique reference for courier transfer')
    courier_transfer_status = models.CharField(max_length=20, default='pending', choices=[('pending', 'Pending'), ('processing', 'Processing'), ('success', 'Success'), ('failed', 'Failed'), ('reversed', 'Reversed')])
    
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
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Starting distance calculation for order {self.id}")

        if not self.vendor:
            logger.error(f"Order {self.id}: No vendor associated")
            return None

        if not self.delivery_address:
            logger.error(f"Order {self.id}: No delivery address")
            return None

        try:
            # Get vendor location - use business address since lat/lng fields don't exist
            vendor_address = getattr(self.vendor, 'business_address', None)
            logger.info(f"Order {self.id}: Vendor address = '{vendor_address}'")
            logger.info(f"Order {self.id}: Delivery address = '{self.delivery_address}'")

            if not vendor_address:
                logger.warning(f"Order {self.id}: Vendor has no business_address - using default delivery fee")
                # Apply default delivery fee without distance calculation
                self.delivery_fee = Decimal('700.00')  # Default delivery fee
                self.save()
                return {'delivery_price': self.delivery_fee, 'distance_km': 0, 'mode': 'default'}

            # Use Google Maps to calculate distance using addresses
            maps_service = GoogleMapsService()
            logger.info(f"Order {self.id}: Calling Google Maps service")

            distance_result = maps_service.get_distance_and_price(
                origin=vendor_address,
                destination=self.delivery_address,
                mode='driving'
            )

            logger.info(f"Order {self.id}: Distance result = {distance_result}")

            if distance_result:
                # Store distance and fee
                self.delivery_distance_km = distance_result.get('distance_km', 0)
                self.delivery_fee = distance_result.get('delivery_price', 0)
                self.save()
                logger.info(f"Order {self.id}: Saved distance_km={self.delivery_distance_km}, fee={self.delivery_fee}")
                return distance_result
            else:
                logger.error(f"Order {self.id}: Google Maps returned None")

        except Exception as e:
            # Log error but don't fail the order
            logger.error(f"Error calculating distance and fee for order {self.id}: {str(e)}", exc_info=True)

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
        """Generate a unique pickup code for the vendor with transfer reference.
        
        Format: PK-XXXXXX (e.g., PK-A1B2C3)
        The 'PK-' prefix helps distinguish it from WhatsApp verification codes.
        """
        import random
        import string
        import uuid

        if self.pickup_code:
            return self.pickup_code

        # Generate 6-character alphanumeric code with PK- prefix
        code_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        code = f"PK-{code_part}"  # e.g., PK-A1B2C3
        self.pickup_code = code
        
        # Generate unique transfer reference for vendor payment (UUID format)
        if not self.vendor_transfer_reference:
            self.vendor_transfer_reference = f"vendor_{self.order_number}_{uuid.uuid4().hex[:16]}"
        
        self.save()
        return code

    def generate_delivery_otp(self):
        """Generate a unique delivery OTP for the customer with transfer reference.
        
        Format: DL-XXXXXX (e.g., DL-123456)
        The 'DL-' prefix helps distinguish it from WhatsApp verification codes.
        """
        import random
        import uuid

        if self.delivery_otp:
            return self.delivery_otp

        # Generate 6-digit numeric OTP with DL- prefix
        otp_part = ''.join(random.choices('0123456789', k=6))
        otp = f"DL-{otp_part}"  # e.g., DL-123456
        self.delivery_otp = otp
        
        # Generate unique transfer reference for courier payment (UUID format)
        if not self.courier_transfer_reference:
            self.courier_transfer_reference = f"courier_{self.order_number}_{uuid.uuid4().hex[:16]}"
        
        self.save()
        return otp

    def verify_pickup_code(self, code):
        """Verify the pickup code entered by vendor.
        
        Accepts code with or without PK- prefix for flexibility.
        """
        if not self.pickup_code:
            return False
        
        # Normalize input - add prefix if not present
        if not code.upper().startswith('PK-'):
            code = f"PK-{code.upper()}"
        
        return self.pickup_code.upper() == code.upper()

    def verify_delivery_otp(self, otp):
        """Verify the delivery OTP entered by customer/courier.
        
        Accepts OTP with or without DL- prefix for flexibility.
        """
        if not self.delivery_otp:
            return False
        
        # Normalize input - add prefix if not present
        if not otp.upper().startswith('DL-'):
            otp = f"DL-{otp.upper()}"
        
        return self.delivery_otp.upper() == otp.upper()

    def mark_as_delivered(self):
        """Mark the order as delivered."""
        from django.utils import timezone

        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save()
    
    def trigger_vendor_payout(self):
        """
        Trigger automatic payment to vendor when pickup code is verified.
        Returns True if payout initiated successfully, False otherwise.
        """
        from bestyy.core_features.user.services.paystack_transfer_service import OrderPaymentAutomation
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            automation = OrderPaymentAutomation()
            success = automation.pay_vendor_on_pickup(self)
            
            if success:
                logger.info(f"✅ Vendor payout triggered for order {self.order_number}")
            else:
                logger.warning(f"⚠️ Vendor payout failed for order {self.order_number}")
            
            return success
        except Exception as e:
            logger.error(f"❌ Error triggering vendor payout for order {self.order_number}: {str(e)}")
            return False
    
    def trigger_courier_payout(self):
        """
        Trigger automatic payment to courier when delivery OTP is verified.
        Returns True if payout initiated successfully, False otherwise.
        """
        from bestyy.core_features.user.services.paystack_transfer_service import OrderPaymentAutomation
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            automation = OrderPaymentAutomation()
            success = automation.pay_courier_on_delivery(self)
            
            if success:
                logger.info(f"✅ Courier payout triggered for order {self.order_number}")
            else:
                logger.warning(f"⚠️ Courier payout failed for order {self.order_number}")
            
            return success
        except Exception as e:
            logger.error(f"❌ Error triggering courier payout for order {self.order_number}: {str(e)}")
            return False
    
    def calculate_payouts(self):
        """
        Calculate payout amounts for vendor, courier, and platform.
        
        PAYMENT DISTRIBUTION FORMULA:
        ────────────────────────────────────────────────────────────
        Customer Pays:     Food Items + Delivery Fee
        
        Platform Fee:      10% of Food Items (NOT including delivery)
        Vendor Gets:       Food Items - Platform Fee (90% of food sales)
        Courier Gets:      100% of Delivery Fee
        Platform Keeps:    Platform Fee (10% of food sales)
        
        EXAMPLE:
        ────────────────────────────────────────────────────────────
        Food Items:        ₦10,000 (self.total_amount)
        Delivery Fee:      ₦1,500  (self.delivery_fee)
        Customer Pays:     ₦11,500 total
        
        Platform Fee:      ₦1,000  (10% of ₦10,000 food)
        Vendor Gets:       ₦9,000  (₦10,000 - ₦1,000 platform fee)
        Courier Gets:      ₦1,500  (100% of delivery fee)
        Platform Keeps:    ₦1,000  (platform fee)
        
        Total Distributed: ₦9,000 + ₦1,500 + ₦1,000 = ₦11,500 ✓
        
        Returns:
            dict: Dictionary with vendor_amount, courier_amount, platform_fee
        """
        from decimal import Decimal
        
        # Ensure we have valid amounts
        food_subtotal = self.total_amount or Decimal('0')
        delivery_fee = self.delivery_fee or Decimal('0')
        
        # Platform fee: 10% of FOOD ITEMS only (not delivery)
        platform_fee_rate = Decimal('0.10')
        platform_fee = food_subtotal * platform_fee_rate
        
        # Vendor gets: Food - Platform Fee (90% of their sales)
        # Note: Vendor does NOT pay for delivery, that's separate
        vendor_amount = food_subtotal - platform_fee
        
        # Courier gets: 100% of delivery fee
        courier_amount = delivery_fee
        
        # Verify our math adds up (important for accounting)
        total_customer_paid = food_subtotal + delivery_fee
        total_distributed = vendor_amount + courier_amount + platform_fee
        
        # Sanity check - should never fail unless there's a bug
        if abs(total_customer_paid - total_distributed) > Decimal('0.01'):
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"⚠️  PAYOUT CALCULATION ERROR for order {self.order_number}:\n"
                f"   Customer paid: ₦{total_customer_paid}\n"
                f"   Distributed: ₦{total_distributed}\n"
                f"   Difference: ₦{total_customer_paid - total_distributed}"
            )
        
        return {
            'vendor_amount': vendor_amount,      # Food revenue - 10% platform fee
            'courier_amount': courier_amount,    # 100% of delivery fee
            'platform_fee': platform_fee,        # 10% commission on food only
            'total_customer_paid': total_customer_paid,  # For verification
            'total_distributed': total_distributed       # Should equal customer_paid
        }


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


class OrderStockReservation(models.Model):
    """
    Model to track stock reservations for orders.
    Stock is reserved when order is placed, and only deducted when order is delivered.
    """
    RESERVATION_STATUS_CHOICES = [
        ('reserved', 'Reserved'),
        ('fulfilled', 'Fulfilled'),  # Stock deducted on delivery
        ('released', 'Released'),    # Order cancelled/failed
    ]
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='stock_reservations'
    )
    product = models.ForeignKey(
        'product.Product',
        on_delete=models.CASCADE,
        related_name='stock_reservations'
    )
    quantity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=RESERVATION_STATUS_CHOICES,
        default='reserved'
    )
    reserved_at = models.DateTimeField(auto_now_add=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-reserved_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product', 'status']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Reservation: {self.quantity}x {self.product.name if self.product else 'Product'} - {self.status}"
    
    def fulfill(self):
        """Mark reservation as fulfilled and deduct stock."""
        if self.status != 'reserved':
            return False
        
        from django.utils import timezone
        
        # Deduct stock from product
        if self.product.stock_quantity >= self.quantity:
            self.product.stock_quantity -= self.quantity
            self.product.save()
            
            self.status = 'fulfilled'
            self.fulfilled_at = timezone.now()
            self.save()
            return True
        return False
    
    def release(self):
        """Release reservation (order cancelled/failed)."""
        if self.status != 'reserved':
            return False
        
        from django.utils import timezone
        
        self.status = 'released'
        self.released_at = timezone.now()
        self.save()
        return True

