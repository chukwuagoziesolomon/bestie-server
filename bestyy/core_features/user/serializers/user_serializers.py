"""
User-related serializers to avoid circular imports.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.apps import apps
from rest_framework.validators import UniqueValidator
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

# Get the User and UserProfile models using the app registry to avoid circular imports
User = get_user_model()
UserProfile = apps.get_model('user', 'UserProfile')

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user data, used for user details and updates.
    """
    first_name = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter your first name.'}
    )
    last_name = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter your last name.'}
    )
    email = serializers.EmailField(
        required=True,
        error_messages={
            'required': 'Please enter your email address.',
            'invalid': 'Enter a valid email address.'
        },
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message='A user with this email already exists.'
            )
        ]
    )
    phone = serializers.CharField(
        source='profile.phone',
        required=False,
        max_length=16,
        error_messages={
            'max_length': 'Phone number cannot be longer than 16 characters.'
        }
    )
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        error_messages={'required': 'Please enter your password.'},
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        error_messages={'required': 'Please confirm your password.'},
        style={'input_type': 'password'}
    )
    referral_code = serializers.CharField(
        read_only=True,
        required=False,
    )

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'phone', 'password', 'confirm_password', 'referral_code')
        read_only_fields = ('id', 'date_joined')
        extra_kwargs = {
            'password': {'write_only': True},
            'confirm_password': {'write_only': True},
        }

    def validate_username(self, value):
        # Use email as username
        if 'email' in self.initial_data:
            return self.initial_data['email']
        return value

    def validate(self, data):
        # Only validate password if it's being updated
        if 'password' in data and 'confirm_password' in data:
            if data['password'] != data['confirm_password']:
                raise serializers.ValidationError(
                    {"confirm_password": "The two password fields didn't match."}
                )
        return data

    def update(self, instance, validated_data):
        # Handle password update if provided
        password = validated_data.pop('password', None)
        confirm_password = validated_data.pop('confirm_password', None)
        
        # Update user fields
        for attr, value in validated_data.items():
            if attr == 'profile':
                # Update profile fields
                profile_data = value
                profile = instance.profile
                for profile_attr, profile_value in profile_data.items():
                    setattr(profile, profile_attr, profile_value)
                profile.save()
            else:
                setattr(instance, attr, value)
        
        # Update password if provided
        if password and confirm_password and password == confirm_password:
            instance.set_password(password)
        
        instance.save()
        return instance

class UserSignupSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter your first name.'}
    )
    last_name = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter your last name.'}
    )
    email = serializers.EmailField(
        required=True,
        error_messages={
            'required': 'Please enter your email address.',
            'invalid': 'Enter a valid email address.'
        },
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message='A user with this email already exists.'
            )
        ]
    )
    phone = serializers.CharField(
        required=True,
        max_length=16,
        error_messages={
            'required': 'Please enter your phone number.',
            'max_length': 'Phone number cannot be longer than 16 characters.'
        }
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        error_messages={'required': 'Please enter your password.'},
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        error_messages={'required': 'Please confirm your password.'},
        style={'input_type': 'password'}
    )
    referral_code = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                 'phone', 'password', 'confirm_password', 'referral_code')
        extra_kwargs = {
            'password': {'write_only': True},
            'confirm_password': {'write_only': True},
        }

    def validate_username(self, value):
        # Use email as username
        return self.initial_data.get('email', value)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "The two password fields didn't match."})
        return data

    def create(self, validated_data):
        # Remove confirm_password and phone from the data before creating the user
        validated_data.pop('confirm_password', None)
        phone = validated_data.pop('phone')
        email = validated_data.pop('email')
        
        # Create the user
        user = User.objects.create_user(
            username=email,  # Use email as username
            email=email,
            **validated_data
        )
        
        # Create a UserProfile for the new user with the phone number
        UserProfile.objects.create(user=user, phone=phone)
        
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profiles.
    Handles both user and profile updates in a single request.
    """
    class Meta:
        model = UserProfile
        fields = [
            'id', 'phone', 'address', 'nick_name',
            'language', 'profile_picture', 'email_notifications',
            'push_notifications'
        ]
        read_only_fields = ('id',)

    def update(self, instance, validated_data):
        # Handle user data if provided
        user_data = validated_data.pop('user', {})
        user = instance
        
        # Update user fields
        for attr, value in user_data.items():
            # Handle password separately to use set_password
            if attr == 'password':
                user.set_password(value)
            else:
                setattr(user, attr, value)
        user.save()
        
        # Update profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        instance.save()
        return instance


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise AuthenticationFailed('Invalid email or password')

        if not user.check_password(password):
            raise AuthenticationFailed('Invalid email or password')

        if not user.is_active:
            raise AuthenticationFailed('User account is disabled')

        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,  # Primary role for backward compatibility
                'roles': [],  # Since UserRole model was deleted, return empty list for now
                'phone': user.profile.phone if hasattr(user, 'profile') else None,  # Include phone number from profile
            }
        }


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password]
    )


class UserDetailSerializer(UserSerializer):
    """
    Detailed user serializer for admin views.
    """
    class Meta(UserSerializer.Meta):
        fields = tuple(set(UserSerializer.Meta.fields + ('is_active', 'is_staff', 'date_joined')))


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration with role-based profile creation.
    Password is optional for normal users, required for vendors and couriers.
    """
    confirm_password = serializers.CharField(write_only=True, required=False)
    role = serializers.ChoiceField(
        choices=User.ROLE_CHOICES,
        default='user',
        required=False,
        help_text="User role: 'user', 'vendor', or 'courier'"
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password', 'confirm_password', 'phone', 'role')
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'phone': {'required': True}
        }

    def validate_email(self, value):
        # For normal users, email is required but can be a placeholder
        # For vendors and couriers, email is required and must be unique
        role = self.initial_data.get('role', 'user')
        if role in ['vendor', 'courier']:
            if User.objects.filter(email=value).exists():
                raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, data):
        role = data.get('role', 'user')

        # For normal users, password is optional
        # For vendors and couriers, password is required
        if role in ['vendor', 'courier']:
            if not data.get('password'):
                raise serializers.ValidationError({"password": "Password is required for vendors and couriers."})
            if data['password'] != data.get('confirm_password'):
                raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        else:
            # For normal users, if password is provided, validate it matches confirm_password
            if data.get('password') and data.get('confirm_password'):
                if data['password'] != data['confirm_password']:
                    raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        return data

    def create(self, validated_data):
        # Remove fields that shouldn't be passed to create_user
        validated_data.pop('confirm_password', None)
        phone = validated_data.pop('phone', None)
        role = validated_data.pop('role', 'user')
        email = validated_data.pop('email')
        password = validated_data.pop('password')

        # For normal users, password is optional
        # For vendors and couriers, password is required
        if role == 'user' and not password:
            # Create user without password for normal users
            user = User.objects.create(
                email=email,
                role=role,
                phone=phone,
                **validated_data
            )
            # Set unusable password for normal users without password
            user.set_unusable_password()
            user.save()
        else:
            # Create user with password for vendors/couriers or users with password
            user = User.objects.create_user(
                email=email,
                password=password,
                role=role,
                phone=phone,
                **validated_data
            )

        # Create appropriate profile based on role
        if role == 'user' and not hasattr(user, 'profile'):
            UserProfile.objects.create(user=user, phone=phone)

        return user


class MultiRoleRegistrationSerializer(serializers.Serializer):
    """
    Serializer for multi-role registration allowing users to sign up for multiple roles
    with the same email/phone/password but preventing duplicate roles.
    """
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=True, max_length=16)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=[('user', 'User'), ('vendor', 'Vendor'), ('courier', 'Courier')]),
        required=True,
        min_length=1,
        help_text="List of roles to register for: ['user', 'vendor', 'courier']"
    )
    
    # Vendor-specific fields (optional)
    business_name = serializers.CharField(required=False, allow_blank=True)
    business_category = serializers.CharField(required=False, allow_blank=True)
    business_address = serializers.CharField(required=False, allow_blank=True)
    delivery_radius = serializers.IntegerField(required=False, allow_null=True)
    service_areas = serializers.CharField(required=False, allow_blank=True)
    logo = serializers.ImageField(required=False, allow_null=True, allow_empty_file=True)
    cover_photo = serializers.ImageField(required=False, allow_null=True, allow_empty_file=True)
    cac_number = serializers.CharField(required=False, allow_blank=True)
    tin_number = serializers.CharField(required=False, allow_blank=True)
    opening_hours = serializers.TimeField(required=False, allow_null=True)
    closing_hours = serializers.TimeField(required=False, allow_null=True)
    
    # Courier-specific fields (optional)
    vehicle_type = serializers.CharField(required=False, allow_blank=True)
    license_number = serializers.CharField(required=False, allow_blank=True)
    vehicle_registration = serializers.CharField(required=False, allow_blank=True)
    availability_status = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        # Email can exist, but we'll check for role conflicts later
        return value

    def validate_roles(self, value):
        if not value:
            raise serializers.ValidationError("At least one role must be specified.")
        
        # Remove duplicates while preserving order
        unique_roles = list(dict.fromkeys(value))
        if len(unique_roles) != len(value):
            raise serializers.ValidationError("Duplicate roles are not allowed.")
        
        return unique_roles

    def validate(self, data):
        if data['password'] != data.get('confirm_password'):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        
        # Validate vendor-specific fields if vendor role is selected
        if 'vendor' in data['roles']:
            vendor_fields = ['business_name', 'business_category', 'business_address']
            missing_fields = [field for field in vendor_fields if not data.get(field)]
            if missing_fields:
                raise serializers.ValidationError({
                    f"vendor_{field}": f"{field.replace('_', ' ').title()} is required for vendor registration."
                    for field in missing_fields
                })
            # Validate required fields for vendor: opening_hours and closing_hours are mandatory
            if not data.get('opening_hours'):
                raise serializers.ValidationError({"opening_hours": "Opening hours is required for vendor registration."})
            if not data.get('closing_hours'):
                raise serializers.ValidationError({"closing_hours": "Closing hours is required for vendor registration."})
        
        # Validate courier-specific fields if courier role is selected
        if 'courier' in data['roles']:
            courier_fields = ['vehicle_type', 'license_number', 'vehicle_registration']
            missing_fields = [field for field in courier_fields if not data.get(field)]
            if missing_fields:
                raise serializers.ValidationError({
                    f"courier_{field}": f"{field.replace('_', ' ').title()} is required for courier registration."
                    for field in missing_fields
                })
        
        return data

    def create(self, validated_data):
        from ..models import PendingUser
        from django.utils import timezone
        from datetime import timedelta
        import secrets

        # Extract data
        email = validated_data['email']
        password = validated_data['password']
        roles = validated_data['roles']
        phone = validated_data['phone']
        first_name = validated_data.get('first_name') or (email.split('@')[0].split('.')[0].title() if email else 'WhatsApp')
        last_name = validated_data.get('last_name') or 'User'

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({
                'email': 'A user with this email already exists.'
            })

        # Check if pending user already exists
        if PendingUser.objects.filter(email=email, is_verified=False).exists():
            raise serializers.ValidationError({
                'email': 'A registration is already pending for this email. Please check your WhatsApp for verification code.'
            })

        # Generate verification code
        verification_code = str(secrets.randbelow(900000) + 100000)

        # Prepare profile data, handling file uploads separately
        profile_data = {
            'roles': roles,
            'business_name': validated_data.get('business_name', ''),
            'business_category': validated_data.get('business_category', ''),
            'business_address': validated_data.get('business_address', ''),
            'vehicle_type': validated_data.get('vehicle_type', ''),
            'service_areas': validated_data.get('service_areas', ''),
            'cac_number': validated_data.get('cac_number'),
            'tin_number': validated_data.get('tin_number'),
            'license_number': validated_data.get('license_number'),
            'vehicle_registration': validated_data.get('vehicle_registration'),
            'availability_status': validated_data.get('availability_status', 'available'),
            'delivery_radius': validated_data.get('delivery_radius', 5),
        }

        # Handle time fields separately to avoid JSON serialization issues
        if validated_data.get('opening_hours'):
            profile_data['opening_hours'] = validated_data['opening_hours'].strftime('%H:%M:%S') if hasattr(validated_data['opening_hours'], 'strftime') else str(validated_data['opening_hours'])
        if validated_data.get('closing_hours'):
            profile_data['closing_hours'] = validated_data['closing_hours'].strftime('%H:%M:%S') if hasattr(validated_data['closing_hours'], 'strftime') else str(validated_data['closing_hours'])

        # Handle file uploads - store file data separately to avoid JSON serialization issues
        uploaded_files = {}
        if 'logo' in validated_data and validated_data['logo']:
            uploaded_files['logo'] = validated_data['logo']
        if 'cover_photo' in validated_data and validated_data['cover_photo']:
            uploaded_files['cover_photo'] = validated_data['cover_photo']

        # Create pending user instead of actual user
        pending_user = PendingUser.objects.create(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            user_type=roles[0],  # Primary role
            verification_code=verification_code,
            profile_data=profile_data,
            expires_at=timezone.now() + timedelta(hours=24)
        )

        # Handle file uploads - store file info for later processing during verification
        # This avoids upload failures during registration and ensures scalability
        if validated_data.get('logo'):
            logo_file = validated_data['logo']
            if logo_file:
                profile_data['logo_filename'] = logo_file.name
                profile_data['logo_size'] = logo_file.size
                profile_data['logo_content_type'] = getattr(logo_file, 'content_type', 'image/jpeg')

        if validated_data.get('cover_photo'):
            cover_file = validated_data['cover_photo']
            if cover_file:
                profile_data['cover_photo_filename'] = cover_file.name
                profile_data['cover_photo_size'] = cover_file.size
                profile_data['cover_photo_content_type'] = getattr(cover_file, 'content_type', 'image/jpeg')

        # Update pending user with profile data
        pending_user.profile_data = profile_data
        pending_user.save()

        # Note: Files will be uploaded to Cloudinary during WhatsApp verification
        # when the actual user account is created. This prevents registration failures
        # and ensures all users can register even if file upload temporarily fails.

        return pending_user

    def _create_role_profile(self, user, role, validated_data, phone=None):
        """Create the appropriate profile for the role"""
        from .vendor_serializers import VendorProfile
        from .courier_serializers import CourierProfile

        # Use provided phone or get from validated_data
        phone = phone or validated_data.get('phone')

        if role == 'user':
            # Create UserProfile if it doesn't exist
            if not hasattr(user, 'profile'):
                UserProfile.objects.create(user=user, phone=phone)

        elif role == 'vendor':
            # Create VendorProfile if it doesn't exist
            if not hasattr(user, 'vendor_profile'):
                VendorProfile.objects.create(
                    user=user,
                    phone=phone,
                    business_name=validated_data.get('business_name'),
                    business_category=validated_data.get('business_category'),
                    business_address=validated_data.get('business_address'),
                    delivery_radius=validated_data.get('delivery_radius', 5),
                    service_areas=validated_data.get('service_areas', ''),
                    logo=validated_data.get('logo'),
                    cac_number=validated_data.get('cac_number'),
                    opening_hours=validated_data.get('opening_hours'),
                    closing_hours=validated_data.get('closing_hours')
                )

        elif role == 'courier':
            # Create CourierProfile if it doesn't exist
            if not hasattr(user, 'courier_profile'):
                CourierProfile.objects.create(
                    user=user,
                    phone=phone,
                    vehicle_type=validated_data.get('vehicle_type'),
                    license_number=validated_data.get('license_number'),
                    vehicle_registration=validated_data.get('vehicle_registration'),
                    availability_status=validated_data.get('availability_status', 'available')
                )
