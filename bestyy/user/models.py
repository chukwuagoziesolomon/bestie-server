from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

class VendorProfile(models.Model):
    """Profile for vendor users, including business and delivery info."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile')
    phone = models.CharField(max_length=16)
    business_name = models.CharField(max_length=255)
    business_category = models.CharField(max_length=100) # Allows any text, including 'Other'
    cac_number = models.CharField(max_length=100, blank=True, null=True) # Optional
    business_description = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='vendor_logos/', blank=True, null=True) # Optional
    business_address = models.CharField(max_length=255)
    delivery_radius = models.CharField(max_length=50)
    service_areas = models.CharField(max_length=255)  # Comma-separated list
    opening_hours = models.TimeField()
    closing_hours = models.TimeField()
    offers_delivery = models.BooleanField(default=False)
    # Menu items will be a separate model linked to VendorProfile
    VERIFICATION_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    verification_status = models.CharField(max_length=10, choices=VERIFICATION_STATUS, default='pending')

    def __str__(self):
        return self.business_name

class CourierProfile(models.Model):
    """Profile for courier users, including delivery and verification info."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='courier_profile')
    phone = models.CharField(max_length=16)
    service_areas = models.CharField(max_length=255)  # Comma-separated list
    delivery_radius = models.CharField(max_length=50)
    opening_hours = models.TimeField()
    closing_hours = models.TimeField()
    has_bike = models.BooleanField(default=False)
    verification_preference = models.CharField(max_length=50, choices=[('NIN', 'NIN'), ('DL', "Driver's License"), ('VC', "Voter's Card")])
    nin_number = models.CharField(max_length=20, blank=True, null=True)
    id_upload = models.ImageField(upload_to='courier_ids/', blank=True, null=True)
    profile_photo = models.ImageField(upload_to='courier_photos/', blank=True, null=True)
    agreed_to_terms = models.BooleanField(default=False)
    VEHICLE_TYPE_CHOICES = [
        ('bike', 'Bike'),
        ('car', 'Car'),
        ('van', 'Van'),
        ('other', 'Other'),
    ]
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES, blank=True, null=True)
    VERIFICATION_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    verification_status = models.CharField(max_length=10, choices=VERIFICATION_STATUS, default='pending')

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class UserProfile(models.Model):
    """Profile for regular users, including phone number and profile details."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=16)
    address = models.CharField(max_length=255, blank=True, null=True)
    nick_name = models.CharField(max_length=100, blank=True, null=True)
    language = models.CharField(max_length=50, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='user_profiles/', blank=True, null=True)
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class MenuItem(models.Model):
    """Menu item for a vendor, linked to VendorProfile."""
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='menu_items')
    dish_name = models.CharField(max_length=255)
    item_description = models.TextField(blank=True, null=True)  # New field for item description
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100)
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True)
    available_now = models.BooleanField(default=True)
    quantity = models.PositiveIntegerField(default=0)  # New field for quantity

    def __str__(self):
        return f"{self.dish_name} ({self.vendor.business_name})"

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='orders')
    items = models.ManyToManyField(MenuItem)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    order_name = models.CharField(max_length=255, blank=True, null=True)  # Display name for the order
    delivery_address = models.TextField()  # Where the order was delivered
    
    # Payment and delivery tracking
    payment_confirmed = models.BooleanField(default=False)  # Payment has been confirmed by backend
    payment_confirmed_at = models.DateTimeField(null=True, blank=True)  # When payment was confirmed
    user_receipt_confirmed = models.BooleanField(default=False)  # User has confirmed they received the order
    user_receipt_confirmed_at = models.DateTimeField(null=True, blank=True)  # When user confirmed receipt
    
    # Delivery timing
    order_placed_at = models.DateTimeField(default=timezone.now)  # When order was placed
    order_ready_at = models.DateTimeField(null=True, blank=True)  # When order was ready for pickup/delivery
    out_for_delivery_at = models.DateTimeField(null=True, blank=True)  # When order went out for delivery
    delivered_at = models.DateTimeField(null=True, blank=True)  # When order was actually delivered
    
    # Legacy fields for backward compatibility
    delivery_date = models.DateTimeField(null=True, blank=True)  # When it was delivered (legacy)
    
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),  # Order placed, waiting for payment confirmation
        ('payment_confirmed', 'Payment Confirmed'),  # Payment confirmed, waiting for vendor to process
        ('processing', 'Processing'),  # Vendor is preparing the order
        ('ready', 'Ready'),  # Order is ready for pickup/delivery
        ('out_for_delivery', 'Out For Delivery'),  # Order is being delivered
        ('delivered', 'Delivered'),  # Order delivered, waiting for user confirmation
        ('completed', 'Completed'),  # User confirmed receipt
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected')
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

    def save(self, *args, **kwargs):
        # Auto-generate order name if not provided
        if not self.order_name:
            item_names = [item.dish_name for item in self.items.all()]
            if item_names:
                self.order_name = f"{', '.join(item_names[:2])}{'...' if len(item_names) > 2 else ''}"
            else:
                self.order_name = f"Order from {self.vendor.business_name}"
        super().save(*args, **kwargs)
    
    def confirm_payment(self):
        """Confirm that payment has been received and verified"""
        from django.utils import timezone
        self.payment_confirmed = True
        self.payment_confirmed_at = timezone.now()
        self.status = 'payment_confirmed'
        self.save()
    
    def confirm_user_receipt(self):
        """User confirms they have received the order"""
        from django.utils import timezone
        self.user_receipt_confirmed = True
        self.user_receipt_confirmed_at = timezone.now()
        self.status = 'completed'
        self.save()
    
    def mark_as_ready(self):
        """Mark order as ready for pickup/delivery"""
        from django.utils import timezone
        self.order_ready_at = timezone.now()
        self.status = 'ready'
        self.save()
    
    def mark_out_for_delivery(self):
        """Mark order as out for delivery"""
        from django.utils import timezone
        self.out_for_delivery_at = timezone.now()
        self.status = 'out_for_delivery'
        self.save()
    
    def mark_as_delivered(self):
        """Mark order as delivered (waiting for user confirmation)"""
        from django.utils import timezone
        self.delivered_at = timezone.now()
        self.delivery_date = timezone.now()  # Legacy field
        self.status = 'delivered'
        self.save()
    
    @property
    def is_pending_confirmation(self):
        """Check if order is pending user confirmation (payment confirmed but user hasn't confirmed receipt)"""
        return self.payment_confirmed and not self.user_receipt_confirmed and self.status in ['delivered', 'ready']
    
    @property
    def delivery_time_minutes(self):
        """Calculate total delivery time in minutes"""
        if self.delivered_at and self.order_placed_at:
            delta = self.delivered_at - self.order_placed_at
            return int(delta.total_seconds() / 60)
        return None
    
    @property
    def time_since_delivered(self):
        """Calculate time since order was delivered (for pending confirmation)"""
        from django.utils import timezone
        if self.delivered_at:
            delta = timezone.now() - self.delivered_at
            return int(delta.total_seconds() / 60)  # minutes
        return None

class Accommodation(models.Model):
    ACCOMMODATION_TYPES = [
        ('hotel', 'Hotel'),
        ('airbnb', 'Airbnb'),
        ('shortlet', 'Shortlet'),
        ('guesthouse', 'Guest House'),
        ('apartment', 'Apartment'),
    ]
    name = models.CharField(max_length=255)
    accommodation_type = models.CharField(max_length=20, choices=ACCOMMODATION_TYPES, default='hotel')
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    photos = models.ImageField(upload_to='accommodation_photos/', blank=True, null=True)
    logo = models.ImageField(upload_to='accommodation_logos/', blank=True, null=True)
    phone = models.CharField(max_length=16, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    price_range = models.CharField(max_length=50, blank=True, null=True)
    amenities = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    accommodation = models.ForeignKey(Accommodation, on_delete=models.CASCADE, related_name='bookings', null=True, blank=True)
    booking_date = models.DateField()
    booking_time = models.TimeField()
    number_of_people = models.IntegerField()
    room_type = models.CharField(max_length=100, blank=True, null=True)
    special_requests = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Booking #{self.id} by {self.user.username} at {self.accommodation.name if self.accommodation else 'N/A'}"

class Address(models.Model):
    ADDRESS_TYPES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='home')
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=16)
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.address_type.title()} address for {self.user.username}"

    def save(self, *args, **kwargs):
        # If this address is set as default, unset other default addresses for this user
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

class Favorite(models.Model):
    FAVORITE_TYPES = [
        ('food', 'Food Item'),
        ('venue', 'Venue/Vendor'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    favorite_type = models.CharField(max_length=10, choices=FAVORITE_TYPES)
    food_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, null=True, blank=True, related_name='favorited_by')
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [
            ('user', 'food_item'),  # User can only favorite a food item once
            ('user', 'vendor'),     # User can only favorite a vendor once
        ]

    def __str__(self):
        if self.favorite_type == 'food' and self.food_item:
            return f"{self.user.username} likes {self.food_item.dish_name}"
        elif self.favorite_type == 'venue' and self.vendor:
            return f"{self.user.username} likes {self.vendor.business_name}"
        return f"{self.user.username}'s favorite"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.favorite_type == 'food' and not self.food_item:
            raise ValidationError('Food item is required for food favorites.')
        elif self.favorite_type == 'venue' and not self.vendor:
            raise ValidationError('Vendor is required for venue favorites.')
        if self.food_item and self.vendor:
            raise ValidationError('Cannot have both food item and vendor in the same favorite.')

class Payment(models.Model):
    PAYMENT_METHODS = [
        ('card', 'Bank Card'),
        ('bank_transfer', 'Bank Transfer'),
    ]

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    paystack_reference = models.CharField(max_length=100, unique=True)
    paystack_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    description = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)  # Store additional Paystack data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.paystack_reference} - {self.user.username} - {self.amount} {self.currency}"

class SavedCard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_cards')
    card_type = models.CharField(max_length=20)  # visa, mastercard, etc.
    last_four_digits = models.CharField(max_length=4)
    expiry_month = models.CharField(max_length=2)
    expiry_year = models.CharField(max_length=4)
    paystack_authorization_code = models.CharField(max_length=100, unique=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.card_type} ending in {self.last_four_digits}"

    def save(self, *args, **kwargs):
        # If this card is set as default, unset other default cards for this user
        if self.is_default:
            SavedCard.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
