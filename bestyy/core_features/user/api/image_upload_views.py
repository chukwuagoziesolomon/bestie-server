"""
Profile photo and image upload endpoints for all user types
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404

from bestyy.core_features.user.models import User, VendorProfile, CourierProfile, UserProfile
from bestyy.core_features.user.permissions import IsVerifiedVendor
from utils.cloudinary_utils import upload_to_cloudinary


class UserProfileImageUpdateView(APIView):
    """
    Update regular user profile picture
    PATCH /api/user/profile/image/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def patch(self, request):
        """Update user profile picture"""
        try:
            user = request.user
            
            # Get or create user profile
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'phone': user.phone or ''}
            )

            # Handle profile picture upload
            if 'profile_picture' in request.FILES:
                try:
                    upload_response = upload_to_cloudinary(
                        request.FILES['profile_picture'],
                        folder=f"user_profiles/{user.id}",
                        resource_type='image'
                    )
                    profile.profile_picture = upload_response['secure_url']
                except Exception as e:
                    return Response({
                        'success': False,
                        'error': f'Failed to upload profile picture: {str(e)}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            elif 'profile_picture' in request.data and isinstance(request.data['profile_picture'], str):
                # Handle Cloudinary URL directly
                if request.data['profile_picture'].startswith('http'):
                    profile.profile_picture = request.data['profile_picture']
                else:
                    profile.profile_picture = None

            profile.save()

            return Response({
                'success': True,
                'message': 'Profile picture updated successfully',
                'profile_picture': profile.profile_picture
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VendorImageUpdateView(APIView):
    """
    Update vendor logo and cover images
    PATCH /api/user/vendors/images/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def patch(self, request):
        """Update vendor images"""
        try:
            if not hasattr(request.user, 'vendor_profile'):
                return Response({
                    'success': False,
                    'error': 'Vendor profile not found'
                }, status=status.HTTP_404_NOT_FOUND)

            vendor = request.user.vendor_profile

            # Handle logo upload
            if 'logo' in request.FILES:
                try:
                    upload_response = upload_to_cloudinary(
                        request.FILES['logo'],
                        folder=f"vendor_logos/{vendor.id}",
                        resource_type='image'
                    )
                    vendor.logo = upload_response['secure_url']
                except Exception as e:
                    return Response({
                        'success': False,
                        'error': f'Failed to upload logo: {str(e)}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            elif 'logo' in request.data and isinstance(request.data['logo'], str):
                if request.data['logo'].startswith('http'):
                    vendor.logo = request.data['logo']
                else:
                    vendor.logo = None

            # Handle cover image upload
            if 'cover_image' in request.FILES:
                try:
                    upload_response = upload_to_cloudinary(
                        request.FILES['cover_image'],
                        folder=f"vendor_covers/{vendor.id}",
                        resource_type='image'
                    )
                    vendor.cover_image = upload_response['secure_url']
                except Exception as e:
                    return Response({
                        'success': False,
                        'error': f'Failed to upload cover image: {str(e)}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            elif 'cover_image' in request.data and isinstance(request.data['cover_image'], str):
                if request.data['cover_image'].startswith('http'):
                    vendor.cover_image = request.data['cover_image']
                else:
                    vendor.cover_image = None

            vendor.save()

            return Response({
                'success': True,
                'message': 'Vendor images updated successfully',
                'images': {
                    'logo': vendor.logo,
                    'cover_image': vendor.cover_image,
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CourierImageUpdateView(APIView):
    """
    Update courier profile photo and ID upload
    PATCH /api/user/couriers/images/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def patch(self, request):
        """Update courier images"""
        try:
            if not hasattr(request.user, 'courier_profile'):
                return Response({
                    'success': False,
                    'error': 'Courier profile not found'
                }, status=status.HTTP_404_NOT_FOUND)

            courier = request.user.courier_profile

            # Handle profile photo upload
            if 'profile_photo' in request.FILES:
                try:
                    upload_response = upload_to_cloudinary(
                        request.FILES['profile_photo'],
                        folder=f"courier_photos/{courier.id}",
                        resource_type='image'
                    )
                    courier.profile_photo = upload_response['secure_url']
                except Exception as e:
                    return Response({
                        'success': False,
                        'error': f'Failed to upload profile photo: {str(e)}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            elif 'profile_photo' in request.data and isinstance(request.data['profile_photo'], str):
                if request.data['profile_photo'].startswith('http'):
                    courier.profile_photo = request.data['profile_photo']
                else:
                    courier.profile_photo = None

            # Handle ID upload
            if 'id_upload' in request.FILES:
                try:
                    upload_response = upload_to_cloudinary(
                        request.FILES['id_upload'],
                        folder=f"courier_ids/{courier.id}",
                        resource_type='image'
                    )
                    courier.id_upload = upload_response['secure_url']
                except Exception as e:
                    return Response({
                        'success': False,
                        'error': f'Failed to upload ID: {str(e)}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            elif 'id_upload' in request.data and isinstance(request.data['id_upload'], str):
                if request.data['id_upload'].startswith('http'):
                    courier.id_upload = request.data['id_upload']
                else:
                    courier.id_upload = None

            courier.save()

            return Response({
                'success': True,
                'message': 'Courier images updated successfully',
                'images': {
                    'profile_photo': courier.profile_photo,
                    'id_upload': courier.id_upload,
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UnifiedImageUpdateView(APIView):
    """
    Unified endpoint for updating any user type's images
    PATCH /api/user/images/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def patch(self, request):
        """Update images based on user role"""
        user = request.user
        response_data = {
            'success': True,
            'message': 'Images updated successfully',
            'images': {}
        }

        try:
            # Update regular user profile picture
            if 'profile_picture' in request.FILES or 'profile_picture' in request.data:
                profile, created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={'phone': user.phone or ''}
                )
                
                if 'profile_picture' in request.FILES:
                    upload_response = upload_to_cloudinary(
                        request.FILES['profile_picture'],
                        folder=f"user_profiles/{user.id}",
                        resource_type='image'
                    )
                    profile.profile_picture = upload_response['secure_url']
                elif isinstance(request.data.get('profile_picture'), str):
                    if request.data['profile_picture'].startswith('http'):
                        profile.profile_picture = request.data['profile_picture']
                    else:
                        profile.profile_picture = None
                
                profile.save()
                
                response_data['images']['profile_picture'] = profile.profile_picture

            # Update vendor images if user is a vendor
            if user.role == 'vendor' and hasattr(user, 'vendor_profile'):
                vendor = user.vendor_profile
                
                if 'logo' in request.FILES:
                    upload_response = upload_to_cloudinary(
                        request.FILES['logo'],
                        folder=f"vendor_logos/{vendor.id}",
                        resource_type='image'
                    )
                    vendor.logo = upload_response['secure_url']
                elif isinstance(request.data.get('logo'), str):
                    if request.data['logo'].startswith('http'):
                        vendor.logo = request.data['logo']
                    else:
                        vendor.logo = None
                
                if 'cover_image' in request.FILES:
                    upload_response = upload_to_cloudinary(
                        request.FILES['cover_image'],
                        folder=f"vendor_covers/{vendor.id}",
                        resource_type='image'
                    )
                    vendor.cover_image = upload_response['secure_url']
                elif isinstance(request.data.get('cover_image'), str):
                    if request.data['cover_image'].startswith('http'):
                        vendor.cover_image = request.data['cover_image']
                    else:
                        vendor.cover_image = None
                
                vendor.save()
                
                response_data['images'].update({
                    'logo': vendor.logo,
                    'cover_image': vendor.cover_image,
                })

            # Update courier images if user is a courier
            elif user.role == 'courier' and hasattr(user, 'courier_profile'):
                courier = user.courier_profile
                
                if 'profile_photo' in request.FILES:
                    upload_response = upload_to_cloudinary(
                        request.FILES['profile_photo'],
                        folder=f"courier_photos/{courier.id}",
                        resource_type='image'
                    )
                    courier.profile_photo = upload_response['secure_url']
                elif isinstance(request.data.get('profile_photo'), str):
                    if request.data['profile_photo'].startswith('http'):
                        courier.profile_photo = request.data['profile_photo']
                    else:
                        courier.profile_photo = None
                
                if 'id_upload' in request.FILES:
                    upload_response = upload_to_cloudinary(
                        request.FILES['id_upload'],
                        folder=f"courier_ids/{courier.id}",
                        resource_type='image'
                    )
                    courier.id_upload = upload_response['secure_url']
                elif isinstance(request.data.get('id_upload'), str):
                    if request.data['id_upload'].startswith('http'):
                        courier.id_upload = request.data['id_upload']
                    else:
                        courier.id_upload = None
                
                courier.save()
                
                response_data['images'].update({
                    'profile_photo': courier.profile_photo,
                    'id_upload': courier.id_upload,
                })

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)