from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.db import transaction
import os

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def create_admin_user(request):
    """
    Create an admin user (one-time setup endpoint)
    """
    # Check if any superuser already exists
    if User.objects.filter(is_superuser=True).exists():
        return Response({
            'message': 'Admin user already exists',
            'success': False
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get credentials from request or environment
    email = request.data.get('email', os.environ.get('ADMIN_EMAIL', 'admin@bestyy.com'))
    password = request.data.get('password', os.environ.get('ADMIN_PASSWORD', 'admin123456'))
    first_name = request.data.get('first_name', 'Admin')
    last_name = request.data.get('last_name', 'User')
    
    try:
        with transaction.atomic():
            # Create superuser
            user = User.objects.create_superuser(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            
            return Response({
                'message': 'Admin user created successfully',
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_superuser': user.is_superuser,
                    'is_staff': user.is_staff,
                }
            }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        return Response({
            'message': f'Error creating admin user: {str(e)}',
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def check_admin_exists(request):
    """
    Check if admin user exists
    """
    admin_exists = User.objects.filter(is_superuser=True).exists()
    
    return Response({
        'admin_exists': admin_exists,
        'message': 'Admin user exists' if admin_exists else 'No admin user found'
    }, status=status.HTTP_200_OK)
