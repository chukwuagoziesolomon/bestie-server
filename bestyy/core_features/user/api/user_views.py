"""
User management views for registration, authentication, and profile management.
"""
from rest_framework import status, permissions, serializers
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
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination

from bestyy.core_features.user.serializers.user_serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
    UserDetailSerializer,
    MultiRoleRegistrationSerializer
)
from bestyy.core_features.user.serializers.address_serializers import AddressSerializer
from bestyy.core_features.user.serializers.order_serializers import OrderSerializer, UserOrderSerializer
from bestyy.core_features.user.models import Address
from bestyy.restaurant_features.order.models import Order

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
    Returns multiple profiles if user has registered for multiple roles.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SelectProfileView(APIView):
    """
    API endpoint to select a specific profile when user has multiple roles.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        profile_id = request.data.get('profile_id')
        
        if not all([email, password, profile_id]):
            return Response({
                'error': 'Email, password, and profile_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get the specific user profile
            user = User.objects.get(id=profile_id, email__iexact=email)
            
            # Verify password
            if not user.check_password(password):
                return Response({
                    'error': 'Invalid credentials'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            if not user.is_active:
                return Response({
                    'error': 'User account is disabled'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Generate tokens for selected profile
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            
            profile_data = {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'phone': user.profile.phone if hasattr(user, 'profile') else user.phone,
            }
            
            # Add role-specific info
            if user.role == 'vendor' and hasattr(user, 'vendor_profile'):
                profile_data['vendor_info'] = {
                    'business_name': user.vendor_profile.business_name,
                    'is_verified': user.vendor_profile.is_verified,
                }
            elif user.role == 'courier' and hasattr(user, 'courier_profile'):
                profile_data['courier_info'] = {
                    'is_verified': user.courier_profile.is_verified,
                    'is_available': user.courier_profile.is_available,
                }
            
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': profile_data
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'error': 'Profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(RetrieveUpdateAPIView):
    """
    API endpoint to view and update user profile.
    Returns complete user data including profile information.
    """
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserProfileInfoView(RetrieveUpdateAPIView):
    """
    API endpoint to get and update user profile information for normal users.
    Supports GET (retrieve) and PUT/PATCH (update) operations.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user profile information"""
        user = request.user

        # Get user profile if it exists
        profile_data = {}
        if hasattr(user, 'profile') and user.profile:
            profile_data = {
                'phone': user.profile.phone,
                'address': user.profile.address,
                'nick_name': user.profile.nick_name,
                'language': user.profile.language,
                'profile_picture': user.profile.profile_picture.url if user.profile.profile_picture else None,
                'email_notifications': user.profile.email_notifications,
                'push_notifications': user.profile.push_notifications,
            }

        response_data = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.full_name,
            'role': user.role,
            'phone': user.phone or profile_data.get('phone'),
            'profile_complete': user.profile_complete,
            'is_featured': user.is_featured,
            'date_joined': user.date_joined.isoformat() if user.date_joined else None,
            'profile': profile_data
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """Update user profile information"""
        user = request.user
        data = request.data

        # Handle user model updates
        user_fields = ['first_name', 'last_name', 'phone']
        user_data = {}

        for field in user_fields:
            if field in data:
                user_data[field] = data[field]

        if user_data:
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()

        # Handle profile updates
        profile_fields = ['phone', 'address', 'nick_name', 'language', 'email_notifications', 'push_notifications', 'profile_picture']
        profile_data = {}

        for field in profile_fields:
            if field in data:
                profile_data[field] = data[field]

        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            profile_data['profile_picture'] = request.FILES['profile_picture']

        if profile_data:
            # Ensure user has a profile
            from bestyy.core_features.user.models import UserProfile
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'phone': user.phone}
            )

            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        # Return updated profile data
        return self.get(request)


class HealthCheckView(APIView):
    """
    Health check endpoint for monitoring service status.
    """
    permission_classes = []  # Allow public access for monitoring

    def get(self, request):
        """Return service health status"""
        from django.db import connection
        from django.core.cache import cache

        health_status = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'service': 'bestyy-backend',
            'version': '1.0.0'
        }

        # Check database connectivity
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_status['database'] = 'connected'
        except Exception as e:
            health_status['database'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'

        # Check cache connectivity (optional)
        try:
            cache.set('health_check', 'ok', 10)
            cache_value = cache.get('health_check')
            if cache_value == 'ok':
                health_status['cache'] = 'connected'
            else:
                health_status['cache'] = 'error: cache not working'
                health_status['status'] = 'degraded'
        except Exception as e:
            health_status['cache'] = f'error: {str(e)}'
            # Don't mark as unhealthy for cache issues

        # Set HTTP status code
        status_code = 200 if health_status['status'] == 'healthy' else 503

        return Response(health_status, status=status_code)


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
    API endpoint to get the current user's main profile details.
    """
    serializer_class = UserProfileSerializer  # Keep this for user profile view
    permission_classes = [IsAuthenticated]

    def get_object(self):
        from bestyy.core_features.user.models import UserProfile, VendorProfile, CourierProfile
        user = self.request.user
        
        # Get explicit roles from UserRole table (don't default to 'user')
        if hasattr(user, 'get_roles'):
            roles = user.get_roles()
        else:
            roles = []
            if hasattr(user, 'role') and user.role:
                roles = [user.role]
        
        # Priority: vendor > courier > user (only if explicitly assigned)
        if 'vendor' in roles:
            if hasattr(user, 'vendor_profile'):
                return user.vendor_profile
            # If vendor role exists but no profile, registration was incomplete
            from rest_framework.exceptions import NotFound
            raise NotFound("Vendor profile not found. Please complete your vendor registration.")
        elif 'courier' in roles:
            if hasattr(user, 'courier_profile'):
                return user.courier_profile
            # If courier role exists but no profile, registration was incomplete
            from rest_framework.exceptions import NotFound
            raise NotFound("Courier profile not found. Please complete your courier registration.")
        elif 'user' in roles:
            # Only return UserProfile if user explicitly has 'user' role
            if hasattr(user, 'profile'):
                return user.profile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            return profile
        
        # If no explicit roles found, raise an error instead of defaulting to user
        from rest_framework.exceptions import NotFound
        raise NotFound("No profile found. Please complete your registration.")


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
        queryset = Order.objects.filter(customer=self.request.user).order_by('-created_at')
        
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
        return Order.objects.filter(customer=self.request.user)
    
    def get_object(self):
        order_id = self.kwargs.get('order_id')
        return get_object_or_404(
            Order.objects.filter(customer=self.request.user),
            id=order_id
        )


class UserAddressListView(ListCreateAPIView):
    """
    API endpoint for users to list and create their addresses.
    
    GET: List all addresses for the authenticated user
    POST: Create a new address for the authenticated user (with Google Maps validation)
    
    POST accepts optional 'validate_google' parameter to enable address validation
    """
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user).order_by('-is_default', '-created_at')
    
    def perform_create(self, serializer):
        # Save address with the authenticated user
        address = serializer.save(user=self.request.user)
        
        # If setting as default, unset other defaults
        if address.is_default:
            Address.objects.filter(
                user=self.request.user,
                is_default=True
            ).exclude(pk=address.pk).update(is_default=False)


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


class ValidateAddressView(APIView):
    """
    Validate and parse a Google Place ID into address components
    
    POST /api/user/addresses/validate/
    {
        "place_id": "ChIJ...",  // Optional: from Google autocomplete
        "address": "123 Street, Lagos"  // Optional: manual address
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from bestyy.core_features.user.services.google_maps_service import GoogleMapsService
        import requests
        from django.conf import settings
        
        place_id = request.data.get('place_id')
        address_text = request.data.get('address')
        
        if not place_id and not address_text:
            return Response({
                'error': 'Either place_id or address is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        google_service = GoogleMapsService()
        
        # If place_id provided, get place details
        if place_id:
            try:
                api_key = settings.GOOGLE_MAPS_API_KEY
                url = f"https://maps.googleapis.com/maps/api/place/details/json"
                params = {
                    'place_id': place_id,
                    'key': api_key,
                    'fields': 'formatted_address,address_components,geometry'
                }
                
                resp = requests.get(url, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                
                if data.get('status') == 'OK' and data.get('result'):
                    result = data['result']
                    address_components = result.get('address_components', [])
                    
                    # Parse components
                    parsed = {
                        'street_address': '',
                        'city': '',
                        'state': '',
                        'postal_code': '',
                        'formatted_address': result.get('formatted_address'),
                        'coordinates': {
                            'latitude': result['geometry']['location']['lat'],
                            'longitude': result['geometry']['location']['lng']
                        }
                    }
                    
                    for component in address_components:
                        types = component.get('types', [])
                        if 'street_number' in types or 'route' in types:
                            parsed['street_address'] += component.get('long_name', '') + ' '
                        elif 'locality' in types or 'administrative_area_level_2' in types:
                            parsed['city'] = component.get('long_name', '')
                        elif 'administrative_area_level_1' in types:
                            parsed['state'] = component.get('long_name', '')
                        elif 'postal_code' in types:
                            parsed['postal_code'] = component.get('long_name', '')
                    
                    parsed['street_address'] = parsed['street_address'].strip()
                    
                    return Response({
                        'success': True,
                        'address': parsed
                    }, status=status.HTTP_200_OK)
                    
            except Exception as e:
                return Response({
                    'error': f'Failed to fetch place details: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # If only address text provided, geocode it
        if address_text:
            result = google_service.validate_and_correct_address(address_text)
            if result and result.get('is_valid'):
                return Response({
                    'success': True,
                    'address': {
                        'formatted_address': result.get('corrected_address'),
                        'coordinates': result.get('coordinates')
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': 'Address validation failed',
                    'suggestions': result.get('suggestions', []) if result else []
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'error': 'Invalid request'
        }, status=status.HTTP_400_BAD_REQUEST)


# Favorites feature (conditionally available)
try:
    from bestyy.core_features.user.serializers.favorite_serializers import FavoriteSerializer
    from bestyy.core_features.user.models import Favorite
    _favorites_available = True
except Exception:
    FavoriteSerializer = None
    Favorite = None
    _favorites_available = False

if _favorites_available:
    class UserFavoritesListView(ListCreateAPIView):
        """
        API endpoint for users to list and create their favorites.
        """
        serializer_class = FavoriteSerializer
        permission_classes = [IsAuthenticated]
        pagination_class = StandardResultsSetPagination

        def get_queryset(self):
            queryset = Favorite.objects.filter(user=self.request.user).order_by('-created_at')
            favorite_type = self.request.query_params.get('type', None)
            if favorite_type:
                queryset = queryset.filter(favorite_type=favorite_type)
            return queryset

        def perform_create(self, serializer):
            serializer.save(user=self.request.user)

    class UserFavoritesDetailView(RetrieveUpdateDestroyAPIView):
        serializer_class = FavoriteSerializer
        permission_classes = [IsAuthenticated]

        def get_queryset(self):
            return Favorite.objects.filter(user=self.request.user)

    class UserFoodFavoritesView(ListAPIView):
        serializer_class = FavoriteSerializer
        permission_classes = [IsAuthenticated]
        pagination_class = StandardResultsSetPagination

        def get_queryset(self):
            return Favorite.objects.filter(user=self.request.user, favorite_type='food').order_by('-created_at')

    class UserVenueFavoritesView(ListAPIView):
        serializer_class = FavoriteSerializer
        permission_classes = [IsAuthenticated]
        pagination_class = StandardResultsSetPagination

        def get_queryset(self):
            return Favorite.objects.filter(user=self.request.user, favorite_type='venue').order_by('-created_at')

    class UserAutoFavoriteView(APIView):
        permission_classes = [IsAuthenticated]

        def post(self, request):
            from bestyy.core_features.user.services.auto_favorite_service import AutoFavoriteService
            service = AutoFavoriteService(request.user)
            return Response({"detail": "Auto-favorite processing triggered."}, status=status.HTTP_200_OK)

else:
    class UserFavoritesListView(APIView):
        permission_classes = [IsAuthenticated]
        def get(self, request):
            return Response({"detail": "Favorites feature is unavailable."}, status=status.HTTP_501_NOT_IMPLEMENTED)
        def post(self, request):
            return Response({"detail": "Favorites feature is unavailable."}, status=status.HTTP_501_NOT_IMPLEMENTED)

    class UserFavoritesDetailView(APIView):
        permission_classes = [IsAuthenticated]
        def get(self, request, *args, **kwargs):
            return Response({"detail": "Favorites feature is unavailable."}, status=status.HTTP_501_NOT_IMPLEMENTED)
        def put(self, request, *args, **kwargs):
            return Response({"detail": "Favorites feature is unavailable."}, status=status.HTTP_501_NOT_IMPLEMENTED)
        def patch(self, request, *args, **kwargs):
            return Response({"detail": "Favorites feature is unavailable."}, status=status.HTTP_501_NOT_IMPLEMENTED)
        def delete(self, request, *args, **kwargs):
            return Response({"detail": "Favorites feature is unavailable."}, status=status.HTTP_501_NOT_IMPLEMENTED)

    class UserFoodFavoritesView(APIView):
        permission_classes = [IsAuthenticated]
        def get(self, request):
            return Response({"detail": "Favorites feature is unavailable."}, status=status.HTTP_501_NOT_IMPLEMENTED)

    class UserVenueFavoritesView(APIView):
        permission_classes = [IsAuthenticated]
        def get(self, request):
            return Response({"detail": "Favorites feature is unavailable."}, status=status.HTTP_501_NOT_IMPLEMENTED)
            
    class UserAutoFavoriteView(APIView):
        permission_classes = [IsAuthenticated]
        def post(self, request):
            return Response({"detail": "Favorites feature is unavailable."}, status=status.HTTP_501_NOT_IMPLEMENTED)


class MultiRoleRegistrationView(APIView):
    """
    View for multi-role registration allowing users to sign up for multiple roles
    with the same email/phone/password but preventing duplicate roles.

    For normal users (role='user'), registration is immediate without verification.
    For vendors and couriers, WhatsApp verification is required.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # Check if this is a simple user registration (only email, password, confirm_password)
        data = request.data
        required_fields = ['email', 'password', 'confirm_password']
        has_only_user_fields = all(field in data for field in required_fields) and len(data) <= 4

        # If only basic user fields are provided, treat as simple user registration
        if has_only_user_fields and 'roles' not in data:
            return self._handle_simple_user_registration(request)

        # Otherwise, use the full multi-role registration flow
        serializer = MultiRoleRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            try:
                # Check if only 'user' role is requested - skip WhatsApp verification
                roles = serializer.validated_data.get('roles', [])
                if roles == ['user']:
                    # Create user directly without WhatsApp verification
                    return self._handle_user_only_registration(serializer.validated_data)

                # For other roles (vendor, courier, or combinations), use WhatsApp verification
                pending_user = serializer.save()

                response_data = {
                    'success': True,
                    'pending_user_id': pending_user.pk,
                    'verification_code': pending_user.verification_code,
                    'phone': pending_user.phone,
                    'roles': pending_user.profile_data.get('roles', []),
                    'message': f'Send "VERIFY {pending_user.verification_code}" to WhatsApp number {pending_user.phone}'
                }

                return Response(response_data, status=status.HTTP_201_CREATED)

            except serializers.ValidationError as e:
                # Handle serializer validation errors (like role conflicts)
                return Response({'error': e.detail}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({
                    'error': f'Registration failed: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _handle_user_only_registration(self, validated_data):
        """
        Handle registration for users with only 'user' role - skip WhatsApp verification.
        Allows same email for different roles.
        """
        email = validated_data['email']
        password = validated_data['password']
        phone = validated_data['phone']
        first_name = validated_data.get('first_name') or (email.split('@')[0].split('.')[0].title() if email else 'User')
        last_name = validated_data.get('last_name') or 'User'

        try:
            # Check if user role already exists with this email AND role
            existing_user_role = User.objects.filter(email=email, role='user').first()
            if existing_user_role:
                return Response({
                    'error': 'You already have a user account with this email. Please login to access it.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # If user has other roles (vendor/courier) with same email, get password from existing account
            existing_user = User.objects.filter(email=email).first()
            if existing_user:
                # Verify password matches existing account
                if not existing_user.check_password(password):
                    return Response({
                        'error': 'Password does not match your existing account. Please use the same password.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                # Use same name from existing account
                first_name = existing_user.first_name
                last_name = existing_user.last_name

            # Create the user directly (no pending verification needed)
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role='user'
            )

            # Create or update user profile
            from bestyy.core_features.user.models import UserProfile
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'phone': phone,
                    'email_notifications': True,
                    'push_notifications': True
                }
            )
            # If profile already existed, ensure phone is set
            if not created and not profile.phone:
                profile.phone = phone
                profile.save()

            # Generate JWT tokens
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            response_data = {
                'success': True,
                'message': 'User account created successfully.',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'phone': user.profile.phone if hasattr(user, 'profile') else phone
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': access_token
                }
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'error': f'Registration failed: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    def _handle_simple_user_registration(self, request):
        """
        Handle simple user registration without WhatsApp verification.
        Only requires email, password, and confirm_password.
        Allows same email for different roles.
        """
        data = request.data

        # Validate required fields
        if not all(field in data for field in ['email', 'password', 'confirm_password']):
            return Response({
                'error': 'Email, password, and confirm_password are required for user registration.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check password match
        if data['password'] != data['confirm_password']:
            return Response({
                'error': 'Passwords do not match.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Check if user role already exists with this email AND role
            existing_user_role = User.objects.filter(email=data['email'], role='user').first()
            if existing_user_role:
                return Response({
                    'error': 'You already have a user account with this email. Please login to access it.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # If user has other roles (vendor/courier) with same email, verify password matches
            existing_user = User.objects.filter(email=data['email']).first()
            if existing_user:
                if not existing_user.check_password(data['password']):
                    return Response({
                        'error': 'Password does not match your existing account. Please use the same password.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                # Use same name from existing account
                data['first_name'] = existing_user.first_name
                data['last_name'] = existing_user.last_name

            # Create the user directly (no pending verification needed)
            user = User.objects.create_user(
                username=data['email'],  # Django requires username, use email
                email=data['email'],
                password=data['password'],
                first_name=data.get('first_name', data['email'].split('@')[0].split('.')[0].title()),
                last_name=data.get('last_name', 'User'),
                role='user'
            )

            # Create user profile
            from bestyy.core_features.user.models import UserProfile
            UserProfile.objects.create(
                user=user,
                phone=data.get('phone', ''),
                email_notifications=True,
                push_notifications=True
            )

            # Generate JWT tokens
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            response_data = {
                'success': True,
                'message': 'User account created successfully.',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'phone': user.profile.phone if hasattr(user, 'profile') else None
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': access_token
                }
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'error': f'Registration failed: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
