"""
Admin verification views for managing pending vendor and courier verifications.
"""
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.contrib.auth import get_user_model

from bestyy.core_features.user.models import VendorProfile, CourierProfile
from bestyy.core_features.user.serializers.vendor_serializers import VendorProfileSerializer
from bestyy.core_features.user.serializers.courier_serializers import CourierProfileSerializer

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
