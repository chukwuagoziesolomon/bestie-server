from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import User

def social_login_test(request):
    """View to test social login functionality"""
    return render(request, 'social_login.html')

def test_cloudinary(request):
    """Test view to verify Cloudinary configuration"""
    config = {
        'is_configured': all([
            hasattr(settings, 'CLOUDINARY_CLOUD_NAME'),
            hasattr(settings, 'CLOUDINARY_API_KEY'),
            hasattr(settings, 'CLOUDINARY_API_SECRET')
        ]),
        'cloud_name': getattr(settings, 'CLOUDINARY_CLOUD_NAME', 'Not configured'),
        'storage_backend': settings.DEFAULT_FILE_STORAGE,
        'media_url': settings.MEDIA_URL,
        'media_root': str(settings.MEDIA_ROOT)
    }
    return JsonResponse(config)

def test_menu_image_upload(request):
    """Test endpoint to verify menu image upload functionality."""
    from django.conf import settings
    from ..utils.cloudinary_menu_utils import get_menu_image_transformations
    
    if request.method == 'POST':
        # Test image upload
        if 'image' in request.FILES:
            try:
                from ..utils.cloudinary_menu_utils import upload_menu_image
                file = request.FILES['image']
                response = upload_menu_image(file, vendor_id=1, folder='test_menu')
                return JsonResponse({
                    'success': True,
                    'upload_response': response,
                    'image_url': response.get('secure_url'),
                    'public_id': response.get('public_id')
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })
        else:
            return JsonResponse({
                'success': False,
                'error': 'No image file provided'
            })
    else:
        # Return available transformations
        return JsonResponse({
            'cloudinary_configured': hasattr(settings, 'DEFAULT_FILE_STORAGE') and 'cloudinary' in settings.DEFAULT_FILE_STORAGE,
            'available_transformations': get_menu_image_transformations(),
            'usage': 'POST an image file to test upload functionality'
        })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_auth(request):
    """Test endpoint to verify authentication is working"""
    user = request.user
    return Response({
        'message': 'Authentication successful!',
        'user': {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'is_social_signup': getattr(user, 'is_social_signup', False),
            'social_provider': getattr(user, 'social_provider', None)
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_vendor_auth(request):
    """Test endpoint specifically for vendor authentication"""
    user = request.user
    
    if not hasattr(user, 'vendor_profile'):
        return Response({
            'authenticated': True,
            'is_vendor': False,
            'error': 'User does not have a vendor profile',
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role
            }
        }, status=403)
    
    vendor = user.vendor_profile
    return Response({
        'authenticated': True,
        'is_vendor': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'role': user.role
        },
        'vendor': {
            'id': vendor.id,
            'business_name': vendor.business_name,
            'verification_status': vendor.verification_status
        }
    })

@api_view(['GET'])
def google_login_test(request):
    """Test endpoint to verify Google OAuth is configured"""
    return Response({
        'google_oauth_configured': bool(settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY),
        'client_id': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
        'auth_url': '/api/auth/social/google/login/',
        'signup_url': '/api/auth/social/google/signup/'
    })
