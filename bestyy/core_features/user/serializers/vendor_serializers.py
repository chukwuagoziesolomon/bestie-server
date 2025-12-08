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
    
    opening_hours = serializers.TimeField(allow_null=True, required=False)
    closing_hours = serializers.TimeField(allow_null=True, required=False)

    class Meta:
        model = VendorProfile
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'verification_status')
        extra_kwargs = {
            'verification_status': {'read_only': True},
            'logo': {'required': False},
            'cover_image': {'required': False},
            'cover_photo': {'required': False},
        }

    def to_representation(self, instance):
        """Customize the output representation to include bio, cover_photo, cover_image, and logo"""
        data = super().to_representation(instance)
        # Ensure bio and cover_photo are included in the response
        data['bio'] = getattr(instance, 'bio', None)
        
        # Include user information for better frontend experience
        user = instance.user
        data['user_info'] = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name(),
            'email': user.email,
        }
        
        # If business_name is empty, suggest using user's name
        if not data['business_name']:
            data['suggested_business_name'] = f"{user.get_full_name()}'s Business"

        # Image fields are now URLFields, so they're returned as-is
        # No need for special handling since they're plain strings

        return data

    def _get_image_url(self, image_field):
        """Get the full URL for an image field"""
        if image_field:
            try:
                if hasattr(image_field, 'url'):
                    return image_field.url
            except:
                pass
        return None

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

    def validate_opening_hours(self, value):
        if value in ("", None):
            return None
        return value

    def validate_closing_hours(self, value):
        if value in ("", None):
            return None
        return value

    def validate(self, attrs):
        # Also handle object-level normalization of blank time fields
        for field in ['opening_hours', 'closing_hours']:
            if field in attrs and (attrs[field] == "" or attrs[field] is None):
                attrs[field] = None
        return super().validate(attrs)

    def validate_logo(self, value):
        return self._clean_cloudinary_image_value(value)

    def validate_cover_image(self, value):
        return self._clean_cloudinary_image_value(value)

    def validate_cover_photo(self, value):
        return self._clean_cloudinary_image_value(value)

    def _clean_cloudinary_image_value(self, value):
        # Accept null/blank
        if value in (None, ''):
            return None
        # Accept file upload
        if hasattr(value, 'read'):
            return value
        # Convert Cloudinary URL to public_id
        if isinstance(value, str) and value.startswith('http'):
            import re
            from urllib.parse import unquote
            cloudinary_pattern = r'res\\.cloudinary\\.com/[^/]+/image/upload/(?:v\\d+/)?(.+)'
            match = re.search(cloudinary_pattern, value)
            if match:
                public_id_with_ext = unquote(match.group(1))
                return public_id_with_ext
            return value
        return value

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


    class Meta:
        model = VendorProfile
        fields = [
            'email', 'password', 'first_name', 'last_name',
            'business_name', 'business_category', 'cac_number', 'tin_number',
            'business_description', 'logo', 'cover_photo', 'business_address',
            'delivery_radius', 'service_areas', 'opening_hours',
            'closing_hours', 'phone', 'offers_delivery'
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
            'opening_hours': {'required': True},
            'closing_hours': {'required': True},
            'logo': {'required': False},
            'cover_photo': {'required': False},
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

        # Prepare profile data (everything except user fields)
        profile_data = dict(validated_data)

        # Generate verification code
        verification_code = str(random.randint(100000, 999999))

        # Create pending user instead of actual user
        from django.utils import timezone
        from datetime import timedelta

        pending_user = PendingUser.objects.create(
            **user_data,
            user_type='vendor',
            verification_code=verification_code,
            profile_data=profile_data,
            expires_at=timezone.now() + timedelta(hours=24)  # Expire in 24 hours
        )

        return pending_user
