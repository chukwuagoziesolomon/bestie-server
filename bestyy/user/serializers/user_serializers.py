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

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'phone', 'password', 'confirm_password')
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

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                 'phone', 'password', 'confirm_password')
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
    user = UserSerializer(required=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'phone', 'address', 'nick_name', 
            'language', 'profile_picture', 'email_notifications', 
            'push_notifications', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')

    def update(self, instance, validated_data):
        # Handle user data if provided
        user_data = validated_data.pop('user', {})
        user = instance.user
        
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
                'roles': user.get_roles(),  # All roles
                'phone': user.phone,  # Include phone number
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
    """
    confirm_password = serializers.CharField(write_only=True, required=True)
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
            'password': {'write_only': True},
            'phone': {'required': True}
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, data):
        if data['password'] != data.get('confirm_password'):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        # Remove fields that shouldn't be passed to create_user
        validated_data.pop('confirm_password', None)
        phone = validated_data.pop('phone', None)
        role = validated_data.pop('role', 'user')
        email = validated_data.pop('email')
        password = validated_data.pop('password')

        # Create user with the specified role
        user = User.objects.create_user(
            email=email,
            password=password,
            role=role,
            phone=phone,  # Save phone on User model
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
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
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
        child=serializers.ChoiceField(choices=User.ROLE_CHOICES),
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
        from .vendor_serializers import VendorProfile
        from .courier_serializers import CourierProfile
        
        # Extract data
        email = validated_data['email']
        password = validated_data['password']
        roles = validated_data['roles']
        phone = validated_data['phone']
        first_name = validated_data['first_name']
        last_name = validated_data['last_name']
        
        # Check if user already exists
        try:
            user = User.objects.get(email=email)
            existing_roles = user.get_roles()
            
            # Check for role conflicts
            conflicting_roles = [role for role in roles if role in existing_roles]
            if conflicting_roles:
                raise serializers.ValidationError({
                    'roles': f"User already has the following roles: {', '.join(conflicting_roles)}. "
                            f"Available roles to add: {', '.join([r for r in roles if r not in existing_roles])}"
                })
            
            # Add new roles to existing user
            for role in roles:
                user.add_role(role)
                self._create_role_profile(user, role, validated_data)
            
        except User.DoesNotExist:
            # Create new user
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=roles[0]  # Set primary role (first in list)
            )
            
            # Add all roles
            for role in roles:
                user.add_role(role)
                self._create_role_profile(user, role, validated_data)
        
        return user

    def _create_role_profile(self, user, role, validated_data):
        """Create the appropriate profile for the role"""
        from .vendor_serializers import VendorProfile
        from .courier_serializers import CourierProfile
        
        if role == 'user':
            # Create UserProfile if it doesn't exist
            if not hasattr(user, 'profile'):
                UserProfile.objects.create(user=user, phone=validated_data['phone'])
        
        elif role == 'vendor':
            # Create VendorProfile if it doesn't exist
            if not hasattr(user, 'vendor_profile'):
                VendorProfile.objects.create(
                    user=user,
                    phone=validated_data['phone'],
                    business_name=validated_data['business_name'],
                    business_category=validated_data['business_category'],
                    business_address=validated_data['business_address'],
                    delivery_radius=validated_data.get('delivery_radius', 5),
                    service_areas=validated_data.get('service_areas', '')
                )
        
        elif role == 'courier':
            # Create CourierProfile if it doesn't exist
            if not hasattr(user, 'courier_profile'):
                CourierProfile.objects.create(
                    user=user,
                    phone=validated_data['phone'],
                    vehicle_type=validated_data['vehicle_type'],
                    license_number=validated_data['license_number'],
                    vehicle_registration=validated_data['vehicle_registration'],
                    availability_status=validated_data.get('availability_status', 'available')
                )
