import logging
from urllib.parse import urlencode

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from allauth.account.utils import user_username, user_email, user_field
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)
User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom social account adapter with enhanced OAuth handling"""
    
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just before a user is logged in via a social account.
        """
        logger.debug(f"Pre-social login for {sociallogin.account.provider}")
        
        # Ensure the user has an email
        if not sociallogin.email_addresses:
            logger.error("No email provided in social login")
            raise ImmediateHttpResponse(
                JsonResponse(
                    {'error': 'Email is required for registration'}, 
                    status=400
                )
            )
            
        # Check if a user with this email already exists
        email = sociallogin.email_addresses[0].email
        try:
            existing_user = User.objects.get(email=email)
            
            # If the user exists but isn't connected to this social account
            if not existing_user.socialaccount_set.filter(provider=sociallogin.account.provider).exists():
                logger.info(f"Connecting existing user {email} to {sociallogin.account.provider}")
                # Connect the social account to the existing user
                sociallogin.connect(request, existing_user)
                
        except User.DoesNotExist:
            logger.info(f"New social login for {email}")
        except Exception as e:
            logger.error(f"Error in pre_social_login: {str(e)}")
            raise

    def authentication_error(self, request, provider_id, error=None, exception=None, extra_context=None):
        """Handle authentication errors"""
        error_msg = str(exception) if exception else 'authentication_failed'
        logger.error(f"OAuth error with {provider_id}: {error_msg}")
        
        # Build redirect URL with error message
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        error_params = urlencode({
            'error': 'oauth_error',
            'message': error_msg
        })
        return redirect(f"{frontend_url}/login?{error_params}")

    def get_connect_redirect_url(self, request, socialaccount):
        """Where to redirect after successful social account connection"""
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        return f"{frontend_url}/profile/social-accounts"
        
    def populate_user(self, request, sociallogin, data):
        """
        Populates user information from social provider info.
        """
        # Get email from social login data or extra data
        email = data.get('email') or sociallogin.account.extra_data.get('email')
        if not email:
            logger.error("No email provided in social login data")
            raise ValidationError('Email is required')
            
        # Create or get user
        user = sociallogin.user
        user_email(user, email)
        
        # Set user details from provider data
        extra_data = sociallogin.account.extra_data
        
        # Handle name fields
        first_name = data.get('first_name') or extra_data.get('given_name') or ''
        last_name = data.get('last_name') or extra_data.get('family_name') or ''
        
        # If no first/last name, try to split full name
        if not first_name and not last_name:
            full_name = data.get('name') or extra_data.get('name', '')
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Set user fields
        user_field(user, 'first_name', first_name)
        user_field(user, 'last_name', last_name)
        
        # Set username to email if not set
        if not user_username(user):
            user_username(user, email.split('@')[0])
            
        # Mark as social signup
        user.is_social_signup = True
        user.social_provider = sociallogin.account.provider
        
        logger.info(f"Populated user data for {email}")
        return user
        
    def save_user(self, request, sociallogin, form=None):
        """Saves a newly signed up social login"""
        user = super().save_user(request, sociallogin, form)
        
        # Additional processing after user is saved
        logger.info(f"New social user created: {user.email}")
        
        # Send welcome email or perform other actions
        # self._send_welcome_email(user)
        
        return user
