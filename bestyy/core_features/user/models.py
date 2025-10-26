from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Avg, ExpressionWrapper, F, DurationField
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model that supports using email instead of username"""
    ROLE_CHOICES = [
        ('user', 'Regular User'),
        ('vendor', 'Vendor'),
        ('courier', 'Courier'),
    ]

    username = None
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')  # Keep for backward compatibility
    referral_code = models.CharField(max_length=8, unique=True, blank=True, null=True, db_index=True, help_text="Unique referral code for user")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store original role to detect changes
        self._original_role = self.role

    def save(self, *args, **kwargs):
        # Check if role is being changed
        if self.pk and self.role != self._original_role:
            self._role_changed = True

        # Generate referral_code if missing
        if not self.referral_code:
            import secrets
            import string
            alphabet = string.ascii_uppercase + string.digits
            unique = False
            while not unique:
                code = ''.join(secrets.choice(alphabet) for _ in range(8))
                if not User.objects.filter(referral_code=code).exists():
                    unique = True
            self.referral_code = code

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    def has_role(self, role):
        """Check if user has a specific role"""
        return self.user_roles.filter(role=role, is_active=True).exists()

    def get_roles(self):
        """Get all active roles for the user"""
        return [user_role.role for user_role in self.user_roles.filter(is_active=True)]

    def add_role(self, role):
        """Add a new role to the user"""
        if not self.has_role(role):
            UserRole.objects.create(user=self, role=role)

    def remove_role(self, role):
        """Remove a role from the user"""
        UserRole.objects.filter(user=self, role=role).update(is_active=False)

# Create your models here.

class UserRole(models.Model):
    """Model to track multiple roles per user"""
    ROLE_CHOICES = [
        ('user', 'Regular User'),
        ('vendor', 'Vendor'),
        ('courier', 'Courier'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'role']  # Prevent duplicate roles
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.email} - {self.get_role_display()}"

class TransferRecipient(models.Model):
    """Model to track transfer recipients for Paystack payouts"""
    RECIPIENT_TYPES = [
        ('vendor', 'Vendor'),
        ('courier', 'Courier'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='transfer_recipient')
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_TYPES)
    paystack_recipient_code = models.CharField(max_length=50, unique=True)
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=100)
    bank_code = models.CharField(max_length=10)
    bank_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Transfer Recipient'
        verbose_name_plural = 'Transfer Recipients'

    def __str__(self):
        return f"{self.recipient_type.title()}: {self.account_name} - {self.user.email}"

class VendorProfile(models.Model):
    """Profile for vendor users, including business and delivery info."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile')
    phone = models.CharField(max_length=16)
    business_name = models.CharField(max_length=255)
    business_category = models.CharField(max_length=100) # Allows any text, including 'Other'
    # subscription_plan = models.ForeignKey(
    #     'SubscriptionPlan',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     help_text="Vendor's current subscription plan"
    # )
    cac_number = models.CharField(max_length=100, blank=True, null=True) # Optional
    business_description = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='vendor_logos/', blank=True, null=True) # Optional
    business_address = models.CharField(max_length=255)
    delivery_radius = models.CharField(max_length=50)
    service_areas = models.CharField(max_length=255)  # Comma-separated list
    opening_hours = models.TimeField(blank=True, null=True)
    closing_hours = models.TimeField(blank=True, null=True)
    offers_delivery = models.BooleanField(default=False)

    # Verification fields
    VERIFICATION_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    verification_status = models.CharField(
        max_length=10,
        choices=VERIFICATION_STATUS,
        default='pending',
        help_text="Current verification status of the vendor"
    )
    verification_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes from admin regarding verification status"
    )
    verification_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the verification status was last updated"
    )

    # Account suspension fields
    is_suspended = models.BooleanField(
        default=False,
        help_text="Whether the vendor account is currently suspended"
    )
    suspension_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for account suspension"
    )
    suspension_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the account was suspended"
    )
    suspension_duration_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Duration of suspension in days (null for indefinite)"
    )
    activation_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the account was last activated"
    )

    # Featured vendor fields
    is_featured = models.BooleanField(
        default=False,
        help_text="Whether this vendor is featured (paid promotion)"
    )
    featured_priority = models.IntegerField(
        default=0,
        help_text="Priority level for featured vendors (higher = more prominent)"
    )
    featured_expiry = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the featured status expires"
    )

    # Menu freshness tracking
    last_menu_update = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the vendor last updated their menu items"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Bank account information for payouts
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Bank name for payouts"
    )
    account_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Bank account number for payouts"
    )
    account_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Bank account name for payouts"
    )
    bank_code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Bank code for payouts"
    )
    bank_account_verified = models.BooleanField(
        default=False,
        help_text="Whether bank account has been verified"
    )
    bank_account_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When bank account was verified"
    )

    # Email and phone verification
    email_verified = models.BooleanField(
        default=False,
        help_text="Whether email has been verified"
    )
    email_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When email was verified"
    )
    email_verification_token = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Email verification token"
    )
    phone_verified = models.BooleanField(
        default=False,
        help_text="Whether WhatsApp phone has been verified"
    )
    phone_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When phone was verified"
    )
    phone_verification_code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Phone verification code"
    )
    phone_verification_attempts = models.IntegerField(
        default=0,
        help_text="Number of phone verification attempts"
    )

    # Document uploads for verification
    cac_document = models.FileField(
        upload_to='vendor_documents/cac/',
        blank=True,
        null=True,
        help_text="Upload CAC document (PDF, JPG, PNG)"
    )
    valid_id = models.FileField(
        upload_to='vendor_documents/ids/',
        blank=True,
        null=True,
        help_text="Upload a valid ID (Driver's License, NIN, Voter's Card)"
    )
    proof_of_address = models.FileField(
        upload_to='vendor_documents/address_proofs/',
        blank=True,
        null=True,
        help_text="Upload proof of business address"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Vendor Profile'
        verbose_name_plural = 'Vendor Profiles'
        permissions = [
            ('can_verify_vendor', 'Can verify vendor accounts'),
            ('can_manage_vendors', 'Can manage all vendors'),
        ]

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
    verification_preference = models.CharField(
        max_length=50,
        choices=[('NIN', 'NIN'), ('DL', "Driver's License"), ('VC', "Voter's Card")]
    )
    nin_number = models.CharField(max_length=20, blank=True, null=True)
    id_upload = models.ImageField(upload_to='courier_ids/', blank=True, null=True)
    profile_photo = models.ImageField(upload_to='courier_photos/', blank=True, null=True)
    agreed_to_terms = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, help_text="Whether the courier is currently active and can receive deliveries")

    # Account suspension fields
    is_suspended = models.BooleanField(
        default=False,
        help_text="Whether the courier account is currently suspended"
    )
    suspension_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for account suspension"
    )
    suspension_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the account was suspended"
    )
    suspension_duration_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Duration of suspension in days (null for indefinite)"
    )
    activation_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the account was last activated"
    )

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

    # Bank account information for payouts
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Bank name for payouts"
    )
    account_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Bank account number for payouts"
    )
    account_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Bank account name for payouts"
    )
    bank_code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Bank code for payouts"
    )
    bank_account_verified = models.BooleanField(
        default=False,
        help_text="Whether bank account has been verified"
    )
    bank_account_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When bank account was verified"
    )

    # Email and phone verification
    email_verified = models.BooleanField(
        default=False,
        help_text="Whether email has been verified"
    )
    email_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When email was verified"
    )
    email_verification_token = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Email verification token"
    )
    phone_verified = models.BooleanField(
        default=False,
        help_text="Whether WhatsApp phone has been verified"
    )
    phone_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When phone was verified"
    )
    phone_verification_code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Phone verification code"
    )
    phone_verification_attempts = models.IntegerField(
        default=0,
        help_text="Number of phone verification attempts"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Courier Profile'
        verbose_name_plural = 'Courier Profiles'

    def __str__(self):
        return self.user.get_full_name() or self.user.email

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
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.user.get_full_name() or self.user.email

class MenuItem(models.Model):
    """Menu item for a vendor, linked to VendorProfile."""
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='menu_items')
    dish_name = models.CharField(max_length=255)
    item_description = models.TextField(blank=True, null=True)  # New field for item description
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100)
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True)
    video = models.FileField(upload_to='menu_videos/', blank=True, null=True, help_text="30-second promotional video for the menu item")
    available_now = models.BooleanField(default=True)
    quantity = models.PositiveIntegerField(default=0)  # New field for quantity
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.dish_name} ({self.vendor.business_name})"

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='orders')
    courier = models.ForeignKey('CourierProfile', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='deliveries')
    items = models.ManyToManyField(MenuItem)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    order_name = models.CharField(max_length=255, blank=True, null=True)  # Display name for the order
    delivery_address = models.TextField()  # Where the order was delivered
    pickup_address = models.TextField(blank=True, null=True)  # Where to pick up the order from
    special_instructions = models.TextField(blank=True, null=True, help_text="Special instructions from the user")

    # Payment and delivery tracking
    payment_confirmed = models.BooleanField(default=False)  # Payment has been confirmed by backend
    payment_confirmed_at = models.DateTimeField(null=True, blank=True)  # When payment was confirmed
    user_receipt_confirmed = models.BooleanField(default=False)  # User has confirmed they received the order
    user_receipt_confirmed_at = models.DateTimeField(null=True, blank=True)  # When user confirmed receipt

    # Delivery metrics
    distance_km = models.FloatField(null=True, blank=True, help_text="Estimated distance in kilometers")
    delivery_time_minutes = models.IntegerField(null=True, blank=True,
                                               help_text="Total delivery time in minutes")
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'),
                                   help_text="Commission earned by the courier")

    # Location coordinates for distance calculation
    pickup_latitude = models.FloatField(null=True, blank=True, help_text="Pickup location latitude")
    pickup_longitude = models.FloatField(null=True, blank=True, help_text="Pickup location longitude")
    delivery_latitude = models.FloatField(null=True, blank=True, help_text="Delivery location latitude")
    delivery_longitude = models.FloatField(null=True, blank=True, help_text="Delivery location longitude")

    # Delivery pricing
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'),
                                     help_text="Calculated delivery fee based on distance")

    # Conditional payment fields
    pickup_code = models.CharField(max_length=6, blank=True, null=True, help_text="Code for vendor to confirm pickup")
    pickup_code_generated_at = models.DateTimeField(null=True, blank=True)
    pickup_code_verified = models.BooleanField(default=False)
    pickup_code_verified_at = models.DateTimeField(null=True, blank=True)

    vendor_paid = models.BooleanField(default=False, help_text="Whether vendor has been paid")
    courier_paid = models.BooleanField(default=False, help_text="Whether courier has been paid")
    vendor_payout_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'),
                                             help_text="Amount paid to vendor")
    courier_payout_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'),
                                               help_text="Amount paid to courier")
    platform_commission = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'),
                                            help_text="Platform commission retained")

    # Delivery timing
    order_placed_at = models.DateTimeField(default=timezone.now)  # When order was placed
    order_ready_at = models.DateTimeField(null=True, blank=True)  # When order was ready for pickup/delivery
    out_for_delivery_at = models.DateTimeField(null=True, blank=True)  # When order went out for delivery
    delivered_at = models.DateTimeField(null=True, blank=True)  # When order was actually delivered

    # Legacy fields for backward compatibility
    delivery_date = models.DateTimeField(null=True, blank=True)  # When it was delivered (legacy)

    status = models.CharField(max_length=20, choices=[
        ('awaiting', 'Awaiting'),  # Order created, waiting for user confirmation and special instructions
        ('pending', 'Pending'),  # Order placed, waiting for payment confirmation
        ('payment_confirmed', 'Payment Confirmed'),  # Payment confirmed, waiting for vendor to process
        ('processing', 'Processing'),  # Vendor is preparing the order
        ('ready', 'Ready'),  # Order is ready for pickup/delivery
        ('out_for_delivery', 'Out For Delivery'),  # Order is being delivered
        ('delivered', 'Delivered'),  # Order delivered, waiting for user confirmation
        ('completed', 'Completed'),  # User confirmed receipt
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected')
    ], default='awaiting')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.email}"

    def save(self, *args, **kwargs):
        # Auto-generate order name if not provided
        if not self.order_name:
            if self.pk:  # Only access items if the order is already saved
                item_names = [item.dish_name for item in self.items.all()]
                if item_names:
                    self.order_name = f"{', '.join(item_names[:2])}{'...' if len(item_names) > 2 else ''}"
                else:
                    self.order_name = f"Order from {self.vendor.business_name}"
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

    def generate_pickup_code(self):
        """Generate a 6-digit pickup code for vendor confirmation"""
        import random
        from django.utils import timezone

        if not self.pickup_code:
            self.pickup_code = f"{random.randint(100000, 999999)}"
            self.pickup_code_generated_at = timezone.now()
            self.save()

    def generate_delivery_otp(self):
        """Generate a 6-digit delivery OTP for customer confirmation"""
        import random
        from django.utils import timezone

        if not self.delivery_otp:
            self.delivery_otp = f"{random.randint(100000, 999999)}"
            self.delivery_otp_generated_at = timezone.now()
            self.save()

    def verify_pickup_code(self, code):
        """Verify pickup code and trigger vendor payout"""
        from django.utils import timezone

        if self.pickup_code == code and not self.pickup_code_verified:
            self.pickup_code_verified = True
            self.pickup_code_verified_at = timezone.now()
            self.save()
            return True
        return False

    def verify_delivery_otp(self, otp):
        """Verify delivery OTP and trigger courier payout"""
        from django.utils import timezone

        if self.delivery_otp == otp and not self.delivery_otp_verified:
            self.delivery_otp_verified = True
            self.delivery_otp_verified_at = timezone.now()
            self.save()
            return True
        return False

    def calculate_payouts(self):
        """Calculate vendor, courier, and platform amounts"""
        from .models import SystemSettings

        # Get platform commission rate from settings (default 10%)
        platform_commission_rate = SystemSettings.get_setting('platform_commission_rate', Decimal('0.10'))

        # Get default fixed amounts
        default_vendor_fixed_amount = SystemSettings.get_setting('default_vendor_fixed_amount', Decimal('0.00'))  # ₦0 default
        default_courier_fixed_amount = SystemSettings.get_setting('default_courier_fixed_amount', Decimal('500.00'))  # ₦500 default

        # Check if vendor has custom fixed amount in subaccount
        vendor_amount = default_vendor_fixed_amount
        try:
            if self.vendor.user.subaccount and self.vendor.user.subaccount.percentage_charge:
                # Use percentage_charge field to store fixed amount for vendors
                vendor_amount = self.vendor.user.subaccount.percentage_charge
        except:
            # Fallback to percentage calculation if no fixed amount
            vendor_amount = self.total_price * (Decimal('1.0') - platform_commission_rate)

        # Check if courier has custom fixed amount in subaccount
        courier_amount = default_courier_fixed_amount
        try:
            if self.courier and self.courier.user.subaccount and self.courier.user.subaccount.percentage_charge:
                # Use percentage_charge field to store fixed amount for couriers
                courier_amount = self.courier.user.subaccount.percentage_charge
        except:
            # Fallback to delivery fee
            courier_amount = getattr(self, 'delivery_fee', Decimal('500.00'))

        # Platform commission (fixed amount or percentage)
        platform_commission = self.total_price * platform_commission_rate

        # Ensure vendor gets food amount minus platform commission if using percentage
        if vendor_amount == Decimal('0.00'):
            vendor_amount = self.total_price - platform_commission

        return {
            'vendor_amount': vendor_amount,
            'courier_amount': courier_amount,
            'platform_commission': platform_commission
        }

    def calculate_distance_and_fee(self, origin_address=None, destination_address=None):
        """
        Calculate distance and delivery fee using Google Maps with configurable pricing

        Args:
            origin_address: Pickup address (if not provided, uses vendor address)
            destination_address: Delivery address (if not provided, uses delivery_address)

        Returns:
            Dict with distance and pricing info or None if failed
        """
        from user.services.google_maps_service import GoogleMapsService
        from .models import SystemSettings

        # Use provided addresses or fall back to stored addresses
        origin = origin_address or self.vendor.business_address
        destination = destination_address or self.delivery_address

        if not origin or not destination:
            return None

        maps_service = GoogleMapsService()
        result = maps_service.get_distance_and_price(origin, destination)

        if result:
            # Update order fields with calculated data
            self.distance_km = result['distance_km']

            # Calculate delivery fee using configurable pricing
            delivery_fee = self.calculate_delivery_fee(result['distance_km'])
            self.delivery_fee = delivery_fee

            # Store coordinates if available (would need geocoding)
            # For now, just store the calculated values
            self.save()

        return result

    def calculate_delivery_fee(self, distance_km):
        """
        Calculate delivery fee based on distance using configurable pricing

        Args:
            distance_km: Distance in kilometers

        Returns:
            Decimal: Calculated delivery fee
        """
        from .models import SystemSettings

        # Get pricing settings
        base_fee = SystemSettings.get_setting('delivery_base_fee', Decimal('1500.00'))  # ₦1,500 base
        rate_per_km = SystemSettings.get_setting('delivery_rate_per_km', Decimal('300.00'))  # ₦300 per km
        max_distance_for_base = SystemSettings.get_setting('delivery_max_distance_for_base', Decimal('5.0'))  # 5km

        # Convert distance to Decimal for calculations
        distance = Decimal(str(distance_km))

        if distance <= max_distance_for_base:
            # Within base distance - charge base fee
            return base_fee
        else:
            # Beyond base distance - add per-km rate
            extra_distance = distance - max_distance_for_base
            extra_fee = extra_distance * rate_per_km
            return base_fee + extra_fee

    def trigger_vendor_payout(self):
        """Trigger payout to vendor after pickup confirmation (uses Paystack transfer, not split)."""
        from user.services.paystack_service import PaystackService
        from user.models import Transfer

        if not self.pickup_code_verified or self.vendor_paid:
            return False

        payouts = self.calculate_payouts()
        vendor_amount = payouts['vendor_amount']

        paystack_service = PaystackService()

        # Create transfer only after OTP confirmation and if not yet paid
        try:
            recipient = self.vendor.user.transfer_recipient
        except Exception:
            return False

        transfer = Transfer.objects.create(
            order=self,
            recipient=recipient,
            amount=vendor_amount,
            paystack_reference=f'vendor_payout_{self.id}_{int(timezone.now().timestamp())}',
            reason=f'Payment for order #{self.id} - {self.order_name}'
        )

        result = paystack_service.initiate_transfer(
            amount=vendor_amount,
            recipient_code=recipient.paystack_recipient_code,
            reference=transfer.paystack_reference,
            reason=transfer.reason
        )

        if result['success']:
            transfer.paystack_transfer_code = result['transfer_code']
            transfer.save()
            self.vendor_paid = True
            self.vendor_payout_amount = vendor_amount
            self.save()
            return True
        return False

    def trigger_courier_payout(self):
        """Trigger payout to courier after delivery OTP confirmation (uses Paystack transfer, not split)."""
        from user.services.paystack_service import PaystackService
        from user.models import Transfer

        if not self.delivery_otp_verified or self.courier_paid:
            return False

        payouts = self.calculate_payouts()
        courier_amount = payouts['courier_amount']

        paystack_service = PaystackService()

        # Create transfer only after OTP confirmation and if not yet paid
        try:
            recipient = self.courier.user.transfer_recipient
        except Exception:
            return False

        transfer = Transfer.objects.create(
            order=self,
            recipient=recipient,
            amount=courier_amount,
            paystack_reference=f'courier_payout_{self.id}_{int(timezone.now().timestamp())}',
            reason=f'Delivery fee for order #{self.id} - {self.order_name}'
        )

        result = paystack_service.initiate_transfer(
            amount=courier_amount,
            recipient_code=recipient.paystack_recipient_code,
            reference=transfer.paystack_reference,
            reason=transfer.reason
        )

        if result['success']:
            transfer.paystack_transfer_code = result['transfer_code']
            transfer.save()
            self.courier_paid = True
            self.courier_payout_amount = courier_amount
            self.platform_commission = payouts['platform_commission']
            self.save()
            return True
        return False

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
        return f"{self.address_type.title()} address for {self.user.email}"

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
            return f"{self.user.email} likes {self.food_item.dish_name}"
        elif self.favorite_type == 'venue' and self.vendor:
            return f"{self.user.email} likes {self.vendor.business_name}"
        return f"{self.user.email}'s favorite"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.favorite_type == 'food' and not self.food_item:
            raise ValidationError('Food item is required for food favorites.')
        elif self.favorite_type == 'venue' and not self.vendor:
            raise ValidationError('Vendor is required for venue favorites.')
        if self.food_item and self.vendor:
            raise ValidationError('Cannot have both food item and vendor in the same favorite.')

class SavedCard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_cards')
    card_type = models.CharField(max_length=20)
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
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking #{self.id} by {self.user.email} at {self.accommodation.name if self.accommodation else 'N/A'}"

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts')
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='carts', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class OrderItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)  # for custom instructions
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.menu_item.dish_name} x {self.quantity} in Cart {self.cart_id}"

class MenuUpdateReminderLog(models.Model):
    vendor = models.ForeignKey('VendorProfile', on_delete=models.CASCADE, related_name='menu_update_reminders')
    reminder_sent_at = models.DateTimeField(auto_now_add=True)
    reminder_type = models.CharField(max_length=30, default='whatsapp', help_text='Channel: whatsapp/email/etc.')
    status = models.CharField(max_length=30, default='pending', help_text='sent, delivered, failed')
    message_body = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.vendor.business_name} reminded on {self.reminder_sent_at}"

class SystemSettings(models.Model):
    """System-wide settings for pricing and configuration"""
    key = models.CharField(max_length=100, unique=True, help_text="Setting key (e.g., 'delivery_rate_per_km')")
    value = models.CharField(max_length=255, help_text="Setting value")
    description = models.TextField(blank=True, null=True, help_text="Description of what this setting controls")
    data_type = models.CharField(max_length=20, choices=[
        ('string', 'String'),
        ('integer', 'Integer'),
        ('decimal', 'Decimal'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
    ], default='string')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'
        ordering = ['key']

    def __str__(self):
        return f"{self.key}: {self.value}"

    @classmethod
    def get_setting(cls, key, default=None):
        """Get a setting value with type conversion"""
        try:
            setting = cls.objects.get(key=key, is_active=True)
            if setting.data_type == 'integer':
                return int(setting.value)
            elif setting.data_type == 'decimal':
                from decimal import Decimal
                return Decimal(setting.value)
            elif setting.data_type == 'boolean':
                return setting.value.lower() in ('true', '1', 'yes', 'on')
            elif setting.data_type == 'json':
                import json
                return json.loads(setting.value)
            else:
                return setting.value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set_setting(cls, key, value, description=None, data_type='string', user=None):
        """Set a setting value"""
        setting, created = cls.objects.get_or_create(
            key=key,
            defaults={
                'description': description,
                'data_type': data_type,
                'updated_by': user
            }
        )
        setting.value = str(value)
        setting.description = description or setting.description
        setting.data_type = data_type
        setting.updated_by = user
        setting.save()
        return setting

class PendingUser(models.Model):
    """Temporary storage for users during WhatsApp verification signup process"""
    USER_TYPES = [
        ('vendor', 'Vendor'),
        ('courier', 'Courier'),
    ]

    # User data
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # Will be hashed when creating actual user
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=16)

    # User type
    user_type = models.CharField(max_length=10, choices=USER_TYPES)

    # Verification data
    verification_code = models.CharField(max_length=6)
    code_generated_at = models.DateTimeField(auto_now_add=True)

    # Vendor/Courier specific data (stored as JSON)
    profile_data = models.JSONField(default=dict)

    # Status
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['verification_code']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Pending {self.user_type}: {self.email}"

    def save(self, *args, **kwargs):
        # Set expiration to 24 hours from creation if not set
        if not self.expires_at:
            from django.utils import timezone
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def generate_verification_code(self):
        """Generate a new 6-digit verification code"""
        import random
        self.verification_code = str(random.randint(100000, 999999))
        self.code_generated_at = timezone.now()
        self.save()

    def verify_code(self, code):
        """Verify the provided code"""
        if self.is_expired:
            return False, "Verification code has expired"

        if self.verification_code != code:
            return False, "Invalid verification code"

        self.is_verified = True
        self.verified_at = timezone.now()
        self.save()
        return True, "Code verified successfully"

    def create_user_account(self):
        """Create the actual user account after verification"""
        if not self.is_verified:
            return None, "User not verified"

        # Create the user
        user = User.objects.create_user(
            email=self.email,
            password=self.password,  # This will be hashed by create_user
            first_name=self.first_name,
            last_name=self.last_name,
            role=self.user_type
        )

        # Create profile based on user type
        if self.user_type == 'vendor':
            VendorProfile.objects.create(
                user=user,
                phone=self.phone,
                **self.profile_data
            )
        elif self.user_type == 'courier':
            CourierProfile.objects.create(
                user=user,
                phone=self.phone,
                **self.profile_data
            )

        # Mark as processed and return user
        self.delete()  # Remove pending user after successful creation
        return user, "Account created successfully"


class Transfer(models.Model):
    """Model to track individual transfers for Paystack payouts"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='transfers')
    recipient = models.ForeignKey(TransferRecipient, on_delete=models.CASCADE, related_name='transfers')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paystack_reference = models.CharField(max_length=100, unique=True)
    paystack_transfer_code = models.CharField(max_length=50, blank=True, null=True)
    reason = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    failure_reason = models.TextField(blank=True, null=True)
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Transfer'
        verbose_name_plural = 'Transfers'
        ordering = ['-initiated_at']

    def __str__(self):
        return f"Transfer {self.paystack_reference} - ₦{self.amount} to {self.recipient.account_name}"
