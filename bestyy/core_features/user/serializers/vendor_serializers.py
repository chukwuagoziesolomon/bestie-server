"""
Vendor-related serializers.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from ..models import VendorProfile
from .user_serializers import UserSerializer
from ..services.verification_service import VerificationService

User = get_user_model()

class VendorProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for vendor profile data.
    For registration, the user field can be just the ID of an existing user.
    Includes suspension status fields for admin dashboard.
    """
    id = serializers.IntegerField(read_only=True)  # Vendor Profile ID (correct for suspension endpoints)
    user_id = serializers.IntegerField(source='user.id', read_only=True)  # User ID
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False  # Not required for updates
    )
    
    # Suspension status fields
    is_suspended = serializers.BooleanField(read_only=True)
    suspension_reason = serializers.CharField(read_only=True)
    suspension_date = serializers.DateTimeField(read_only=True)
    suspension_duration_days = serializers.IntegerField(read_only=True)
    activation_date = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = VendorProfile
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'verification_status')
        extra_kwargs = {
            'verification_status': {'read_only': True},
        }

    def create(self, validated_data):
        # Get or create user
        user = validated_data.pop('user', None)
        if not user and 'request' in self.context:
            user = self.context['request'].user
        
        if not user:
            raise serializers.ValidationError({"user": "User is required"})
            
        # Check if user already has a vendor profile
        if hasattr(user, 'vendor_profile'):
            raise serializers.ValidationError({"user": "User already has a vendor profile"})
        
        # Create vendor profile
        vendor_profile = VendorProfile.objects.create(
            user=user,
            **validated_data
        )
        return vendor_profile

    def update(self, instance, validated_data):
        # User cannot be updated through this endpoint
        validated_data.pop('user', None)
        
        # Update vendor profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance

class VendorRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for vendor registration.
    Includes user creation and vendor profile creation in one step.
    Now includes bank account details and triggers verification.
    """
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)

    # Bank account fields
    bank_name = serializers.CharField(write_only=True, required=True)
    account_number = serializers.CharField(write_only=True, required=True)
    account_name = serializers.CharField(write_only=True, required=True)
    bank_code = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = VendorProfile
        fields = [
            'email', 'password', 'first_name', 'last_name',
            'business_name', 'business_category', 'cac_number',
            'business_description', 'logo', 'business_address',
            'delivery_radius', 'service_areas', 'opening_hours',
            'closing_hours', 'phone', 'offers_delivery',
            # Bank account fields
            'bank_name', 'account_number', 'account_name', 'bank_code'
        ]
        read_only_fields = ('verification_status', 'created_at', 'updated_at',
                          'email_verified', 'phone_verified', 'bank_account_verified')
        extra_kwargs = {
            'phone': {'required': True},
            'business_name': {'required': True},
            'business_category': {'required': True},
            'business_address': {'required': True},
            'delivery_radius': {'required': True},
            'service_areas': {'required': True},
        }
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate_phone(self, value):
        if not value:
            raise serializers.ValidationError("Phone number is required.")
        return value
    
    def create(self, validated_data):
        from ..models import PendingUser
        import random

        # Extract user data
        user_data = {
            'email': validated_data.pop('email'),
            'password': validated_data.pop('password'),
            'first_name': validated_data.pop('first_name', ''),
            'last_name': validated_data.pop('last_name', ''),
            'phone': validated_data.get('phone'),
        }

        # Extract bank account data
        bank_data = {
            'bank_name': validated_data.pop('bank_name'),
            'account_number': validated_data.pop('account_number'),
            'account_name': validated_data.pop('account_name'),
            'bank_code': validated_data.pop('bank_code'),
        }

        # Prepare profile data (everything except user fields)
        profile_data = dict(validated_data)
        profile_data.update(bank_data)

        # Generate verification code
        verification_code = str(random.randint(100000, 999999))

        # Create pending user instead of actual user
        pending_user = PendingUser.objects.create(
            **user_data,
            user_type='vendor',
            verification_code=verification_code,
            profile_data=profile_data
        )

        return pending_user
