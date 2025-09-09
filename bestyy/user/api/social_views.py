import json
import logging
import secrets
import string
import time
from rest_framework.permissions import IsAuthenticated
from dj_rest_auth.registration.views import SocialLoginView, SocialConnectView
from allauth.account.views import LoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from urllib.parse import urlencode, unquote, urlparse

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from user.models import VendorProfile, CourierProfile
from user.serializers import VendorProfileSerializer, CourierProfileSerializer

from .social_serializers import SocialLoginSerializer, GoogleAuthSerializer

# Configure logger
logger = logging.getLogger(__name__)

class OAuthError(Exception):
    """Base exception for OAuth related errors"""
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class BaseOAuthHandler:
    """Base class for OAuth handlers with common functionality"""
    
    # These should be overridden by subclasses
    PROVIDER_NAME = None
    AUTHORIZATION_URL = None
    TOKEN_URL = None
    USER_INFO_URL = None
    
    def __init__(self, request):
        self.request = request
        self.redirect_uri = self._get_redirect_uri()
        self.state = self._generate_state()
        
    def _get_redirect_uri(self):
        """Get the OAuth callback URL"""
        # Use settings if available, otherwise construct from request
        if hasattr(settings, 'OAUTH_CALLBACK_URL'):
            return settings.OAUTH_CALLBACK_URL
        return f"{self.request.scheme}://{self.request.get_host()}/api/auth/social/callback/"
    
    def _generate_state(self):
        """Generate a secure random state parameter"""
        return secrets.token_urlsafe(32)
    
    def _get_client_info(self):
        """Get client ID and secret from settings"""
        try:
            provider_settings = settings.SOCIALACCOUNT_PROVIDERS.get(self.PROVIDER_NAME, {})
            if not provider_settings or 'APP' not in provider_settings:
                raise OAuthError(f"{self.PROVIDER_NAME} OAuth settings not found")
                
            client_id = provider_settings['APP'].get('client_id')
            client_secret = provider_settings['APP'].get('secret')
            
            if not client_id or not client_secret:
                raise OAuthError(f"{self.PROVIDER_NAME} OAuth client_id or secret not found")
                
            return client_id, client_secret
            
        except Exception as e:
            logger.error(f"Error getting {self.PROVIDER_NAME} OAuth settings: {str(e)}")
            raise OAuthError("Server configuration error")
    
    def get_authorization_url(self, **extra_params):
        """Generate the OAuth authorization URL"""
        client_id, _ = self._get_client_info()
        
        params = {
            'client_id': client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'state': self.state,
            'access_type': 'offline',
            'prompt': 'select_account',
            **extra_params
        }
        
        return f"{self.AUTHORIZATION_URL}?{urlencode(params)}"
    
    def exchange_code_for_token(self, code):
        """Exchange authorization code for access token"""
        client_id, client_secret = self._get_client_info()
        
        data = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        try:
            response = requests.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error exchanging code for token: {str(e)}")
            raise OAuthError("Failed to exchange authorization code for token")
    
    def get_user_info(self, access_token):
        """Get user info using access token"""
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(self.USER_INFO_URL, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting user info: {str(e)}")
            raise OAuthError("Failed to get user information")

class GoogleOAuthHandler(BaseOAuthHandler):
    """Google OAuth 2.0 handler"""
    PROVIDER_NAME = 'google'
    AUTHORIZATION_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    TOKEN_URL = 'https://oauth2.googleapis.com/token'
    USER_INFO_URL = 'https://www.googleapis.com/oauth2/v1/userinfo'
    
    def __init__(self, request):
        super().__init__(request)
        self.scope = 'openid email profile'
    
    def get_authorization_url(self, **extra_params):
        """Generate Google OAuth authorization URL with required scopes"""
        return super().get_authorization_url(
            scope=self.scope,
            **extra_params
        )

@method_decorator(csrf_exempt, name='dispatch')
class GoogleLogin(APIView):
    """
    Handle Google OAuth login flow
    
    This view handles both OAuth initiation and callback:
    - GET without code parameter: Returns the OAuth authorization URL
    - GET with code parameter: Handles the OAuth callback
    - POST: Handles OAuth flow for clients that prefer POST
    """
    permission_classes = [AllowAny]
    serializer_class = SocialLoginSerializer
    
    # Timeout for OAuth state parameter in seconds (10 minutes)
    STATE_CACHE_TIMEOUT = 600
    
    def _add_cors_headers(self, response):
        """Add CORS headers to the response"""
        response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS, POST'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRFToken, *'
        response['Access-Control-Allow-Credentials'] = 'true'
        return response
    
    def options(self, request, *args, **kwargs):
        """Handle OPTIONS request for CORS preflight"""
        response = JsonResponse({})
        return self._add_cors_headers(response)
    
    def _store_state_in_cache(self, state, redirect_uri):
        """Store OAuth state in cache for validation"""
        cache.set(f'oauth_state_{state}', redirect_uri, timeout=self.STATE_CACHE_TIMEOUT)
    
    def _validate_state(self, state):
        """Validate OAuth state parameter"""
        if not state:
            return False
        return cache.get(f'oauth_state_{state}') is not None
    
    def _get_google_settings(self):
        """Helper method to get Google OAuth settings"""
        google_settings = settings.SOCIALACCOUNT_PROVIDERS.get('google', {})
        if not google_settings or 'APP' not in google_settings:
            raise KeyError("Google OAuth settings not found in SOCIALACCOUNT_PROVIDERS")
        
        client_id = google_settings['APP'].get('client_id')
        client_secret = google_settings['APP'].get('secret')
        
        if not client_id or not client_secret:
            raise KeyError("Google OAuth client_id or secret not found in settings")
        
        logger.debug("Successfully retrieved Google OAuth settings")
        return client_id, client_secret
    
    def _handle_oauth_callback(self, request):
        """Handle OAuth callback with authorization code"""
        logger = logging.getLogger(__name__)
        logger.info("Handling OAuth callback from Google")
        
        # Get the authorization code and state from the request
        code = request.GET.get('code')
        state = request.GET.get('state', 'http://localhost:3000/login')
        
        if not code:
            logger.error("No authorization code provided in callback")
            return JsonResponse(
                {'error': 'No authorization code provided'}, 
                status=400
            )
        
        try:
            # Get Google OAuth settings
            client_id, client_secret = self._get_google_settings()
            
            # Exchange the authorization code for tokens
            token_url = 'https://oauth2.googleapis.com/token'
            callback_url = f"{request.scheme}://{request.get_host()}/api/auth/social/google/callback/"
            
            token_data = {
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': callback_url,
                'grant_type': 'authorization_code'
            }
            
            logger.debug("Exchanging code for tokens")
            token_response = requests.post(token_url, data=token_data)
            token_response.raise_for_status()
            
            tokens = token_response.json()
            logger.debug("Token exchange successful")
            
            # Get user info from Google
            user_info_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
            headers = {
                'Authorization': f"Bearer {tokens.get('access_token')}"
            }
            
            user_info_response = requests.get(user_info_url, headers=headers)
            user_info_response.raise_for_status()
            user_info = user_info_response.json()
            
            logger.info(f"Successfully authenticated user: {user_info.get('email')}")
            
            # Prepare response data
            response_data = {
                'user': user_info,
                'tokens': tokens,
                'redirect_uri': state  # The original frontend URL to redirect back to
            }
            
            # In a real implementation, you would create or authenticate the user here
            # and generate your own JWT tokens
            
            response = JsonResponse(response_data)
            return self._add_cors_headers(response)
            
        except Exception as e:
            logger.error(f"Error in OAuth callback: {str(e)}", exc_info=True)
            return JsonResponse(
                {'error': 'Failed to process OAuth callback'}, 
                status=500
            )
    
    def _handle_oauth_initiation(self, request):
        """Handle OAuth flow initiation"""
        logger = logging.getLogger(__name__)
        logger.info("Initiating Google OAuth flow")
        
        try:
            # Get Google OAuth settings
            client_id, _ = self._get_google_settings()
            
            # Generate a secure state parameter
            state = secrets.token_urlsafe(32)
            
            # Get the redirect_uri from the request or use default
            redirect_uri = request.GET.get('redirect_uri', 'http://localhost:3000/login')
            
            # Store the state and redirect_uri in cache for validation
            self._store_state_in_cache(state, redirect_uri)
            
            # Build the Google OAuth callback URL
            callback_uri = f"{request.scheme}://{request.get_host()}/api/auth/social/google/callback/"
            logger.debug(f"Using callback URL: {callback_uri}")
            
            # Build the authorization URL parameters
            params = {
                'client_id': client_id,
                'redirect_uri': callback_uri,
                'response_type': 'code',
                'scope': 'openid email profile',
                'access_type': 'offline',
                'prompt': 'select_account',
                'state': state
            }
            
            # Add any additional parameters from the request
            for key in ['login_hint', 'include_granted_scopes']:
                if key in request.GET:
                    value = request.GET[key]
                    if isinstance(value, list):
                        value = value[0]
                    params[key] = value
            
            # Build the authorization URL
            auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
            logger.debug("Generated auth URL")
            
            # Return the authorization URL to the frontend
            response_data = {
                'authorization_url': auth_url,
                'state': state
            }
            
            response = JsonResponse(response_data)
            return self._add_cors_headers(response)
            
        except Exception as e:
            logger.error(f"Error in OAuth initiation: {str(e)}", exc_info=True)
            error_response = JsonResponse(
                {'error': 'Failed to initiate OAuth flow'}, 
                status=500
            )
            return self._add_cors_headers(error_response)

    def post(self, request, *args, **kwargs):
        """Handle OAuth callback with authorization code"""
        code = request.data.get('code')
        if not code:
            return Response(
                {'error': 'Authorization code is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Create a serializer instance with the code
        serializer = self.serializer_class(data={'code': code})
        
        try:
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        except Exception as e:
            error_response = Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
            return self._add_cors_headers(error_response)

    def get(self, request, *args, **kwargs):
        """Initiate OAuth or handle callback based on query params"""
        # If Google redirected back with a code, handle callback
        if request.GET.get('code'):
            return self._handle_oauth_callback(request)
        # Otherwise, initiate and return auth URL
        return self._handle_oauth_initiation(request)


class GoogleSignup(APIView):
    """
    Handle Google OAuth signup
    """
    permission_classes = [AllowAny]
    serializer_class = GoogleAuthSerializer

    def post(self, request, *args, **kwargs):
        is_signup = 'signup' in request.path
        
        # Get client's IP and user agent for security logging
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        try:
            # Validate and process the request
            serializer = self.serializer_class(
                data=request.data,
                context={
                    'is_signup': is_signup,
                    'request': request
                }
            )
            serializer.is_valid(raise_exception=True)
            
            user = serializer.validated_data['user']
            role = serializer.validated_data['role']
            
            # Log successful authentication
            logger.info(
                f"Google OAuth {'signup' if is_signup else 'login'} successful",
                extra={
                    'user_id': user.id,
                    'email': user.email,
                    'role': role,
                    'ip': ip_address,
                    'user_agent': user_agent
                }
            )
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            # Set cookie with HttpOnly flag for better security
            response = Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': role,
                    'profile_complete': user.profile_complete,
                    'is_social_signup': user.is_social_signup
                }
            }, status=status.HTTP_201_CREATED if is_signup else status.HTTP_200_OK)
            
            # Set secure cookie for web clients
            if not settings.DEBUG:
                response.set_cookie(
                    'refresh_token',
                    str(refresh),
                    httponly=True,
                    secure=True,
                    samesite='Lax',
                    max_age=60 * 60 * 24 * 7  # 7 days
                )
                
            return response
            
        except Exception as e:
            # Log authentication failure
            logger.error(
                f"Google OAuth {'signup' if is_signup else 'login'} failed: {str(e)}",
                extra={
                    'ip': ip_address,
                    'user_agent': user_agent,
                    'error': str(e)
                }
            )
            raise
    
    def get_client_ip(self, request):
        """Get the client's IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CompleteProfile(APIView):
    """
    Complete profile after social signup
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        user = request.user
        role = request.data.get('role')
        
        if not role or role not in ['vendor', 'courier']:
            return Response(
                {'error': 'Invalid role. Must be either vendor or courier'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if role == 'vendor':
                profile = user.vendor_profile
                serializer = VendorProfileSerializer(profile, data=request.data, partial=True)
            else:
                profile = user.courier_profile
                serializer = CourierProfileSerializer(profile, data=request.data, partial=True)
            
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Save the profile
            serializer.save()
            
            # Mark profile as complete
            user.profile_complete = True
            user.save()
            
            return Response({
                'message': f'{role.capitalize()} profile completed successfully',
                'profile': serializer.data
            })
            
        except (VendorProfile.DoesNotExist, CourierProfile.DoesNotExist):
            return Response(
                {'error': f'{role.capitalize()} profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class GoogleConnect(SocialConnectView):
    """
    Connect Google OAuth to an existing account
    """
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = 'http://localhost:8000/auth/google/callback/'
    serializer_class = SocialLoginSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        # Only allow connecting if user is authenticated
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        response = super().post(request, *args, **kwargs)
        
        # Update user's social auth info
        if response.status_code == 200:
            user = request.user
            user.is_social_signup = True
            user.social_provider = 'google'
            user.save()
            
        return response
