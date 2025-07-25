from rest_framework import serializers
from django.contrib.auth.models import User
from .models import VendorProfile, CourierProfile, UserProfile, MenuItem, Order, Booking, Address, Favorite, Payment, SavedCard, Accommodation

class UserSerializer(serializers.ModelSerializer):
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
        error_messages={'required': 'Please enter your email address.', 'invalid': 'Enter a valid email address.'}
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        error_messages={'required': 'Please enter your password.'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        error_messages={'required': 'Please confirm your password.'}
    )
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'password', 'confirm_password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        # Password match
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        # Removed unique email validation to allow multi-role registration
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(
            username=validated_data.get('username', validated_data['email']),
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        return user

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
            'business_description', 'logo', 'business_address', 'delivery_radius', 
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
    opening_hours = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter your opening hours.'}
    )
    closing_hours = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter your closing hours.'}
    )
    class Meta:
        model = CourierProfile
        fields = '__all__'
        read_only_fields = ['user']

    def validate(self, data):
        phone = data.get('phone')
        if phone and CourierProfile.objects.filter(phone=phone).exists():
            raise serializers.ValidationError({"phone": "A courier with this phone number already exists."})
        return data

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
        if CourierProfile.objects.filter(user=user).exists():
            raise serializers.ValidationError({'user': 'A courier profile with this email already exists.'})
        courier_profile = CourierProfile.objects.create(user=user, **validated_data)
        return courier_profile

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

class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    vendor = VendorProfileSerializer(read_only=True)
    items = MenuItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'vendor', 'items', 'total_price', 'order_name', 'delivery_address', 'delivery_date', 'status', 'created_at'] 

class VendorOrderTrackingSerializer(serializers.ModelSerializer):
    dish_name = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    item = serializers.SerializerMethodField()
    total = serializers.DecimalField(source='total_price', max_digits=10, decimal_places=2)
    status = serializers.CharField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'username', 'dish_name', 'address', 'item', 'total', 'status']

    def get_dish_name(self, obj):
        # Assuming one item per order for simplicity
        return obj.items.first().dish_name if obj.items.exists() else None

    def get_address(self, obj):
        return obj.delivery_address

    def get_item(self, obj):
        # List all dish names in the order
        return [item.dish_name for item in obj.items.all()]

    def get_username(self, obj):
        return obj.user.get_full_name() or obj.user.username

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
    full_name = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter the full name.'}
    )
    phone_number = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter the phone number.'}
    )
    street_address = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter the street address.'}
    )
    city = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter the city.'}
    )
    state = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter the state.'}
    )
    postal_code = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter the postal code.'}
    )

    class Meta:
        model = Address
        fields = ['id', 'address_type', 'full_name', 'phone_number', 'street_address', 'city', 'state', 'postal_code', 'is_default', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
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