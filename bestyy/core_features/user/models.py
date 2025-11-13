from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Avg, ExpressionWrapper, F, DurationField
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from typing import Optional, Dict, Any
import uuid
import logging

logger = logging.getLogger(__name__)


class UserManager(BaseUserManager):
    """Custom user manager for User model"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom User model extending AbstractUser"""

    ROLE_CHOICES = [
        ('user', 'User'),
        ('vendor', 'Vendor'),
        ('courier', 'Courier'),
    ]

    SOCIAL_PROVIDERS = [
        ('google', 'Google'),
        ('facebook', 'Facebook'),
        ('email', 'Email'),
    ]

    SOCIAL_PROVIDERS = [
        ('google', 'Google'),
        ('facebook', 'Facebook'),
        ('email', 'Email'),
    ]
    
    username = None  # Remove username field
    email = models.EmailField(unique=True, verbose_name='email address')
    
    # Social authentication fields
    social_provider = models.CharField(
        choices=SOCIAL_PROVIDERS, 
        max_length=20, 
        null=True, 
        blank=True
    )
    social_uid = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text="User's ID from the social provider"
    )
    is_social_signup = models.BooleanField(
        default=False, 
        help_text='True if user signed up via social auth'
    )
    
    # Profile completion
    profile_complete = models.BooleanField(
        default=False, 
        help_text='True if user has completed their profile'
    )
    
    # Phone number
    phone = models.CharField(
        max_length=16,
        null=True,
        blank=True
    )

    # Role field for primary role
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='user',
        help_text='Primary user role'
    )

    # Subscription fields for user featured status
    is_featured = models.BooleanField(
        default=False,
        help_text='Whether this user has an active featured subscription'
    )
    subscription_code = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Paystack subscription code for this user'
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('cancelled', 'Cancelled'),
            ('expired', 'Expired'),
        ],
        null=True,
        blank=True,
        help_text='Current status of user subscription'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = UserManager()
    
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        """Return the user's full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_profile_type(self):
        """Get the user's profile type (vendor, courier, or regular user)"""
        if hasattr(self, 'vendor_profile'):
            return 'vendor'
        elif hasattr(self, 'courier_profile'):
            return 'courier'
        else:
            return 'user'

class UserProfile(models.Model):
    """Extended user profile information"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    phone = models.CharField(max_length=16)
    address = models.CharField(max_length=255, null=True, blank=True)
    nick_name = models.CharField(max_length=100, null=True, blank=True)
    language = models.CharField(max_length=50, null=True, blank=True)
    profile_picture = models.ImageField(
        upload_to='user_profiles/', 
        null=True, 
        blank=True
    )
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.email} Profile"


class VendorProfile(models.Model):
    """Vendor business profile"""
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='vendor_profile'
    )
    phone = models.CharField(max_length=16)
    business_name = models.CharField(max_length=255)
    business_category = models.CharField(max_length=100)
    cac_number = models.CharField(max_length=100, null=True, blank=True)
    business_description = models.TextField(null=True, blank=True)
    logo = models.ImageField(
        upload_to='vendor_logos/',
        null=True,
        blank=True
    )
    cover_image = models.ImageField(
        upload_to='vendor_covers/',
        null=True,
        blank=True,
        help_text='Vendor cover photo for profile display'
    )
    business_address = models.CharField(max_length=255)
    delivery_radius = models.CharField(max_length=50)
    service_areas = models.CharField(max_length=255)
    opening_hours = models.TimeField(null=True, blank=True)
    closing_hours = models.TimeField(null=True, blank=True)
    offers_delivery = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=10, 
        choices=VERIFICATION_STATUS_CHOICES, 
        default='pending'
    )
    verification_notes = models.TextField(
        null=True, 
        blank=True,
        help_text='Notes from admin regarding verification status'
    )
    verification_date = models.DateTimeField(
        null=True, 
        blank=True,
        help_text='When the verification status was last updated'
    )
    cac_document = models.FileField(
        upload_to='vendor_documents/cac/', 
        null=True, 
        blank=True,
        help_text='Upload CAC document (PDF, JPG, PNG)'
    )
    valid_id = models.FileField(
        upload_to='vendor_documents/ids/', 
        null=True, 
        blank=True,
        help_text="Upload a valid ID (Driver's License, NIN, Voter's Card)"
    )
    proof_of_address = models.FileField(
        upload_to='vendor_documents/address_proofs/',
        null=True,
        blank=True,
        help_text='Upload proof of business address'
    )
    # Suspension fields
    is_suspended = models.BooleanField(
        default=False,
        help_text='Whether the vendor account is currently suspended'
    )
    suspension_reason = models.TextField(
        null=True,
        blank=True,
        help_text='Reason for account suspension'
    )
    suspension_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the account was suspended'
    )
    suspension_duration_days = models.IntegerField(
        null=True,
        blank=True,
        help_text='Duration of suspension in days (null for indefinite)'
    )
    activation_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the account was last activated'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Vendor Profile'
        verbose_name_plural = 'Vendor Profiles'
        ordering = ['-created_at']
        permissions = [
            ('can_verify_vendor', 'Can verify vendor accounts'),
            ('can_manage_vendors', 'Can manage all vendors')
        ]
    
    def __str__(self):
        return f"{self.business_name}"


class CourierProfile(models.Model):
    """Courier delivery profile"""
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    VEHICLE_TYPE_CHOICES = [
        ('bike', 'Bike'),
        ('car', 'Car'),
        ('van', 'Van'),
        ('other', 'Other'),
    ]
    
    VERIFICATION_PREFERENCE_CHOICES = [
        ('NIN', 'NIN'),
        ('DL', "Driver's License"),
        ('VC', "Voter's Card"),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='courier_profile'
    )
    phone = models.CharField(max_length=16)
    service_areas = models.CharField(max_length=255)
    delivery_radius = models.CharField(max_length=50)

    # Location fields for nearby courier discovery
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Current latitude of the courier'
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Current longitude of the courier'
    )
    last_location_update = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the location was last updated'
    )
    opening_hours = models.TimeField()
    closing_hours = models.TimeField()
    has_bike = models.BooleanField(default=False)
    verification_preference = models.CharField(
        max_length=50, 
        choices=VERIFICATION_PREFERENCE_CHOICES
    )
    nin_number = models.CharField(max_length=20, null=True, blank=True)
    id_upload = models.ImageField(
        upload_to='courier_ids/', 
        null=True, 
        blank=True
    )
    profile_photo = models.ImageField(
        upload_to='courier_photos/', 
        null=True, 
        blank=True
    )
    agreed_to_terms = models.BooleanField(default=False)
    is_active = models.BooleanField(
        default=True,
        help_text='Whether the courier is currently active and can receive deliveries'
    )
    vehicle_type = models.CharField(
        max_length=20,
        choices=VEHICLE_TYPE_CHOICES,
        null=True,
        blank=True
    )
    verification_status = models.CharField(
        max_length=10,
        choices=VERIFICATION_STATUS_CHOICES,
        default='pending'
    )
    # Suspension fields
    is_suspended = models.BooleanField(
        default=False,
        help_text='Whether the courier account is currently suspended'
    )
    suspension_reason = models.TextField(
        null=True,
        blank=True,
        help_text='Reason for account suspension'
    )
    suspension_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the account was suspended'
    )
    suspension_duration_days = models.IntegerField(
        null=True,
        blank=True,
        help_text='Duration of suspension in days (null for indefinite)'
    )
    activation_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the account was last activated'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Courier Profile'
        verbose_name_plural = 'Courier Profiles'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - Courier"


class Address(models.Model):
    """User address information"""
    ADDRESS_TYPE_CHOICES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='addresses'
    )
    address_type = models.CharField(
        max_length=10, 
        choices=ADDRESS_TYPE_CHOICES, 
        default='home'
    )
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
        return f"{self.full_name} - {self.city}"


class TransferRecipient(models.Model):
    """Transfer recipient information for payouts"""
    RECIPIENT_TYPE_CHOICES = [
        ('vendor', 'Vendor'),
        ('courier', 'Courier'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='transfer_recipients'
    )
    recipient_type = models.CharField(
        max_length=20, 
        choices=RECIPIENT_TYPE_CHOICES
    )
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=100)
    bank_code = models.CharField(max_length=10)
    paystack_recipient_code = models.CharField(
        max_length=100, 
        null=True, 
        blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.account_name} - {self.bank_name}"


class DedicatedVirtualAccount(models.Model):
    """Dedicated Virtual Account for Paystack payments"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='dedicated_account'
    )
    paystack_customer_id = models.CharField(max_length=100, null=True, blank=True)
    paystack_dedicated_account_id = models.CharField(max_length=100, null=True, blank=True)
    bank_name = models.CharField(max_length=100)
    bank_slug = models.CharField(max_length=100, null=True, blank=True)
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_assigned = models.BooleanField(default=True)
    assignment_type = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.account_name} - {self.account_number}"

    class Meta:
        verbose_name = 'Dedicated Virtual Account'
        verbose_name_plural = 'Dedicated Virtual Accounts'


class Transfer(models.Model):
    """Money transfer records"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    ]

    order = models.ForeignKey(
        'order.Order',
        on_delete=models.CASCADE,
        related_name='transfers',
        null=True,
        blank=True
    )
    recipient = models.ForeignKey(
        TransferRecipient,
        on_delete=models.CASCADE,
        related_name='transfers'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    paystack_reference = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    paystack_transfer_code = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Transfer {self.amount} to {self.recipient.account_name}"


class Cart(models.Model):
    """
    Session-based cart model for storing user shopping cart items.
    Supports multiple vendors and session persistence.
    """
    CART_STATUS_CHOICES = [
        ('active', 'Active'),
        ('abandoned', 'Abandoned'),
        ('converted', 'Converted to Order'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='carts',
        null=True,
        blank=True,
        help_text='User who owns the cart (null for anonymous carts)'
    )
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        help_text='Django session key for anonymous users'
    )
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='carts',
        help_text='Vendor this cart is associated with'
    )
    status = models.CharField(
        max_length=20,
        choices=CART_STATUS_CHOICES,
        default='active',
        help_text='Current status of the cart'
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Total price of all items in cart'
    )
    item_count = models.PositiveIntegerField(
        default=0,
        help_text='Total number of items in cart'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this cart is currently active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'vendor', 'is_active']),
            models.Index(fields=['session_key', 'vendor', 'is_active']),
            models.Index(fields=['status', 'updated_at']),
        ]

    def __str__(self):
        owner = self.user.email if self.user else f"Session: {self.session_key[:8]}..."
        return f"{owner} - {self.vendor.business_name} ({self.item_count} items)"

    def add_item(self, menu_item, quantity=1, variants=None, special_instructions=''):
        """
        Add an item to the cart or update quantity if it already exists.
        """
        from decimal import Decimal

        # Check if item already exists in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=self,
            menu_item=menu_item,
            defaults={
                'quantity': 0,
                'base_price': menu_item.price,
                'variants': variants or {},
                'special_instructions': special_instructions,
            }
        )

        # Update quantity and total price
        old_quantity = cart_item.quantity
        cart_item.quantity += quantity
        cart_item.variants = variants or cart_item.variants
        cart_item.special_instructions = special_instructions or cart_item.special_instructions
        cart_item.total_price = Decimal(str(cart_item.base_price)) * cart_item.quantity
        cart_item.save()

        # Update cart totals
        self.total_price += (cart_item.base_price * quantity)
        self.item_count += quantity
        self.save()

        return cart_item, created

    def remove_item(self, menu_item, quantity=None):
        """
        Remove quantity of an item from cart, or remove entirely if quantity is None.
        """
        try:
            cart_item = CartItem.objects.get(cart=self, menu_item=menu_item)

            if quantity is None or quantity >= cart_item.quantity:
                # Remove entire item
                removed_quantity = cart_item.quantity
                removed_price = cart_item.total_price
                cart_item.delete()
            else:
                # Reduce quantity
                removed_quantity = quantity
                removed_price = cart_item.base_price * quantity
                cart_item.quantity -= quantity
                cart_item.total_price = cart_item.base_price * cart_item.quantity
                cart_item.save()

            # Update cart totals
            self.total_price -= removed_price
            self.item_count -= removed_quantity
            self.save()

            return True, removed_quantity

        except CartItem.DoesNotExist:
            return False, 0

    def clear(self):
        """
        Clear all items from the cart.
        """
        CartItem.objects.filter(cart=self).delete()
        self.total_price = 0
        self.item_count = 0
        self.save()

    def get_items(self):
        """
        Get all items in the cart with full details.
        """
        return CartItem.objects.filter(cart=self).select_related('menu_item')

    @classmethod
    def get_or_create_cart(cls, user, vendor, session_key=None):
        """
        Get or create a cart for the user/vendor combination.
        """
        # For authenticated users, look for existing active cart
        if user and user.is_authenticated:
            cart, created = cls.objects.get_or_create(
                user=user,
                vendor=vendor,
                is_active=True,
                defaults={'status': 'active'}
            )
        else:
            # For anonymous users, use session key
            if not session_key:
                raise ValueError("Session key required for anonymous users")

            cart, created = cls.objects.get_or_create(
                session_key=session_key,
                vendor=vendor,
                is_active=True,
                defaults={'status': 'active'}
            )

        return cart, created

    def merge_with_user_cart(self, user):
        """
        Merge anonymous cart with user's cart when user logs in.
        """
        if not user or not user.is_authenticated:
            return

        # Find user's existing cart for this vendor
        try:
            user_cart = Cart.objects.get(
                user=user,
                vendor=self.vendor,
                is_active=True
            )

            # Merge items from anonymous cart to user cart
            for cart_item in self.get_items():
                user_cart.add_item(
                    cart_item.menu_item,
                    cart_item.quantity,
                    cart_item.variants,
                    cart_item.special_instructions
                )

            # Delete anonymous cart
            self.delete()

            return user_cart

        except Cart.DoesNotExist:
            # No existing user cart, just assign this cart to the user
            self.user = user
            self.session_key = None
            self.save()
            return self


class CartItem(models.Model):
    """
    Individual item in a shopping cart.
    """
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    menu_item = models.ForeignKey(
        'product.Product',
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    base_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text='Price per unit at time of adding to cart'
    )
    variants = models.JSONField(
        default=dict,
        blank=True,
        help_text='Selected variants (size, toppings, etc.)'
    )
    special_instructions = models.TextField(
        blank=True,
        help_text='Special preparation instructions'
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Total price for this item (base_price * quantity)'
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        ordering = ['added_at']
        unique_together = ['cart', 'menu_item']  # One item per cart

    def __str__(self):
        return f"{self.cart} - {self.menu_item.dish_name} (x{self.quantity})"

    def save(self, *args, **kwargs):
        # Auto-calculate total price
        from decimal import Decimal
        self.total_price = Decimal(str(self.base_price)) * self.quantity
        super().save(*args, **kwargs)


class Favorite(models.Model):
    """
    Model for user favorites (food items or vendors).
    """
    FAVORITE_TYPES = [
        ('food', 'Food Item'),
        ('venue', 'Vendor/Venue'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    favorite_type = models.CharField(max_length=20, choices=FAVORITE_TYPES)
    food_item = models.ForeignKey(
        'product.Product',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='favorites'
    )
    vendor = models.ForeignKey(
        'VendorProfile',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='favorites'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Favorite'
        verbose_name_plural = 'Favorites'
        ordering = ['-created_at']
        unique_together = ['user', 'food_item', 'vendor']  # Prevent duplicate favorites

    def __str__(self):
        if self.favorite_type == 'food':
            return f"{self.user.email} - {self.food_item.name if self.food_item else 'Unknown Food'}"
        else:
            return f"{self.user.email} - {self.vendor.business_name if self.vendor else 'Unknown Vendor'}"


class UserRecommendationHistory(models.Model):
    """
    Model to track when users receive personalized recommendations.
    Used to ensure fair cycling and prevent spam.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='recommendation_history')
    last_sent = models.DateTimeField(null=True, blank=True)
    total_sent = models.PositiveIntegerField(default=0)
    # Featured vendor fields
    is_featured = models.BooleanField(
        default=False,
        help_text='Whether this vendor is currently featured'
    )
    featured_priority = models.IntegerField(
        default=0,
        help_text='Priority order for featured vendors (higher = more prominent)'
    )
    featured_expiry = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the featured status expires'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Recommendation History'
        verbose_name_plural = 'User Recommendation Histories'
        ordering = ['-last_sent']

    def __str__(self):
        return f"{self.user.email} - {self.total_sent} recommendations"

    @staticmethod
    def get_next_eligible_users(limit=15):
        """
        Get users who haven't received recommendations recently.
        Cycles through users fairly to prevent any user from being spammed.
        """
        from django.db.models import Q
        from datetime import timedelta

        three_days_ago = timezone.now() - timedelta(days=3)

        # Get users who haven't received recommendations in the last 3 days
        # Order by last_sent (oldest first) to ensure fair cycling
        eligible_histories = UserRecommendationHistory.objects.filter(
            Q(last_sent__isnull=True) | Q(last_sent__lt=three_days_ago)
        ).select_related('user').order_by('last_sent')[:limit]

        return [history.user for history in eligible_histories]

    @staticmethod
    def create_or_get(user):
        """
        Get or create recommendation history for a user.
        """
        history, created = UserRecommendationHistory.objects.get_or_create(
            user=user,
            defaults={'total_sent': 0}
        )
        return history

    def mark_sent(self):
        """
        Mark that a recommendation was sent to this user.
        """
        from django.utils import timezone
        self.last_sent = timezone.now()
        self.total_sent += 1
        self.save()


class ImageUpload(models.Model):
    """
    Model to track uploaded images with duplicate detection.
    """
    IMAGE_TYPES = [
        ('vendor_logo', 'Vendor Logo'),
        ('vendor_cover', 'Vendor Cover Photo'),
        ('menu_item', 'Menu Item Image'),
        ('courier_photo', 'Courier Profile Photo'),
    ]

    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='uploaded_images')
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPES)
    image_hash = models.CharField(max_length=64, db_index=True, help_text="SHA256 hash for duplicate detection")
    cloudinary_public_id = models.CharField(max_length=100, unique=True)
    cloudinary_url = models.URLField()
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    metadata = models.JSONField(default=dict, help_text="Additional metadata about the image")
    is_active = models.BooleanField(default=True, help_text="Whether this image is still in use")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Image Upload'
        verbose_name_plural = 'Image Uploads'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['image_hash', 'image_type', 'is_active']),
            models.Index(fields=['user', 'image_type']),
        ]

    def __str__(self):
        return f"{self.image_type} - {self.original_filename}"

    def get_optimized_url(self, width: Optional[int] = None, height: Optional[int] = None) -> str:
        """
        Get optimized image URL with optional resizing.
        """
        if not width and not height:
            return self.cloudinary_url

        # Use Cloudinary's URL transformation
        # This is a simplified implementation - in production, use Cloudinary SDK
        transformations = []
        if width:
            transformations.append(f"w_{width}")
        if height:
            transformations.append(f"h_{height}")
        if width and height:
            transformations.append("c_fill")

        transform_str = ",".join(transformations)
        base_url = self.cloudinary_url.replace('/upload/', f'/upload/{transform_str}/')
        return base_url


class SystemSettings(models.Model):
    """
    Model for storing system-wide settings and configuration values.
    Used for dynamic configuration of platform settings like fees, rates, etc.
    """
    DATA_TYPE_CHOICES = [
        ('string', 'String'),
        ('integer', 'Integer'),
        ('decimal', 'Decimal'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
    ]

    key = models.CharField(
        max_length=100,
        unique=True,
        help_text='Unique key for the setting'
    )
    value = models.TextField(
        help_text='Value of the setting (stored as string, cast based on data_type)'
    )
    description = models.TextField(
        blank=True,
        help_text='Description of what this setting controls'
    )
    data_type = models.CharField(
        max_length=20,
        choices=DATA_TYPE_CHOICES,
        default='string',
        help_text='Data type for proper casting'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this setting is currently active'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_settings',
        help_text='User who last updated this setting'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'
        ordering = ['key']
        indexes = [
            models.Index(fields=['key', 'is_active']),
        ]

    def __str__(self):
        return f"{self.key}: {self.value}"

    @property
    def typed_value(self):
        """Return the value cast to the appropriate data type."""
        if self.data_type == 'integer':
            try:
                return int(self.value)
            except (ValueError, TypeError):
                return 0
        elif self.data_type == 'decimal':
            try:
                return Decimal(self.value)
            except (ValueError, TypeError, decimal.InvalidOperation):
                return Decimal('0.00')
        elif self.data_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.data_type == 'json':
            try:
                import json
                return json.loads(self.value)
            except (ValueError, TypeError):
                return {}
        else:
            return self.value

    @classmethod
    def get_setting(cls, key, default=None):
        """
        Get a setting value by key, with optional default.
        Returns the typed value based on data_type.
        """
        try:
            setting = cls.objects.get(key=key, is_active=True)
            return setting.typed_value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set_setting(cls, key, value, description='', data_type='string', user=None):
        """
        Create or update a system setting.
        """
        # Determine data type if not specified
        if data_type == 'string':
            if isinstance(value, bool):
                data_type = 'boolean'
            elif isinstance(value, int):
                data_type = 'integer'
            elif isinstance(value, (Decimal, float)):
                data_type = 'decimal'

        setting, created = cls.objects.get_or_create(
            key=key,
            defaults={
                'value': str(value),
                'description': description,
                'data_type': data_type,
                'updated_by': user,
            }
        )

        if not created:
            setting.value = str(value)
            setting.description = description or setting.description
            setting.data_type = data_type
            setting.updated_by = user
            setting.is_active = True
            setting.save()

        return setting

    @classmethod
    def get_active_settings(cls):
        """
        Get all active settings as a dictionary with typed values.
        """
        settings = {}
        for setting in cls.objects.filter(is_active=True):
            settings[setting.key] = setting.typed_value
        return settings


class PendingUser(models.Model):
    """
    Model for pending users awaiting verification.
    Used during signup process before account activation.
    """
    USER_TYPE_CHOICES = [
        ('vendor', 'Vendor'),
        ('courier', 'Courier'),
    ]

    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=16)
    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_CHOICES
    )
    verification_code = models.CharField(max_length=6)
    code_generated_at = models.DateTimeField(auto_now_add=True)
    profile_data = models.JSONField(default=dict)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        verbose_name = 'Pending User'
        verbose_name_plural = 'Pending Users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['verification_code']),
            models.Index(fields=['expires_at']),
        ]

    @property
    def is_expired(self):
        """Check if the pending user verification has expired."""
        return timezone.now() > self.expires_at

    def create_user_account(self):
        """
        Create the actual user account from pending user data.
        Handles multi-role registration by checking existing users.
        """
        try:
            from django.contrib.auth import get_user_model
            from django.db import transaction
            User = get_user_model()

            clean_phone = self.phone.replace('+', '').replace(' ', '').replace('-', '').strip()

            with transaction.atomic():
                # Check if user already exists - FIRST by email (most reliable), then by phone
                # Do this INSIDE the transaction to avoid race conditions
                existing_user = None

                # Priority 1: Check if user exists by email (most reliable check)
                try:
                    existing_user = User.objects.select_for_update().get(email=self.email)
                    logger.info(f"Found existing user by email: {existing_user.email}")
                except User.DoesNotExist:
                    # Priority 2: Look for existing user by phone across all profiles
                    user_profile_exists = UserProfile.objects.filter(phone__icontains=clean_phone).exists()
                    vendor_profile_exists = VendorProfile.objects.filter(phone__icontains=clean_phone).exists()
                    courier_profile_exists = CourierProfile.objects.filter(phone__icontains=clean_phone).exists()

                    if user_profile_exists or vendor_profile_exists or courier_profile_exists:
                        # Find the user associated with any of these profiles
                        if user_profile_exists:
                            existing_user = UserProfile.objects.select_related('user').filter(phone__icontains=clean_phone).first().user
                        elif vendor_profile_exists:
                            existing_user = VendorProfile.objects.select_related('user').filter(phone__icontains=clean_phone).first().user
                        elif courier_profile_exists:
                            existing_user = CourierProfile.objects.select_related('user').filter(phone__icontains=clean_phone).first().user

                        if existing_user:
                            logger.info(f"Found existing user by phone: {existing_user.email}")
                if existing_user:
                    # User exists, add the new role/profile
                    logger.info(f"Adding {self.user_type} role to existing user: {existing_user.email}")

                    if self.user_type == 'vendor':
                        # Check if vendor profile already exists using database query (with lock to prevent race conditions)
                        if VendorProfile.objects.filter(user=existing_user).exists():
                            logger.info(f"User {existing_user.email} already has a vendor profile - skipping creation")
                            return existing_user, f"You have already signed up as a vendor. You can log in to your existing account."

                        # Create vendor profile with error handling for duplicate key violations
                        try:
                            VendorProfile.objects.create(
                                user=existing_user,
                                phone=self.phone,
                                business_name=self.profile_data.get('business_name', ''),
                                business_category=self.profile_data.get('business_category', ''),
                                business_address=self.profile_data.get('business_address', ''),
                                delivery_radius=self.profile_data.get('delivery_radius', '5'),
                                service_areas=self.profile_data.get('service_areas', ''),
                                offers_delivery=self.profile_data.get('offers_delivery', False),
                                cac_number=self.profile_data.get('cac_number'),
                                business_description=self.profile_data.get('business_description'),
                            )
                            logger.info(f"Successfully created vendor profile for user {existing_user.email}")
                        except Exception as e:
                            # Check if this is a duplicate key error (race condition or concurrent request)
                            from django.db import IntegrityError
                            error_str = str(e).lower()
                            if isinstance(e, IntegrityError) and ('unique constraint failed' in error_str or 'duplicate key' in error_str) and ('vendorprofile' in error_str or 'user_id' in error_str):
                                logger.warning(f"Vendor profile already exists for user {existing_user.email} (race condition detected)")
                                # Verify it actually exists now
                                if VendorProfile.objects.filter(user=existing_user).exists():
                                    return existing_user, f"You have already signed up as a vendor. You can log in to your existing account."
                            logger.error(f"Failed to create vendor profile for user {existing_user.email}: {str(e)}")
                            return None, f"Failed to create vendor profile: {str(e)}"

                    elif self.user_type == 'courier':
                        # Check if courier profile already exists using database query
                        if CourierProfile.objects.filter(user=existing_user).exists():
                            logger.info(f"User {existing_user.email} already has a courier profile - skipping creation")
                            return existing_user, f"You have already signed up as a courier. You can log in to your existing account."

                        # Create courier profile with error handling for duplicate key violations
                        try:
                            CourierProfile.objects.create(
                                user=existing_user,
                                phone=self.phone,
                                service_areas=self.profile_data.get('service_areas', ''),
                                delivery_radius=self.profile_data.get('delivery_radius', '10'),
                                opening_hours=self.profile_data.get('opening_hours'),
                                closing_hours=self.profile_data.get('closing_hours'),
                                has_bike=self.profile_data.get('has_bike', False),
                                verification_preference=self.profile_data.get('verification_preference', 'NIN'),
                                agreed_to_terms=self.profile_data.get('agreed_to_terms', False),
                                vehicle_type=self.profile_data.get('vehicle_type'),
                            )
                            logger.info(f"Successfully created courier profile for user {existing_user.email}")
                        except Exception as e:
                            # Check if this is a duplicate key error (race condition or concurrent request)
                            from django.db import IntegrityError
                            error_str = str(e).lower()
                            if isinstance(e, IntegrityError) and ('unique constraint failed' in error_str or 'duplicate key' in error_str) and ('courierprofile' in error_str or 'user_id' in error_str):
                                logger.warning(f"Courier profile already exists for user {existing_user.email} (race condition detected)")
                                # Verify it actually exists now
                                if CourierProfile.objects.filter(user=existing_user).exists():
                                    return existing_user, f"You have already signed up as a courier. You can log in to your existing account."
                            logger.error(f"Failed to create courier profile for user {existing_user.email}: {str(e)}")
                            return None, f"Failed to create courier profile: {str(e)}"

                    # Update user's primary role if it's still 'user'
                    if existing_user.role == 'user':
                        existing_user.role = self.user_type
                        existing_user.save()

                    # Mark pending user as verified
                    self.is_verified = True
                    self.verified_at = timezone.now()
                    self.save()

                    return existing_user, f"Successfully added {self.user_type} role to existing account"

                else:
                    # Create new user account
                    logger.info(f"Creating new user account for: {self.email}")

                    # Create the user with error handling for duplicate email (race condition)
                    user = None
                    try:
                        user = User.objects.create_user(
                            email=self.email,
                            password=self.password,
                            first_name=self.first_name,
                            last_name=self.last_name,
                            phone=self.phone,
                            role=self.user_type
                        )
                        logger.info(f"Successfully created new user: {user.email}")
                    except Exception as e:
                        # Check if this is a duplicate email error (race condition)
                        from django.db import IntegrityError
                        error_str = str(e).lower()
                        if isinstance(e, IntegrityError) and ('unique constraint failed' in error_str or 'duplicate key' in error_str) and 'email' in error_str:
                            logger.warning(f"User with email {self.email} already exists (race condition detected) - fetching existing user")
                            # User exists - fetch it and treat as existing user
                            try:
                                existing_user = User.objects.get(email=self.email)
                                # Check if profile already exists
                                if self.user_type == 'vendor' and VendorProfile.objects.filter(user=existing_user).exists():
                                    logger.info(f"User {existing_user.email} already has vendor profile")
                                    self.is_verified = True
                                    self.verified_at = timezone.now()
                                    self.save()
                                    return existing_user, f"You have already signed up as a vendor. You can log in to your existing account."
                                elif self.user_type == 'courier' and CourierProfile.objects.filter(user=existing_user).exists():
                                    logger.info(f"User {existing_user.email} already has courier profile")
                                    self.is_verified = True
                                    self.verified_at = timezone.now()
                                    self.save()
                                    return existing_user, f"You have already signed up as a courier. You can log in to your existing account."
                                # User exists but doesn't have this profile type - continue to create profile
                                user = existing_user
                                logger.info(f"User exists but needs {self.user_type} profile - will create profile")
                            except User.DoesNotExist:
                                logger.error(f"IntegrityError for email but user not found: {self.email}")
                                return None, f"An account with this email may already exist. Please try logging in."
                        else:
                            logger.error(f"Failed to create user with email {self.email}: {str(e)}")
                            return None, f"Failed to create user account: {str(e)}"

                    # If we still don't have a user at this point, something went wrong
                    if not user:
                        logger.error(f"User is None after creation attempt for {self.email}")
                        return None, f"Failed to create user account."

                    # Before creating profile, double-check it doesn't already exist (race condition protection)
                    if self.user_type == 'vendor':
                        if VendorProfile.objects.filter(user=user).exists():
                            logger.warning(f"Vendor profile already exists for user {user.email} - this shouldn't happen in new user creation path")
                            # Profile already exists - mark as verified and return
                            self.is_verified = True
                            self.verified_at = timezone.now()
                            self.save()
                            return user, "Account already exists. Profile verified."
                    elif self.user_type == 'courier':
                        if CourierProfile.objects.filter(user=user).exists():
                            logger.warning(f"Courier profile already exists for user {user.email} - this shouldn't happen in new user creation path")
                            # Profile already exists - mark as verified and return
                            self.is_verified = True
                            self.verified_at = timezone.now()
                            self.save()
                            return user, "Account already exists. Profile verified."

                    # Create appropriate profile based on user type
                    try:
                        if self.user_type == 'vendor':
                            VendorProfile.objects.create(
                                user=user,
                                phone=self.phone,
                                business_name=self.profile_data.get('business_name', ''),
                                business_category=self.profile_data.get('business_category', ''),
                                business_address=self.profile_data.get('business_address', ''),
                                delivery_radius=self.profile_data.get('delivery_radius', '5'),
                                service_areas=self.profile_data.get('service_areas', ''),
                                offers_delivery=self.profile_data.get('offers_delivery', False),
                                cac_number=self.profile_data.get('cac_number'),
                                business_description=self.profile_data.get('business_description'),
                            )

                        elif self.user_type == 'courier':
                            CourierProfile.objects.create(
                                user=user,
                                phone=self.phone,
                                service_areas=self.profile_data.get('service_areas', ''),
                                delivery_radius=self.profile_data.get('delivery_radius', '10'),
                                opening_hours=self.profile_data.get('opening_hours'),
                                closing_hours=self.profile_data.get('closing_hours'),
                                has_bike=self.profile_data.get('has_bike', False),
                                verification_preference=self.profile_data.get('verification_preference', 'NIN'),
                                agreed_to_terms=self.profile_data.get('agreed_to_terms', False),
                                vehicle_type=self.profile_data.get('vehicle_type'),
                            )

                        else:
                            # Regular user profile
                            UserProfile.objects.create(
                                user=user,
                                phone=self.phone,
                            )
                    except Exception as e:
                        # Check if this is a duplicate profile error - handle it gracefully
                        from django.db import IntegrityError
                        error_str = str(e).lower()
                        error_message = str(e)

                        logger.warning(f"Exception while creating {self.user_type} profile for user {user.email}: {error_message}")

                        if isinstance(e, IntegrityError):
                            # Check for UNIQUE constraint errors - SQLite format: "UNIQUE constraint failed: user_vendorprofile.user_id"
                            is_unique_error = ('unique constraint failed' in error_str or 'duplicate key' in error_str or 'unique' in error_str)

                            if is_unique_error:
                                # Check for vendor profile constraint
                                if self.user_type == 'vendor' and ('vendorprofile' in error_str or 'user_vendorprofile' in error_str or 'user_id' in error_str):
                                    logger.warning(f"Vendor profile UNIQUE constraint violation for user {user.email} - checking if profile exists")
                                    # Verify it exists and return success
                                    profile_exists = VendorProfile.objects.filter(user=user).exists()
                                    if profile_exists:
                                        logger.info(f"Vendor profile exists for user {user.email} - returning success")
                                        self.is_verified = True
                                        self.verified_at = timezone.now()
                                        self.save()
                                        return user, "Account already exists. Profile verified."
                                    else:
                                        logger.error(f"IntegrityError but profile doesn't exist - this is unexpected for user {user.email}")

                                # Check for courier profile constraint
                                elif self.user_type == 'courier' and ('courierprofile' in error_str or 'user_courierprofile' in error_str or 'user_id' in error_str):
                                    logger.warning(f"Courier profile UNIQUE constraint violation for user {user.email} - checking if profile exists")
                                    profile_exists = CourierProfile.objects.filter(user=user).exists()
                                    if profile_exists:
                                        logger.info(f"Courier profile exists for user {user.email} - returning success")
                                        self.is_verified = True
                                        self.verified_at = timezone.now()
                                        self.save()
                                        return user, "Account already exists. Profile verified."
                                    else:
                                        logger.error(f"IntegrityError but profile doesn't exist - this is unexpected for user {user.email}")

                                # Check for user profile constraint
                                elif self.user_type == 'user' and ('userprofile' in error_str or 'user_userprofile' in error_str or 'user_id' in error_str):
                                    logger.warning(f"User profile UNIQUE constraint violation for user {user.email} - checking if profile exists")
                                    profile_exists = UserProfile.objects.filter(user=user).exists()
                                    if profile_exists:
                                        logger.info(f"User profile exists for user {user.email} - returning success")
                                        self.is_verified = True
                                        self.verified_at = timezone.now()
                                        self.save()
                                        return user, "Account already exists. Profile verified."
                                    else:
                                        logger.error(f"IntegrityError but profile doesn't exist - this is unexpected for user {user.email}")

                        # If we get here, it's not a duplicate profile error or profile doesn't exist
                        # For any other IntegrityError or exception, return error
                        logger.error(f"Failed to create {self.user_type} profile for user {user.email}: {error_message}")
                        # Return error - transaction will handle cleanup
                        return None, f"Failed to create {self.user_type} profile: {error_message}"

                    # Mark pending user as verified
                    self.is_verified = True
                    self.verified_at = timezone.now()
                    self.save()

                    return user, "Account created successfully"

        except Exception as e:
            logger.error(f"Error creating user account: {str(e)}", exc_info=True)
            return None, f"Failed to create account: {str(e)}"

    def __str__(self):
        return f"{self.email} - {self.user_type} (Pending)"
