"""
Test views for Cloudinary upload functionality.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from utils.cloudinary_utils import upload_to_cloudinary
import cloudinary
import cloudinary.api


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_cloudinary_config(request):
    """
    Test Cloudinary configuration and check if upload preset exists.
    """
    try:
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY['cloud_name'],
            api_key=settings.CLOUDINARY['api_key'],
            api_secret=settings.CLOUDINARY['api_secret']
        )
        
        # Check if upload preset exists
        upload_preset = settings.CLOUDINARY.get('upload_preset', 'bestyy_upload_preset')
        preset_exists = False
        preset_details = None
        
        try:
            preset_details = cloudinary.api.upload_preset(upload_preset)
            preset_exists = True
        except cloudinary.api.NotFound:
            preset_exists = False
        
        return Response({
            'cloudinary_configured': bool(settings.CLOUDINARY['cloud_name']),
            'upload_preset_name': upload_preset,
            'upload_preset_exists': preset_exists,
            'preset_details': preset_details,
            'cloud_name': settings.CLOUDINARY['cloud_name'],
            'api_key_configured': bool(settings.CLOUDINARY['api_key']),
            'api_secret_configured': bool(settings.CLOUDINARY['api_secret']),
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': str(e),
            'cloudinary_configured': False,
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_cloudinary_upload(request):
    """
    Test Cloudinary upload functionality.
    """
    try:
        if 'file' not in request.FILES:
            return Response({
                'error': 'No file provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        folder = request.data.get('folder', 'test_uploads')
        
        # Upload to Cloudinary
        response = upload_to_cloudinary(
            file=file,
            folder=folder,
            resource_type='image'
        )
        
        return Response({
            'success': True,
            'upload_response': response,
            'url': response.get('secure_url'),
            'public_id': response.get('public_id'),
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': str(e),
            'success': False,
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
