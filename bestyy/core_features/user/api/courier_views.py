"""
API endpoints for managing courier users.
Includes public registration and admin-only management endpoints.
"""
import logging
from rest_framework import generics, status, permissions, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser as DRFIsAdminUser
from rest_framework.parsers import MultiPartParser, JSONParser
from django.conf import settings
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Case, When, IntegerField, Avg, Value, FloatField

# Use absolute imports to avoid relative import issues
from bestyy.core_features.user.models import CourierProfile
from bestyy.restaurant_features.order.models import Order
from bestyy.core_features.user.serializers.courier_serializers import (
    CourierListSerializer,
    CourierProfileSerializer,
    CourierRegistrationSerializer,
)

logger = logging.getLogger(__name__)


class CourierListView(generics.ListAPIView):
    """
    API endpoint to list all couriers with their details.
    
    Returns:
    - id: Courier profile ID
    - name: Full name of the courier
    - email: Email address
    - phone: Phone number
    - profile_image: URL to the courier's profile image
    - completed_deliveries: Number of completed deliveries
    - rating: Average rating (1-5)
    - verification_status: Current verification status (pending/verified/rejected)
    - is_active: Boolean indicating if the courier is active
    - joined_date: Date when the courier joined
    
    Query Parameters:
    - search: Search by name, email, or phone number
    - verification_status: Filter by verification status (pending, verified, rejected)
    - user__is_active: Filter by active status (true/false)
    - user__date_joined__date__gte: Filter by join date (greater than or equal to)
    - user__date_joined__date__lte: Filter by join date (less than or equal to)
    - ordering: Order by any field (prefix with - for descending)
    """
    permission_classes = [permissions.IsAuthenticated, DRFIsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    
    # Disable browsable API filter form
    filter_fields = None
    search_fields = [
        'user__first_name', 
        'user__last_name', 
        'user__email', 
        'phone',
        'nin_number'
    ]
    filterset_fields = {
        'verification_status': ['exact', 'in'],
        'user__is_active': ['exact'],
        'user__date_joined': ['date__gte', 'date__lte', 'date__range'],
    }
    ordering_fields = [
        'user__date_joined', 'user__first_name', 
        'user__last_name', 'completed_deliveries', 'rating'
    ]
    ordering = ['-user__date_joined']

    def get_queryset(self):
        # Start with base queryset
        queryset = CourierProfile.objects.select_related('user')
        
        # Check if the Order model has a foreign key to CourierProfile
        try:
            from django.apps import apps
            order_model = apps.get_model('user', 'Order')
            if hasattr(order_model, 'courier'):
                # If Order has a courier ForeignKey to CourierProfile
                queryset = queryset.annotate(
                    completed_deliveries=Count(
                        Case(
                            When(order__status='delivered', then=1),
                            output_field=IntegerField(),
                        )
                    )
                )
            elif hasattr(order_model, 'courier_profile'):
                # If Order has a courier_profile ForeignKey to CourierProfile
                queryset = queryset.annotate(
                    completed_deliveries=Count(
                        Case(
                            When(order__status='delivered', then=1),
                            output_field=IntegerField(),
                        )
                    )
                )
            else:
                # Default to 0 if no order relationship exists
                queryset = queryset.annotate(
                    completed_deliveries=Value(0, output_field=IntegerField())
                )
        except Exception as e:
            logger.warning(f"Could not set up completed_deliveries annotation: {str(e)}")
            queryset = queryset.annotate(
                completed_deliveries=Value(0, output_field=IntegerField())
            )
        
        # Add default rating annotation (0.0) since Review model doesn't exist
        queryset = queryset.annotate(rating=Value(0.0, output_field=FloatField()))
        
        # Handle search query
        search_query = self.request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__email__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(nin_number__icontains=search_query)
            )
            
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def get_serializer_class(self):
        return CourierListSerializer


class CourierDetailView(generics.RetrieveUpdateAPIView):
    """
    API endpoint to retrieve, update, or delete a specific courier.
    """
    queryset = CourierProfile.objects.all()
    serializer_class = CourierProfileSerializer
    permission_classes = [permissions.IsAuthenticated, DRFIsAdminUser]
    lookup_field = 'id'
    
    def get_queryset(self):
        return CourierProfile.objects.select_related('user')
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Don't allow updating the user's email or username through this endpoint
        user_data = request.data.pop('user', None)
        if user_data:
            if 'email' in user_data:
                del user_data['email']
            if 'username' in user_data:
                del user_data['username']
            
            # Update user data if provided
            user_serializer = self.get_serializer(instance.user, data=user_data, partial=partial)
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()
        
        # Update courier profile
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)


class CourierVerificationView(generics.UpdateAPIView):
    """
    API endpoint to update a courier's verification status.
    
    Required fields in request body:
    - action: 'approve' or 'reject'
    - notes: Required if action is 'reject'
    """
    queryset = CourierProfile.objects.all()
    serializer_class = CourierProfileSerializer
    permission_classes = [permissions.IsAuthenticated, DRFIsAdminUser]
    lookup_field = 'id'
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        action = request.data.get('action', '').lower()
        notes = request.data.get('notes', '').strip()
        
        if action not in ['approve', 'reject']:
            return Response(
                {"error": "Invalid action. Must be 'approve' or 'reject'"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if action == 'reject' and not notes:
            return Response(
                {"error": "Rejection notes are required when rejecting a courier"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if action == 'approve':
            instance.verification_status = 'verified'
            instance.verification_notes = ''
            message = f"Courier {instance.user.get_full_name()} has been approved"
        else:
            instance.verification_status = 'rejected'
            instance.verification_notes = notes
            message = f"Courier {instance.user.get_full_name()} has been rejected"
            
        instance.verified_by = request.user
        instance.save()
        
        serializer = self.get_serializer(instance)
        return Response({
            "message": message,
            "courier": serializer.data
        })


class CourierRegistrationView(generics.CreateAPIView):
    """
    Public endpoint for new couriers to register.
    Creates both a User and a CourierProfile with verification_status='pending'.
    No authentication required.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = CourierRegistrationSerializer
    parser_classes = [MultiPartParser, JSONParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                courier_profile = serializer.save()

            # Prepare response with detailed profile
            response_serializer = CourierProfileSerializer(courier_profile)
            # Use response serializer (not the registration serializer) to avoid binding errors
            headers = self.get_success_headers(response_serializer.data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        except Exception as e:
            logger.exception("Courier registration failed")
            detail = str(e) if settings.DEBUG else "An error occurred during registration. Please try again."
            return Response(
                {"detail": detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
