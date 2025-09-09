from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from .models import User, VendorProfile, CourierProfile, UserProfile
from .serializers import VendorProfileSerializer, CourierProfileSerializer, UserProfileSerializer

class AssignRoleView(APIView):
    """
    API endpoint that allows users to assign a new role to their account.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        role = request.data.get('role')
        
        if not role or role not in dict(User.ROLE_CHOICES).keys():
            return Response(
                {'error': 'Invalid or missing role. Must be one of: user, vendor, courier'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If user already has this role, just return success
        if user.role == role:
            return Response({
                'message': f'User already has {role} role',
                'role': user.role
            })
        
        # Check if user already has a profile for this role
        if role == 'vendor' and hasattr(user, 'vendor_profile'):
            return Response(
                {'error': 'Vendor profile already exists for this user'},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif role == 'courier' and hasattr(user, 'courier_profile'):
            return Response(
                {'error': 'Courier profile already exists for this user'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update user role
        user.role = role
        user.save()
        
        # Create corresponding profile if needed
        profile_data = {}
        if role == 'vendor':
            profile = VendorProfile.objects.create(user=user)
            profile_serializer = VendorProfileSerializer(profile)
            profile_data = profile_serializer.data
        elif role == 'courier':
            profile = CourierProfile.objects.create(user=user)
            profile_serializer = CourierProfileSerializer(profile)
            profile_data = profile_serializer.data
        elif role == 'user' and not hasattr(user, 'profile'):
            profile = UserProfile.objects.create(user=user)
            profile_serializer = UserProfileSerializer(profile)
            profile_data = profile_serializer.data
        
        # Generate new token with updated user data
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'is_active': user.is_active,
                'profile': profile_data
            }
        })

class AvailableRolesView(APIView):
    """
    API endpoint that returns available roles and whether the user has them.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        roles = []
        
        for role_code, role_name in User.ROLE_CHOICES:
            has_role = (
                (role_code == 'user' and hasattr(user, 'profile')) or
                (role_code == 'vendor' and hasattr(user, 'vendor_profile')) or
                (role_code == 'courier' and hasattr(user, 'courier_profile'))
            )
            
            roles.append({
                'code': role_code,
                'name': role_name,
                'has_role': has_role,
                'is_current': user.role == role_code
            })
            
        return Response(roles)
