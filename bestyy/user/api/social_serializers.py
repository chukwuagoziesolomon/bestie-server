from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.conf import settings
import requests

User = get_user_model()

class SocialSignupSerializer(serializers.Serializer):
    """
    Serializer for social signup with Google OAuth
    """
    access_token = serializers.CharField(required=True)
    role = serializers.ChoiceField(choices=['vendor', 'courier'])
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        access_token = attrs.get('access_token')
        role = attrs.get('role')
        
        try:
            # Verify Google access token
            idinfo = self.verify_google_token(access_token)
            
            # Get or create user
            email = idinfo.get('email')
            if not email:
                raise serializers.ValidationError('Email is required')
                
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': idinfo.get('given_name', ''),
                    'last_name': idinfo.get('family_name', ''),
                    'is_social_signup': True,
                    'social_provider': 'google',
                    'social_uid': idinfo.get('sub')
                }
            )
            
            if created:
                user.set_unusable_password()
                user.save()
            
            attrs['user'] = user
            attrs['role'] = role
            return attrs
            
        except ValueError as e:
            raise serializers.ValidationError({'access_token': 'Invalid token'})
        except Exception as e:
            raise serializers.ValidationError(str(e))
    
    def verify_google_token(self, token):
        """Verify Google OAuth token and return user info"""
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests
            
            return id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.GOOGLE_OAUTH_CLIENT_ID
            )
        except Exception as e:
            raise ValueError(f'Token verification failed: {str(e)}')

class SocialLoginSerializer(serializers.Serializer):
    """
    Serializer for social login with Google OAuth
    """
    code = serializers.CharField(required=True)
    redirect_uri = serializers.CharField(required=False, default='postmessage')
    
    def validate(self, attrs):
        code = attrs.get('code')
        redirect_uri = attrs.get('redirect_uri')
        
        try:
            # Exchange authorization code for tokens
            token_url = 'https://oauth2.googleapis.com/token'
            data = {
                'code': code,
                'client_id': settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id'],
                'client_secret': settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['secret'],
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            }
            
            # Get access token
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            # Get user info
            user_info_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
            headers = {'Authorization': f'Bearer {token_data["access_token"]}'}
            response = requests.get(user_info_url, headers=headers)
            response.raise_for_status()
            user_info = response.json()
            
            # Get or create user
            email = user_info.get('email')
            if not email:
                raise serializers.ValidationError('Email is required')
                
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise serializers.ValidationError('User with this email does not exist. Please sign up first.')
            
            # Check if user is active
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Update last login
            user.save()
            
            return {
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_vendor': hasattr(user, 'vendor_profile'),
                    'is_courier': hasattr(user, 'courier_profile'),
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }
            
        except requests.exceptions.HTTPError as e:
            error_msg = f'Authentication failed: {str(e)}'
            try:
                error_data = e.response.json()
                error_msg = error_data.get('error_description', error_msg)
            except:
                pass
            raise serializers.ValidationError(error_msg)
        except Exception as e:
            raise serializers.ValidationError(f'Authentication error: {str(e)}')

class GoogleAuthSerializer(serializers.Serializer):
    """
    Serializer for Google OAuth authentication
    """
    access_token = serializers.CharField(required=True)
    id_token = serializers.CharField(required=False)
    role = serializers.ChoiceField(choices=['user', 'vendor', 'courier'], default='user')

    def validate(self, attrs):
        access_token = attrs.get('access_token')
        id_token = attrs.get('id_token')
        role = attrs.get('role', 'user')

        try:
            # Verify Google token
            idinfo = self.verify_google_token(access_token, id_token)
            
            email = idinfo.get('email')
            if not email:
                raise serializers.ValidationError('Email is required')

            # Prevent admin emails from using social login
            if email.endswith(('@admin.com', '@bestyyadmin.com')):
                raise serializers.ValidationError('Please use the admin login page')

            # Check if user exists
            try:
                user = User.objects.get(email=email)
                # Prevent admin users from using social login
                if user.is_staff or user.is_superuser:
                    raise serializers.ValidationError('Admin users must use the admin login')
                
                # Update user info if needed
                user.first_name = user.first_name or idinfo.get('given_name', '')
                user.last_name = user.last_name or idinfo.get('family_name', '')
                user.social_provider = 'google'
                user.social_uid = idinfo.get('sub')
                user.save()
                
                # Check if user has the requested role
                if role == 'vendor' and not hasattr(user, 'vendor_profile'):
                    VendorProfile.objects.create(user=user)
                elif role == 'courier' and not hasattr(user, 'courier_profile'):
                    CourierProfile.objects.create(user=user)
                    
            except User.DoesNotExist:
                # Create new user (non-admin)
                user = User.objects.create_user(
                    email=email,
                    first_name=idinfo.get('given_name', ''),
                    last_name=idinfo.get('family_name', ''),
                    social_provider='google',
                    social_uid=idinfo.get('sub'),
                    is_social_signup=True,
                    is_staff=False,
                    is_superuser=False,
                    profile_complete=role == 'user'  # Only mark as complete for regular users
                )
                
                # Create profile based on role
                if role == 'vendor':
                    VendorProfile.objects.create(user=user)
                elif role == 'courier':
                    CourierProfile.objects.create(user=user)
                else:  # Regular user
                    UserProfile.objects.create(user=user)
            
            attrs['user'] = user
            return attrs
            
        except ValueError as e:
            raise serializers.ValidationError({'token': str(e)})
            
    def verify_google_token(self, access_token, id_token):
        """Verify Google OAuth token and return user info"""
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests
            
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                access_token or id_token,
                requests.Request(),
                settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY  # Changed to use the correct setting
            )
            
            # Check token audience
            if idinfo['aud'] not in [settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY]:
                raise ValueError('Could not verify audience.')
                
            return idinfo
            
        except Exception as e:
            raise ValueError(f'Invalid token: {str(e)}')
