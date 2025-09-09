"""
Serializers for courier-related API endpoints.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from user.models import CourierProfile


class CourierListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing couriers with essential information.
    Includes profile image, name, contact info, verification status, and suspension status.
    """
    id = serializers.IntegerField(read_only=True)  # Courier Profile ID (correct for suspension endpoints)
    user_id = serializers.IntegerField(source='user.id', read_only=True)  # User ID
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email')
    phone = serializers.CharField()
    profile_image = serializers.ImageField(source='profile_photo')
    verification_status = serializers.CharField()
    is_active = serializers.BooleanField()
    joined_date = serializers.DateTimeField(source='created_at', format='%Y-%m-%d')
    vehicle_type = serializers.CharField()
    
    # Suspension status fields
    is_suspended = serializers.BooleanField(read_only=True)
    suspension_reason = serializers.CharField(read_only=True)
    suspension_date = serializers.DateTimeField(read_only=True)
    suspension_duration_days = serializers.IntegerField(read_only=True)
    activation_date = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = CourierProfile
        fields = [
            'id', 'user_id', 'name', 'email', 'phone', 'profile_image', 
            'verification_status', 'is_active', 'joined_date', 'vehicle_type',
            'is_suspended', 'suspension_reason', 'suspension_date', 
            'suspension_duration_days', 'activation_date'
        ]
    
    def get_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"


class CourierProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed courier profile information.
    Includes all fields from the CourierProfile model plus related user information and suspension status.
    """
    id = serializers.IntegerField(read_only=True)  # Courier Profile ID (correct for suspension endpoints)
    user_id = serializers.IntegerField(source='user.id', read_only=True)  # User ID
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    date_joined = serializers.DateTimeField(source='user.date_joined', read_only=True)
    
    # Suspension status fields
    is_suspended = serializers.BooleanField(read_only=True)
    suspension_reason = serializers.CharField(read_only=True)
    suspension_date = serializers.DateTimeField(read_only=True)
    suspension_duration_days = serializers.IntegerField(read_only=True)
    activation_date = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = CourierProfile
        fields = [
            'id', 'user_id', 'email', 'first_name', 'last_name', 'phone', 
            'service_areas', 'delivery_radius', 'opening_hours', 
            'closing_hours', 'has_bike', 'verification_preference',
            'nin_number', 'id_upload', 'profile_photo', 'agreed_to_terms',
            'vehicle_type', 'verification_status', 'is_active', 'date_joined',
            'is_suspended', 'suspension_reason', 'suspension_date', 
            'suspension_duration_days', 'activation_date'
        ]
        read_only_fields = ['verification_status', 'created_at', 'updated_at']
    
    def update(self, instance, validated_data):
        # Handle nested user data
        user_data = validated_data.pop('user', {})
        user = instance.user
        
        # Update user fields
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()
        
        # Update profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance


class CourierRegistrationSerializer(serializers.Serializer):
    """
    Serializer to register a new courier. Creates both User and CourierProfile.
    """
    # User fields
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)

    # Courier profile fields
    phone = serializers.CharField(max_length=16)
    service_areas = serializers.CharField(max_length=255)
    delivery_radius = serializers.CharField(max_length=50)
    opening_hours = serializers.TimeField()
    closing_hours = serializers.TimeField()
    has_bike = serializers.BooleanField(required=False, default=False)
    verification_preference = serializers.ChoiceField(choices=[('NIN', 'NIN'), ('DL', "Driver's License"), ('VC', "Voter's Card")])
    nin_number = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    vehicle_type = serializers.ChoiceField(choices=[('bike', 'Bike'), ('car', 'Car'), ('van', 'Van'), ('other', 'Other')], required=False, allow_null=True)
    agreed_to_terms = serializers.BooleanField()

    # File uploads
    id_upload = serializers.ImageField(required=False, allow_null=True)
    profile_photo = serializers.ImageField(required=False, allow_null=True)

    def validate_email(self, value):
        User = get_user_model()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate_email(self, value):
        User = get_user_model()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate_agreed_to_terms(self, value):
        if not value:
            raise serializers.ValidationError('You must agree to the terms to register as a courier.')
        return value

    def create(self, validated_data):
        User = get_user_model()
        # Extract user fields
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')

        # Create user with courier role
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role='courier',  # Set role to courier
        )

        # Create courier profile with remaining fields
        courier_profile = CourierProfile.objects.create(user=user, **validated_data)
        # verification_status defaults to 'pending' per model
        return courier_profile
