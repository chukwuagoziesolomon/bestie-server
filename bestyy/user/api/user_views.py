"""
User management views for registration, authentication, and profile management.
"""
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import (
    CreateAPIView, 
    RetrieveUpdateAPIView, 
    ListAPIView,
    UpdateAPIView,
    DestroyAPIView,
    RetrieveAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView
)
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination

from user.serializers.user_serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
    UserDetailSerializer,
    MultiRoleRegistrationSerializer
)
from user.serializers import AddressSerializer, OrderSerializer, UserOrderSerializer, FavoriteSerializer
from user.models import Address, Order, Favorite

User = get_user_model()

class UserRegistrationView(CreateAPIView):
    """
    API endpoint for user registration.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        # Additional logic after user creation can go here


class UserLoginView(APIView):
    """
    API endpoint for user login.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(RetrieveUpdateAPIView):
    """
    API endpoint to view and update user profile.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(UpdateAPIView):
    """
    API endpoint to change user password.
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            if not self.object.check_password(serializer.data.get("old_password")):
                return Response(
                    {"old_password": ["Wrong password."]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Set the new password
            self.object.set_password(serializer.data.get("new_password"))
            self.object.save()
            return Response("Password updated successfully", status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(ListAPIView):
    """
    API endpoint to list all users (admin only).
    """
    serializer_class = UserDetailSerializer
    permission_classes = [IsAdminUser]
    queryset = User.objects.all()


class UserDetailView(RetrieveUpdateAPIView):
    """
    API endpoint to view/update a user (admin only).
    """
    serializer_class = UserDetailSerializer
    permission_classes = [IsAdminUser]
    queryset = User.objects.all()
    lookup_field = 'id'


class AdminUserCreateView(CreateAPIView):
    """
    API endpoint for admin to create new users.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [IsAdminUser]


class AdminUserUpdateView(UpdateAPIView):
    """
    API endpoint for admin to update users.
    """
    serializer_class = UserDetailSerializer
    permission_classes = [IsAdminUser]
    queryset = User.objects.all()
    lookup_field = 'id'


class AdminUserDeleteView(DestroyAPIView):
    """
    API endpoint for admin to delete users.
    """
    permission_classes = [IsAdminUser]
    queryset = User.objects.all()
    lookup_field = 'id'
    
    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class CurrentUserView(RetrieveAPIView):
    """
    API endpoint to get the current user's profile details.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.profile


class LogoutView(APIView):
    """
    API endpoint to log out the user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Simply return success - the actual token invalidation is handled by the frontend
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class UserOrdersView(ListAPIView):
    """
    API endpoint for users to view their own orders.
    
    GET: List all orders for the authenticated user with filtering options
    """
    serializer_class = UserOrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        queryset = Order.objects.filter(user=self.request.user).order_by('-created_at')
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Filter by vendor if provided
        vendor_id = self.request.query_params.get('vendor_id', None)
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
        
        return queryset


class UserOrderDetailView(RetrieveAPIView):
    """
    API endpoint for users to view detailed information about a specific order.
    
    GET: Get detailed information about a specific order by ID
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
    
    def get_object(self):
        order_id = self.kwargs.get('order_id')
        return get_object_or_404(
            Order.objects.filter(user=self.request.user),
            id=order_id
        )


class UserAddressListView(ListCreateAPIView):
    """
    API endpoint for users to list and create their addresses.
    
    GET: List all addresses for the authenticated user
    POST: Create a new address for the authenticated user
    """
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user).order_by('-is_default', '-created_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserAddressDetailView(RetrieveUpdateDestroyAPIView):
    """
    API endpoint for users to view, update, and delete their addresses.
    
    GET: Get a specific address
    PUT/PATCH: Update a specific address
    DELETE: Delete a specific address
    """
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)
    
    def perform_update(self, serializer):
        # If this address is being set as default, unset other defaults
        if serializer.validated_data.get('is_default', False):
            Address.objects.filter(
                user=self.request.user, 
                is_default=True
            ).exclude(pk=serializer.instance.pk).update(is_default=False)
        serializer.save()
    
    def perform_destroy(self, instance):
        # If this was the default address, set another one as default
        if instance.is_default:
            other_addresses = Address.objects.filter(
                user=self.request.user
            ).exclude(pk=instance.pk).order_by('-created_at')
            if other_addresses.exists():
                other_addresses.first().is_default = True
                other_addresses.first().save()
        instance.delete()


class UserAddressSetDefaultView(APIView):
    """
    API endpoint for users to set a specific address as their default address.
    
    POST: Set an address as default
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, address_id):
        try:
            address = Address.objects.get(id=address_id, user=request.user)
            
            # Unset all other default addresses for this user
            Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
            
            # Set this address as default
            address.is_default = True
            address.save()
            
            return Response({
                "detail": f"Address '{address.full_name}' has been set as default.",
                "address": AddressSerializer(address).data
            }, status=status.HTTP_200_OK)
            
        except Address.DoesNotExist:
            return Response({
                "detail": "Address not found."
            }, status=status.HTTP_404_NOT_FOUND)


class UserFavoritesListView(ListCreateAPIView):
    """
    API endpoint for users to list and create their favorites.
    
    GET: List all favorites for the authenticated user
    POST: Create a new favorite (food item or venue)
    """
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        queryset = Favorite.objects.filter(user=self.request.user).order_by('-created_at')
        
        # Filter by favorite type if provided
        favorite_type = self.request.query_params.get('type', None)
        if favorite_type:
            queryset = queryset.filter(favorite_type=favorite_type)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserFavoritesDetailView(RetrieveUpdateDestroyAPIView):
    """
    API endpoint for users to view, update, and delete their favorites.
    
    GET: Get a specific favorite
    PUT/PATCH: Update a specific favorite
    DELETE: Delete a specific favorite
    """
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)


class UserFoodFavoritesView(ListAPIView):
    """
    API endpoint for users to view only their favorite food items.
    
    GET: List all favorite food items for the authenticated user
    """
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        return Favorite.objects.filter(
            user=self.request.user, 
            favorite_type='food'
        ).order_by('-created_at')


class UserVenueFavoritesView(ListAPIView):
    """
    API endpoint for users to view only their favorite venues.
    
    GET: List all favorite venues for the authenticated user
    """
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        return Favorite.objects.filter(
            user=self.request.user, 
            favorite_type='venue'
        ).order_by('-created_at')


class UserAutoFavoriteView(APIView):
    """
    API endpoint to manually trigger auto-favorite service for the current user.
    
    POST: Trigger auto-favorite check and add favorites based on ordering history
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            from user.services.auto_favorite_service import AutoFavoriteService
            
            service = AutoFavoriteService(request.user)
            
            # Get frequently ordered items and restaurants
            frequent_items = service.get_frequently_ordered_items(days=30, min_orders=3)
            frequent_restaurants = service.get_frequently_ordered_restaurants(days=60, min_orders=5)
            
            # Add favorites
            added_food_favorites = []
            added_venue_favorites = []
            
            for item in frequent_items:
                if not Favorite.objects.filter(
                    user=request.user,
                    favorite_type='food',
                    food_item=item
                ).exists():
                    service._add_food_favorite(item)
                    added_food_favorites.append({
                        'id': item.id,
                        'name': item.dish_name,
                        'vendor': item.vendor.business_name
                    })
            
            for restaurant in frequent_restaurants:
                if not Favorite.objects.filter(
                    user=request.user,
                    favorite_type='venue',
                    vendor=restaurant
                ).exists():
                    service._add_restaurant_favorite(restaurant)
                    added_venue_favorites.append({
                        'id': restaurant.id,
                        'name': restaurant.business_name
                    })
            
            return Response({
                'message': 'Auto-favorite check completed successfully',
                'added_food_favorites': added_food_favorites,
                'added_venue_favorites': added_venue_favorites,
                'total_added': len(added_food_favorites) + len(added_venue_favorites)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Auto-favorite check failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MultiRoleRegistrationView(APIView):
    """
    View for multi-role registration allowing users to sign up for multiple roles
    with the same email/phone/password but preventing duplicate roles.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = MultiRoleRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                user = serializer.save()
                
                # Generate JWT tokens
                from rest_framework_simplejwt.tokens import RefreshToken
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'message': 'Registration successful',
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'roles': user.get_roles(),
                        'primary_role': user.role
                    },
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token)
                    }
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response({
                    'error': f'Registration failed: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
