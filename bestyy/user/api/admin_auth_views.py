"""
Admin authentication views for the Bestyy admin panel.
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()
logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class AdminLoginView(APIView):
    """
    Custom admin login view that works with JWT authentication.
    This is needed because the default Django admin login doesn't work well with JWT.
    """
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response(
                {'error': 'Please provide both email and password'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Authenticate user
        user = authenticate(request, email=email, password=password)
        
        if user is None:
            return Response(
                {'error': 'Invalid credentials'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check if user is superuser (only superusers can access admin panel)
        if not user.is_superuser:
            return Response(
                {'error': 'Only superusers can access the admin panel'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Log the user in (creates session)
        login(request, user)
        
        # Generate JWT token
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            }
        }, status=status.HTTP_200_OK)


class AdminLogoutView(APIView):
    """
    Handles admin logout by clearing the session.
    """
    def post(self, request, *args, **kwargs):
        # Logout the user (clears the session)
        from django.contrib.auth import logout
        logout(request)
        return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
