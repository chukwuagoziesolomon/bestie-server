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
            vendor_profile = serializer.save()
            
            # Send WebSocket notification to admins
            try:
                notify_vendor_registered(vendor_profile)
            except Exception as e:
                logger.error(f"Failed to send vendor registration notification: {str(e)}")
            
            # Get the full serialized data including read-only fields
            response_serializer = VendorProfileSerializer(vendor_profile)
            
            headers = self.get_success_headers(serializer.data)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )
            
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
    """
    permission_classes = [permissions.IsAuthenticated, IsVerifiedVendor]
    serializer_class = VendorProfileSerializer
    parser_classes = [MultiPartParser, JSONParser]
    
    def get_object(self):
        # Get the vendor profile for the current user
        # The IsVerifiedVendor permission ensures the profile exists
        return self.request.user.vendor_profile


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
