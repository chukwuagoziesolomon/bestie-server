from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from allauth.account import app_settings as allauth_settings
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
from allauth.utils import get_username_max_length

User = get_user_model()

class CustomRegisterSerializer(serializers.Serializer):
    """Custom registration serializer that works with email-only authentication"""
    email = serializers.EmailField(required=allauth_settings.EMAIL_REQUIRED)
    first_name = serializers.CharField(required=True, write_only=True)
    last_name = serializers.CharField(required=True, write_only=True)
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(
        choices=User.ROLE_CHOICES,
        required=True,
        write_only=True,
        help_text="User role: 'user', 'vendor', or 'courier'"
    )

    def validate_email(self, email):
        email = get_adapter().clean_email(email)
        if allauth_settings.UNIQUE_EMAIL:
            if User.objects.filter(email=email).exists():
                raise serializers.ValidationError("A user is already registered with this email address.")
        return email

    def validate_password1(self, password):
        return get_adapter().clean_password(password)

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError("The two password fields didn't match.")
        return data

    def get_cleaned_data(self):
        return {
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
            'email': self.validated_data.get('email', ''),
            'password1': self.validated_data.get('password1', ''),
        }

    def validate(self, data):
        data = super().validate(data)
        email = data.get('email')
        role = data.get('role')
        
        # Check if user already has this role
        if User.objects.filter(email=email, role=role).exists():
            raise serializers.ValidationError({
                'error': f'User with this email is already registered as a {role}.'
            })
            
        return data
        
    def save(self, request):
        adapter = get_adapter()
        user = User(
            email=self.validated_data['email'],
            first_name=self.validated_data['first_name'],
            last_name=self.validated_data['last_name'],
            role=self.validated_data['role']
        )
        user.set_password(self.validated_data['password1'])
        user.save()
        setup_user_email(request, user, [])
        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        refresh = self.get_token(self.user)
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role,
            'is_active': self.user.is_active,
            'is_staff': self.user.is_staff,
            'is_superuser': self.user.is_superuser,
            'profile_complete': getattr(self.user, 'profile_complete', False),
            'is_social_signup': getattr(self.user, 'is_social_signup', False),
            'social_provider': getattr(self.user, 'social_provider', None),
        }
        return data

class CustomUserDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser', 
                 'profile_complete', 'is_social_signup', 'social_provider')
        read_only_fields = ('is_active', 'is_staff', 'is_superuser', 'profile_complete', 
                          'is_social_signup', 'social_provider')


    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError({"password2": "The two password fields didn't match."})
        
        try:
            validate_password(data['password1'], self.context['request'].user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password1': list(e.messages)})
            
        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password1']
        )
        return user

class CustomLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(style={'input_type': 'password'})

class CustomTokenSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = CustomUserDetailsSerializer()
