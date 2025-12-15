"""
Views for vendor-related API endpoints.
"""
import logging
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.http import Http404
from ..permissions import IsVerifiedVendor

from ..models import VendorProfile
from ..serializers.vendor_serializers import (
    VendorProfileSerializer, 
    VendorRegistrationSerializer
)
from ..utils.websocket_notifications import (
    notify_vendor_registered,
    notify_vendor_approved,
    notify_vendor_rejected
)

logger = logging.getLogger(__name__)
User = get_user_model()

class VendorRegistrationView(generics.CreateAPIView):
    """
    Endpoint for new vendors to register.
    Creates both a user account and vendor profile in one step.
    No authentication required.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = VendorRegistrationSerializer
    parser_classes = [MultiPartParser, JSONParser]

    def create(self, request, *args, **kwargs):
        logger.info(f"Vendor registration request data: {request.data}")
        
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            logger.error(f"Vendor registration validation errors: {serializer.errors}")
            return Response(
                {"detail": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = serializer.save()

            # If serializer returned a PendingUser placeholder (registration flow), return profile_data
            # instead of trying to serialize it as a VendorProfile instance.
            if hasattr(result, 'profile_data') and hasattr(result, 'verification_code'):
                pending = result
                # Notify admins that a registration occurred (non-blocking)
                try:
                    notify_vendor_registered(pending)
                except Exception as e:
                    logger.error(f"Failed to send vendor registration notification: {str(e)}")

                headers = self.get_success_headers(serializer.data)
                # Flatten profile_data into the top-level response
                response_data = {
                    'success': True,
                    'status': 'pending',
                    'message': 'Registration received. Please verify your account.',
                    'verification_code': getattr(pending, 'verification_code', None)
                }
                if isinstance(pending.profile_data, dict):
                    response_data.update(pending.profile_data)
                else:
                    response_data['profile_data'] = pending.profile_data
                return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

            # Otherwise assume a VendorProfile was created and return serialized vendor profile
            vendor_profile = result
            try:
                notify_vendor_registered(vendor_profile)
            except Exception as e:
                logger.error(f"Failed to send vendor registration notification: {str(e)}")

            response_serializer = VendorProfileSerializer(vendor_profile)
            headers = self.get_success_headers(serializer.data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        except Exception as e:
            logger.error(f"Vendor registration failed: {str(e)}")
            return Response(
                {"detail": "An error occurred during registration. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VendorProfileView(generics.RetrieveUpdateAPIView):
    """
    Endpoint for vendors to view and update their profile.
    Requires vendor authentication and verification.
    Supports updating logo and cover images.
    """
    permission_classes = [permissions.IsAuthenticated, IsVerifiedVendor]
    serializer_class = VendorProfileSerializer
    parser_classes = [MultiPartParser, JSONParser]

    def get_object(self):
        # Get the vendor profile for the current user
        # The IsVerifiedVendor permission ensures the profile exists
        return self.request.user.vendor_profile

    def update(self, request, *args, **kwargs):
        """Override update to handle Cloudinary URLs and file uploads"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Check for bank-related fields that require verification
        bank_fields = ['bank_account_number', 'bank_code', 'bank_name', 'account_number', 'account_name']
        bank_fields_in_request = [field for field in bank_fields if field in request.data]

        if bank_fields_in_request:
            return Response({
                'success': False,
                'error': 'Bank details cannot be updated directly. Please use the bank verification endpoint: POST /api/user/verification/verify-bank/',
                'bank_verification_endpoint': '/api/user/verification/verify-bank/',
                'required_fields': ['account_number', 'account_name', 'bank_name'],
                'optional_fields': ['bank_code']
            }, status=status.HTTP_400_BAD_REQUEST)

        # Handle Cloudinary URLs (strings) and file uploads
        url_fields = ['logo', 'cover_image', 'cover_photo']
        for field_name in url_fields:
            if field_name in request.data:
                # If it's a string, treat it as Cloudinary URL
                value = request.data[field_name]
                if isinstance(value, str) and value.strip():
                    # Check if it's a Cloudinary URL - if so, store as string
                    if value.startswith('http') and 'cloudinary' in value:
                        setattr(instance, field_name, value)
                    else:
                        # For other strings, clear the field (set to None)
                        setattr(instance, field_name, None)
                elif hasattr(request.FILES, field_name):
                    # Handle file upload if present
                    setattr(instance, field_name, request.FILES[field_name])
                else:
                    # If no value provided, don't change the field
                    pass

        # Handle other data fields
        data_to_update = {}
        for field_name, value in request.data.items():
            if field_name not in url_fields:  # Skip URL/file fields already handled
                data_to_update[field_name] = value

        # Handle time fields specifically - convert empty strings to None
        time_fields = ['opening_hours', 'closing_hours']
        for field_name in time_fields:
            if field_name in data_to_update:
                value = data_to_update[field_name]
                if value == "" or value is None:
                    data_to_update[field_name] = None

        # Update other fields
        for field_name, value in data_to_update.items():
            if hasattr(instance, field_name):
                setattr(instance, field_name, value)

        instance.save()

        # Return updated data
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class VendorVerificationStatusView(APIView):
    """
    Endpoint for vendors to check their verification status.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        try:
            vendor_profile = request.user.vendor_profile
            return Response({
                'status': vendor_profile.verification_status,
                'verified': vendor_profile.verification_status == 'approved',
                'message': self._get_status_message(vendor_profile.verification_status),
                'notes': vendor_profile.verification_notes if vendor_profile.verification_status == 'rejected' else None
            })
        except VendorProfile.DoesNotExist:
            raise Http404("No vendor profile found for this user.")
    
    def _get_status_message(self, status):
        messages = {
            'pending': 'Your vendor application is under review.',
            'approved': 'Your vendor account has been approved!',
            'rejected': 'Your vendor application was rejected.'
        }
        return messages.get(status, 'Unknown status')
