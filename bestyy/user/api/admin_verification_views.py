"""
Admin verification views for managing pending vendor and courier verifications.
"""
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.contrib.auth import get_user_model

from user.models import VendorProfile, CourierProfile
from user.serializers import VendorProfileSerializer, CourierProfileSerializer

User = get_user_model()

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class PendingVerificationList(generics.ListAPIView):
    """
    List all pending vendor and courier verifications with search and pagination.
    """
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user_type = self.request.query_params.get('type', 'all')
        search_query = self.request.query_params.get('search', '').strip()
        
        # Base querysets
        vendor_queryset = VendorProfile.objects.filter(
            verification_status='pending'
        ).select_related('user')
        
        courier_queryset = CourierProfile.objects.filter(
            verification_status='pending'
        ).select_related('user')
        
        # Apply search if provided
        if search_query:
            vendor_queryset = vendor_queryset.filter(
                Q(business_name__icontains=search_query) |
                Q(user__email__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(cac_number__icontains=search_query)
            )
            
            courier_queryset = courier_queryset.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__email__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(nin_number__icontains=search_query)
            )
        
        # Return combined or filtered results based on type
        if user_type.lower() == 'vendor':
            return vendor_queryset
        elif user_type.lower() == 'courier':
            return courier_queryset
        else:
            # Return both querysets as a list to be processed by list()
            return list(vendor_queryset) + list(courier_queryset)
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Paginate the queryset
        page = self.paginate_queryset(queryset)
        if page is not None:
            # Determine the type of each item and serialize accordingly
            results = []
            for item in page:
                if hasattr(item, 'business_name'):  # It's a VendorProfile
                    serializer = VendorProfileSerializer(item, context={'request': request})
                    result = serializer.data
                    result['user_type'] = 'vendor'
                else:  # It's a CourierProfile
                    serializer = CourierProfileSerializer(item, context={'request': request})
                    result = serializer.data
                    result['user_type'] = 'courier'
                results.append(result)
            return self.get_paginated_response(results)
        
        # Fallback if not using pagination (shouldn't happen with default settings)
        vendor_serializer = VendorProfileSerializer(
            [v for v in queryset if hasattr(v, 'business_name')], 
            many=True,
            context={'request': request}
        )
        courier_serializer = CourierProfileSerializer(
            [c for c in queryset if not hasattr(c, 'business_name')], 
            many=True,
            context={'request': request}
        )
        
        results = [
            {**data, 'user_type': 'vendor'} for data in vendor_serializer.data
        ] + [
            {**data, 'user_type': 'courier'} for data in courier_serializer.data
        ]
        
        return Response(results)

class VerificationDocumentView(generics.RetrieveAPIView):
    """
    Get document URLs for a specific vendor or courier.
    """
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request, *args, **kwargs):
        user_type = kwargs.get('user_type')
        user_id = kwargs.get('user_id')
        
        try:
            if user_type.lower() == 'vendor':
                profile = VendorProfile.objects.get(id=user_id)
                documents = {
                    'cac_certificate': request.build_absolute_uri(profile.cac_certificate.url) if profile.cac_certificate else None,
                    'id_upload': request.build_absolute_uri(profile.id_upload.url) if profile.id_upload else None,
                    'proof_of_address': request.build_absolute_uri(profile.proof_of_address.url) if profile.proof_of_address else None,
                }
            elif user_type.lower() == 'courier':
                profile = CourierProfile.objects.get(id=user_id)
                documents = {
                    'id_upload': request.build_absolute_uri(profile.id_upload.url) if profile.id_upload else None,
                    'profile_photo': request.build_absolute_uri(profile.profile_photo.url) if profile.profile_photo else None,
                }
            else:
                return Response(
                    {"error": "Invalid user_type. Must be 'vendor' or 'courier'"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            return Response({
                'user_type': user_type,
                'user_id': user_id,
                'documents': documents
            })
            
        except (VendorProfile.DoesNotExist, CourierProfile.DoesNotExist):
            return Response(
                {"error": f"{user_type.capitalize()} profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )
