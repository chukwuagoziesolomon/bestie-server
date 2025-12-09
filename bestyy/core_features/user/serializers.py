"""
Main serializers module. This file re-exports serializers from their respective modules.
"""
from .serializers.user_serializers import (
    UserSerializer,
    UserProfileSerializer,
    UserSignupSerializer,
)
from .serializers.vendor_serializers import (
    VendorProfileSerializer,
    VendorApplicationSerializer,
    VendorProfileMinimalSerializer,
)
from .serializers.courier_serializers import (
    CourierProfileSerializer,
    CourierSignupSerializer,
    CourierApplicationSerializer,
)
from .serializers.menu_serializers import MenuItemSerializer
from .models import Favorite, Payment, SavedCard, Address, Order, Booking, Accommodation

# Re-export the serializers
__all__ = [
    'UserSerializer',
    'UserProfileSerializer',
    'UserSignupSerializer',
    'VendorProfileSerializer',
    'VendorApplicationSerializer',
    'VendorProfileMinimalSerializer',
    'CourierProfileSerializer',
    'CourierSignupSerializer',
    'CourierApplicationSerializer',
    'MenuItemSerializer',
]

class MenuItemSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(
        required=True,
        error_messages={'required': 'Please upload a photo for this menu item.'}
    )
    dish_name = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter the item name.'}
    )
    item_description = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter the item description.'}
    )
    category = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter the category.'}
    )
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        error_messages={'required': 'Please enter the price.'}
    )
    quantity = serializers.IntegerField(
        required=True,
        error_messages={'required': 'Please enter the quantity.'}
    )

    class Meta:
        model = MenuItem
        fields = ['id', 'dish_name', 'item_description', 'price', 'category', 'quantity', 'image', 'available_now']
        read_only_fields = ['id']

class VendorApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorProfile
        exclude = ['user', 'verification_status'] # User is set automatically

class CourierApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourierProfile
        exclude = ['user', 'verification_status'] # User is set automatically

class VendorProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=True)

    class Meta:
        model = VendorProfile
        fields = [
            'id', 'user', 'phone', 'business_name', 'business_category', 'cac_number', 
            'business_description', 'logo', 'cover_image', 'business_address', 'delivery_radius', 
            'service_areas', 'opening_hours', 'closing_hours', 'offers_delivery', 
            'verification_status'
        ]
        read_only_fields = ['id', 'verification_status', 'user']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        email = user_data.get('email')
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': user_data.get('username', email),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', '')
            }
        )
        if created:
            user.set_password(user_data.get('password'))
            user.save()
        if VendorProfile.objects.filter(user=user).exists():
            raise serializers.ValidationError({'user': 'A vendor profile with this email already exists.'})
        vendor_profile = VendorProfile.objects.create(user=user, **validated_data)
        return vendor_profile

class CourierSignupSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True, write_only=True)
    last_name = serializers.CharField(required=True, write_only=True)
    email = serializers.EmailField(required=True, write_only=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    phone = serializers.CharField(required=True)
    address = serializers.CharField(required=True)
    service_areas = serializers.CharField(required=True)
    delivery_radius = serializers.CharField(required=True)
    opening_hours = serializers.TimeField(required=True)
    closing_hours = serializers.TimeField(required=True)
    has_bike = serializers.BooleanField(required=True)
    verification_preference = serializers.ChoiceField(
        choices=[('NIN', 'NIN'), ('DL', "Driver's License"), ('VC', "Voter's Card")],
        required=True
    )
    id_upload = serializers.ImageField(required=True)
    profile_photo = serializers.ImageField(required=True)
    agreed_to_terms = serializers.BooleanField(required=True)
    
    class Meta:
        model = CourierProfile
        fields = [
            'first_name', 'last_name', 'email', 'password', 'confirm_password',
            'phone', 'address', 'service_areas', 'delivery_radius',
            'opening_hours', 'closing_hours', 'has_bike', 'verification_preference',
            'id_upload', 'profile_photo', 'agreed_to_terms'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'confirm_password': {'write_only': True},
        }
    
    def validate(self, data):
        # Check if passwords match
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        
        # Check if email is already in use
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})
        
        # Check if phone is already in use
        if CourierProfile.objects.filter(phone=data['phone']).exists():
            raise serializers.ValidationError({"phone": "A courier with this phone number already exists."})
        
        # Check if terms are agreed to
        if not data.get('agreed_to_terms'):
            raise serializers.ValidationError({"agreed_to_terms": "You must agree to the terms and conditions."})
        
        return data
    
    def create(self, validated_data):
        # Remove confirm_password as it's not needed for user creation
        validated_data.pop('confirm_password', None)
        
        # Create user
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        
        # Create courier profile
        courier_profile = CourierProfile.objects.create(
            user=user,
            phone=validated_data['phone'],
            service_areas=validated_data['service_areas'],
            delivery_radius=validated_data['delivery_radius'],
            opening_hours=validated_data['opening_hours'],
            closing_hours=validated_data['closing_hours'],
            has_bike=validated_data['has_bike'],
            verification_preference=validated_data['verification_preference'],
            id_upload=validated_data['id_upload'],
            profile_photo=validated_data['profile_photo'],
            agreed_to_terms=validated_data['agreed_to_terms']
        )
        return courier_profile

class CourierProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=True)
    phone = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter your phone number.'}
    )
    service_areas = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter your service areas.'}
    )
    delivery_radius = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter your delivery radius.'}
    )
    opening_hours = serializers.TimeField(
        required=True,
        error_messages={'required': 'Please enter your opening hours.'},
        format='%I:%M %p'
    )
    closing_hours = serializers.TimeField(
        required=True,
        error_messages={'required': 'Please enter your closing hours.'},
        format='%I:%M %p'
    )
    id_upload = serializers.ImageField(read_only=True)
    profile_photo = serializers.ImageField(read_only=True)
    nin_number = serializers.CharField(read_only=True)
    verification_preference = serializers.CharField(read_only=True)
    has_bike = serializers.BooleanField(read_only=True)
    vehicle_type = serializers.CharField(read_only=True)
    verification_status = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %I:%M %p')
    
    class Meta:
        model = CourierProfile
        fields = [
            'id', 'user', 'phone', 'service_areas', 'delivery_radius',
            'opening_hours', 'closing_hours', 'has_bike', 'verification_preference',
            'nin_number', 'id_upload', 'profile_photo', 'vehicle_type',
            'verification_status', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        # Handle user data if present in the request
        user_data = data.pop('user', None)
        if user_data and isinstance(user_data, dict):
            # If user data is provided, validate it
            user_serializer = UserSerializer(data=user_data)
            if not user_serializer.is_valid():
                raise serializers.ValidationError({"user": user_serializer.errors})
            data['user'] = user_serializer.validated_data
        
        # Phone number validation
        phone = data.get('phone')
        if phone and (not phone.isdigit() or len(phone) < 10):
            raise serializers.ValidationError({"phone": "Please enter a valid phone number with at least 10 digits."})
        
        # Ensure opening hours are before closing hours if both are provided
        opening_hours = data.get('opening_hours')
        closing_hours = data.get('closing_hours')
        
        if opening_hours and closing_hours:
            if opening_hours >= closing_hours:
                raise serializers.ValidationError({
                    "opening_hours": "Opening hours must be before closing hours."
                })
        
        return data

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        email = user_data.get('email')
        
        # Check if user with this email already exists
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})
        
        # Create user
        user_serializer = UserSerializer(data=user_data)
        if not user_serializer.is_valid():
            raise serializers.ValidationError({"user": user_serializer.errors})
            
        user = user_serializer.save()
        
        # Create courier profile with verification_status defaulting to 'pending'
        courier_profile = CourierProfile.objects.create(
            user=user,
            verification_status='pending',
            **validated_data
        )
        return courier_profile
        
    def update(self, instance, validated_data):
        # Update user data if provided
        user_data = validated_data.pop('user', None)
        if user_data:
            user_serializer = UserSerializer(
                instance.user, 
                data=user_data, 
                partial=True
            )
            if not user_serializer.is_valid():
                raise serializers.ValidationError({"user": user_serializer.errors})
            user_serializer.save()
        
        # Update courier profile
        for attr, value in validated_data.items():
            # Don't allow updating verification_status through this endpoint
            if attr != 'verification_status':
                setattr(instance, attr, value)
                
        instance.save()
        return instance

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'phone', 'address', 'nick_name', 'language', 'profile_picture', 'email_notifications', 'push_notifications']
        read_only_fields = ['user']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        email = user_data.get('email')
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': user_data.get('username', email),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', '')
            }
        )
        if created:
            user.set_password(user_data.get('password'))
            user.save()
        if UserProfile.objects.filter(user=user).exists():
            raise serializers.ValidationError({'user': 'A user profile with this email already exists.'})
        user_profile = UserProfile.objects.create(user=user, **validated_data)
        return user_profile

class UserSignupSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=True)
    phone = serializers.CharField(required=True)

    class Meta:
        model = UserProfile
        fields = ['user', 'phone']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        phone_number = validated_data.pop('phone')
        email = user_data.get('email')
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': user_data.get('username', email),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', '')
            }
        )
        if created:
            user.set_password(user_data.get('password'))
            user.save()
        if UserProfile.objects.filter(user=user).exists():
            raise serializers.ValidationError({'user': 'A user profile with this email already exists.'})
        user_profile = UserProfile.objects.create(user=user, phone=phone_number, **validated_data)
        return user_profile 

# Order serializers moved to user/serializers/order_serializers.py 

# VendorOrderTrackingSerializer moved to user/serializers/order_serializers.py

class AccommodationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Accommodation
        fields = [
            'id', 'name', 'accommodation_type', 'description', 'address', 'city', 'state', 
            'photos', 'logo', 'phone', 'email', 'website', 'rating', 
            'price_range', 'amenities', 'is_active', 'created_at', 'updated_at'
        ]

class BookingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    accommodation = AccommodationSerializer(read_only=True)
    accommodation_logo = serializers.SerializerMethodField()
    accommodation_photos = serializers.SerializerMethodField()
    accommodation_name = serializers.SerializerMethodField()
    accommodation_address = serializers.SerializerMethodField()
    accommodation_city = serializers.SerializerMethodField()
    accommodation_rating = serializers.SerializerMethodField()
    accommodation_price_range = serializers.SerializerMethodField()
    accommodation_type = serializers.SerializerMethodField()
    is_upcoming = serializers.SerializerMethodField()
    is_past = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'user', 'accommodation', 'accommodation_logo', 'accommodation_photos', 'accommodation_name',
            'accommodation_address', 'accommodation_city', 'accommodation_rating', 'accommodation_price_range',
            'accommodation_type', 'booking_date', 'booking_time', 'number_of_people', 'room_type',
            'special_requests', 'status', 'created_at', 'updated_at', 
            'is_upcoming', 'is_past'
        ]

    def get_accommodation_logo(self, obj):
        if obj.accommodation and obj.accommodation.logo:
            return obj.accommodation.logo.url
        return None

    def get_accommodation_photos(self, obj):
        if obj.accommodation and obj.accommodation.photos:
            return obj.accommodation.photos.url
        return None

    def get_accommodation_name(self, obj):
        return obj.accommodation.name if obj.accommodation else None

    def get_accommodation_address(self, obj):
        return obj.accommodation.address if obj.accommodation else None

    def get_accommodation_city(self, obj):
        return obj.accommodation.city if obj.accommodation else None

    def get_accommodation_rating(self, obj):
        return obj.accommodation.rating if obj.accommodation else None

    def get_accommodation_price_range(self, obj):
        return obj.accommodation.price_range if obj.accommodation else None

    def get_accommodation_type(self, obj):
        return obj.accommodation.accommodation_type if obj.accommodation else None

    def get_is_upcoming(self, obj):
        from datetime import date
        return obj.booking_date >= date.today()

    def get_is_past(self, obj):
        from datetime import date
        return obj.booking_date < date.today()

class AddressSerializer(serializers.ModelSerializer):
    address_type = serializers.ChoiceField(
        choices=Address.ADDRESS_TYPES,
        error_messages={'required': 'Please select an address type.'}
    )
    address = serializers.CharField(
        source='street_address',
        required=True,
        error_messages={'required': 'Please enter the address.'}
    )
    city = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter the city.'}
    )
    state = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter the state.'}
    )
    zip_code = serializers.CharField(
        source='postal_code',
        required=True,
        error_messages={'required': 'Please enter the zip code.'}
    )
    is_default = serializers.BooleanField(
        default=False,
        required=False
    )

    class Meta:
        model = Address
        fields = ['id', 'address_type', 'address', 'city', 'state', 'zip_code', 'is_default', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        # Set default values for required fields that are not in the simplified payload
        validated_data['full_name'] = self.context['request'].user.get_full_name() or self.context['request'].user.username
        validated_data['phone_number'] = getattr(self.context['request'].user.profile, 'phone', '')
        return super().create(validated_data) 

class FavoriteSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    food_item = MenuItemSerializer(read_only=True)
    vendor = VendorProfileSerializer(read_only=True)
    favorite_type = serializers.ChoiceField(
        choices=Favorite.FAVORITE_TYPES,
        error_messages={'required': 'Please select a favorite type.'}
    )

    class Meta:
        model = Favorite
        fields = ['id', 'user', 'favorite_type', 'food_item', 'vendor', 'created_at']
        read_only_fields = ['created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def validate(self, data):
        favorite_type = data.get('favorite_type')
        food_item = data.get('food_item')
        vendor = data.get('vendor')

        if favorite_type == 'food' and not food_item:
            raise serializers.ValidationError({'food_item': 'Food item is required for food favorites.'})
        elif favorite_type == 'venue' and not vendor:
            raise serializers.ValidationError({'vendor': 'Vendor is required for venue favorites.'})
        
        if food_item and vendor:
            raise serializers.ValidationError('Cannot have both food item and vendor in the same favorite.')

        return data 

class PaymentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2,
        error_messages={'required': 'Please enter the payment amount.'}
    )
    payment_method = serializers.ChoiceField(
        choices=Payment.PAYMENT_METHODS,
        error_messages={'required': 'Please select a payment method.'}
    )
    description = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter a payment description.'}
    )

    class Meta:
        model = Payment
        fields = ['id', 'user', 'amount', 'currency', 'payment_method', 'paystack_reference', 'paystack_transaction_id', 'status', 'description', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['user', 'paystack_reference', 'paystack_transaction_id', 'status', 'metadata', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        # Generate unique reference (you can customize this)
        import uuid
        validated_data['paystack_reference'] = f"BESTYY_{uuid.uuid4().hex[:16].upper()}"
        return super().create(validated_data)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than zero.")
        return value

class SavedCardSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    card_type = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter the card type.'}
    )
    last_four_digits = serializers.CharField(
        required=True,
        max_length=4,
        min_length=4,
        error_messages={
            'required': 'Please enter the last four digits.',
            'min_length': 'Last four digits must be exactly 4 characters.',
            'max_length': 'Last four digits must be exactly 4 characters.'
        }
    )
    expiry_month = serializers.CharField(
        required=True,
        max_length=2,
        min_length=2,
        error_messages={
            'required': 'Please enter the expiry month.',
            'min_length': 'Expiry month must be exactly 2 characters.',
            'max_length': 'Expiry month must be exactly 2 characters.'
        }
    )
    expiry_year = serializers.CharField(
        required=True,
        max_length=4,
        min_length=4,
        error_messages={
            'required': 'Please enter the expiry year.',
            'min_length': 'Expiry year must be exactly 4 characters.',
            'max_length': 'Expiry year must be exactly 4 characters.'
        }
    )
    paystack_authorization_code = serializers.CharField(
        required=True,
        error_messages={'required': 'Please provide the Paystack authorization code.'}
    )

    class Meta:
        model = SavedCard
        fields = ['id', 'user', 'card_type', 'last_four_digits', 'expiry_month', 'expiry_year', 'paystack_authorization_code', 'is_default', 'created_at']
        read_only_fields = ['user', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def validate_expiry_month(self, value):
        try:
            month = int(value)
            if month < 1 or month > 12:
                raise serializers.ValidationError("Expiry month must be between 01 and 12.")
        except ValueError:
            raise serializers.ValidationError("Expiry month must be a valid number.")
        return value

    def validate_expiry_year(self, value):
        try:
            year = int(value)
            if year < 2024:  # Adjust as needed
                raise serializers.ValidationError("Card has expired.")
        except ValueError:
            raise serializers.ValidationError("Expiry year must be a valid number.")
        return value 

class VendorProfileMinimalSerializer(serializers.ModelSerializer):
    language = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    nick_name = serializers.SerializerMethodField()

    class Meta:
        model = VendorProfile
        fields = ['business_name', 'language', 'email', 'nick_name']

    def get_language(self, obj):
        # Try to get language from UserProfile if exists
        try:
            return obj.user.profile.language
        except Exception:
            return None

    def get_email(self, obj):
        return obj.user.email

    def get_nick_name(self, obj):
        try:
            return obj.user.profile.nick_name
        except Exception:
            return None 