from django.shortcuts import render
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import VendorProfile, CourierProfile, UserProfile, MenuItem, Order, Booking, Address, Favorite, Payment, SavedCard
from .serializers import (
    VendorProfileSerializer, CourierProfileSerializer, UserProfileSerializer, 
    OrderSerializer, BookingSerializer, AddressSerializer, FavoriteSerializer, 
    PaymentSerializer, SavedCardSerializer, MenuItemSerializer,
    UserSignupSerializer, VendorApplicationSerializer, CourierApplicationSerializer,
    VendorProfileMinimalSerializer, VendorOrderTrackingSerializer
)
from rest_framework.permissions import IsAuthenticated
import requests
import json
from django.utils import timezone

# Serializers will be imported/defined here

class VendorSignupView(generics.CreateAPIView):
    """API endpoint for vendor registration."""
    serializer_class = VendorProfileSerializer
    permission_classes = [] # No auth needed for signup

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        vendor_profile = serializer.save()  # Save and get the instance
        user = vendor_profile.user
        token, created = Token.objects.get_or_create(user=user)

        # Use minimal serializer for response
        minimal_profile = VendorProfileMinimalSerializer(vendor_profile).data

        return Response(
            {
                "message": "Registration successful. Your account is now active.",
                "token": token.key,
                "vendor": minimal_profile
            },
            status=status.HTTP_201_CREATED
        )

class CourierSignupView(generics.CreateAPIView):
    """API endpoint for courier registration."""
    serializer_class = CourierProfileSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "message": "Registration successful. Your account will be reviewed and activated soon.",
                "courier": serializer.data
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )

# --- User Account and Role Management ---

class UserSignupView(generics.CreateAPIView):
    """
    Handles core user account creation. This is the first step for anyone.
    """
    serializer_class = UserSignupSerializer
    permission_classes = [] # No auth needed

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_profile = self.perform_create(serializer)
        
        user = user_profile.user
        token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            "message": "User account created successfully.",
            "token": token.key,
            "user_id": user.id,
            "email": user.email
        }, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        return serializer.save()

class VendorApplicationView(generics.CreateAPIView):
    """
    Allows a logged-in user to apply to become a vendor.
    """
    serializer_class = VendorApplicationSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Prevent creating multiple vendor profiles
        if VendorProfile.objects.filter(user=self.request.user).exists():
            raise serializers.ValidationError("You already have a vendor profile.")
        serializer.save(user=self.request.user)

class CourierApplicationView(generics.CreateAPIView):
    """
    Allows a logged-in user to apply to become a courier.
    """
    serializer_class = CourierApplicationSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Prevent creating multiple courier profiles
        if CourierProfile.objects.filter(user=self.request.user).exists():
            raise serializers.ValidationError("You already have a courier profile.")
        serializer.save(user=self.request.user)


class EmailLoginView(APIView):
    """Secure email-based login with authentication token and multiple roles info."""
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        # Validate required fields
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({'error': 'Password is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Invalid email or password.'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(username=user.username, password=password)
        if user:
            token, created = Token.objects.get_or_create(user=user)
            
            # Check for all possible roles
            roles = []
            profiles = {}

            # Check for standard user profile
            try:
                user_profile = user.profile
                roles.append('user')
                profiles['user'] = UserProfileSerializer(user_profile).data
            except UserProfile.DoesNotExist:
                pass # Not a standard user

            # Check for vendor profile
            try:
                vendor_profile = user.vendor_profile
                roles.append('vendor')
                profiles['vendor'] = VendorProfileSerializer(vendor_profile).data
            except VendorProfile.DoesNotExist:
                pass # Not a vendor

            # Check for courier profile
            try:
                courier_profile = user.courier_profile
                roles.append('courier')
                profiles['courier'] = CourierProfileSerializer(courier_profile).data
            except CourierProfile.DoesNotExist:
                pass # Not a courier
            
            # If no specific roles found, they are at least a base user
            if not roles:
                roles.append('user')

            return Response({
                'message': 'Login successful.',
                'token': token.key,
                'roles': roles,
                'profiles': profiles,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                }
            })
        else:
            return Response({'error': 'Invalid email or password.'}, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    """Logout endpoint to invalidate token."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Delete the token
            request.user.auth_token.delete()
            return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Error during logout.'}, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(APIView):
    """Get current user profile."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        try:
            user_profile = UserProfile.objects.get(user=user)
            profile_data = {
                'id': user_profile.id,
                'phone': user_profile.phone,
                'address': user_profile.address,
                'profile_picture': user_profile.profile_picture.url if user_profile.profile_picture else None
            }
        except UserProfile.DoesNotExist:
            profile_data = None
        
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'profile': profile_data
            }
        })

class UserProfileUpdateView(generics.UpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return UserProfile.objects.get(user=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_update(serializer)
        return Response(
            {
                "message": "Profile updated successfully.",
                "profile": serializer.data
            }
        )

class UserOrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

class UserBookingListView(generics.ListAPIView):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).order_by('-created_at')

class UserAddressListView(generics.ListAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user).order_by('-is_default', '-created_at')

class UserAddressCreateView(generics.CreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "message": "Address saved successfully.",
                "address": serializer.data
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )

class UserAddressUpdateView(generics.UpdateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_update(serializer)
        return Response(
            {
                "message": "Address updated successfully.",
                "address": serializer.data
            }
        )

class UserAddressDeleteView(generics.DestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "Address deleted successfully."},
            status=status.HTTP_200_OK
        )

class UserFavoriteListView(generics.ListAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Favorite.objects.filter(user=self.request.user)
        favorite_type = self.request.query_params.get('type', None)
        if favorite_type:
            queryset = queryset.filter(favorite_type=favorite_type)
        return queryset.order_by('-created_at')

class UserFavoriteCreateView(generics.CreateAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if favorite already exists
        favorite_type = serializer.validated_data.get('favorite_type')
        food_item = serializer.validated_data.get('food_item')
        vendor = serializer.validated_data.get('vendor')
        
        existing_favorite = None
        if favorite_type == 'food' and food_item:
            existing_favorite = Favorite.objects.filter(
                user=request.user, 
                favorite_type='food', 
                food_item=food_item
            ).first()
        elif favorite_type == 'venue' and vendor:
            existing_favorite = Favorite.objects.filter(
                user=request.user, 
                favorite_type='venue', 
                vendor=vendor
            ).first()
        
        if existing_favorite:
            return Response(
                {"error": "This item is already in your favorites."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "message": "Added to favorites successfully.",
                "favorite": serializer.data
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )

class UserFavoriteDeleteView(generics.DestroyAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "Removed from favorites successfully."},
            status=status.HTTP_200_OK
        )

class PaymentCreateView(generics.CreateAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        payment = serializer.save()
        
        # Initialize Paystack transaction
        try:
            paystack_response = self.initialize_paystack_transaction(payment)
            return Response({
                "message": "Payment initialized successfully.",
                "payment": serializer.data,
                "paystack_data": paystack_response
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            payment.status = 'failed'
            payment.save()
            return Response({
                "error": "Failed to initialize payment.",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def initialize_paystack_transaction(self, payment):
        # Paystack API configuration (you'll need to add these to settings)
        PAYSTACK_SECRET_KEY = "your_paystack_secret_key"  # Add to settings
        PAYSTACK_BASE_URL = "https://api.paystack.co"
        
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "amount": int(payment.amount * 100),  # Paystack expects amount in kobo
            "email": payment.user.email,
            "reference": payment.paystack_reference,
            "callback_url": "https://your-domain.com/api/paystack/webhook/",
            "currency": payment.currency,
            "metadata": {
                "payment_id": payment.id,
                "user_id": payment.user.id,
                "description": payment.description
            }
        }
        
        response = requests.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Paystack API error: {response.text}")

class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).order_by('-created_at')

class SavedCardListView(generics.ListAPIView):
    serializer_class = SavedCardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SavedCard.objects.filter(user=self.request.user).order_by('-is_default', '-created_at')

class SavedCardCreateView(generics.CreateAPIView):
    serializer_class = SavedCardSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "message": "Card saved successfully.",
                "card": serializer.data
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )

class SavedCardDeleteView(generics.DestroyAPIView):
    serializer_class = SavedCardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SavedCard.objects.filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "Card removed successfully."},
            status=status.HTTP_200_OK
        )

class PaystackWebhookView(APIView):
    def post(self, request):
        # Verify Paystack webhook signature
        if not self.verify_paystack_signature(request):
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            data = json.loads(request.body)
            event = data.get('event')
            
            if event == 'charge.success':
                self.handle_successful_payment(data['data'])
            elif event == 'charge.failed':
                self.handle_failed_payment(data['data'])
            
            return Response({"status": "success"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def verify_paystack_signature(self, request):
        # Implement Paystack webhook signature verification
        # This is important for security
        PAYSTACK_SECRET_KEY = "your_paystack_secret_key"  # Add to settings
        # Add signature verification logic here
        return True  # Placeholder

    def handle_successful_payment(self, data):
        reference = data.get('reference')
        payment = Payment.objects.get(paystack_reference=reference)
        payment.status = 'successful'
        payment.paystack_transaction_id = data.get('id')
        payment.metadata = data
        payment.save()

    def handle_failed_payment(self, data):
        reference = data.get('reference')
        payment = Payment.objects.get(paystack_reference=reference)
        payment.status = 'failed'
        payment.metadata = data
        payment.save()

class UserOrderCreateView(generics.CreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        items = data.pop('items', [])
        vendor_id = data.get('vendor')
        if not vendor_id or not items:
            return Response({'error': 'Vendor and items are required.'}, status=status.HTTP_400_BAD_REQUEST)
        from .models import VendorProfile, MenuItem, Order
        try:
            vendor = VendorProfile.objects.get(pk=vendor_id)
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        menu_items = MenuItem.objects.filter(pk__in=items, vendor=vendor)
        if menu_items.count() != len(items):
            return Response({'error': 'One or more menu items are invalid for this vendor.'}, status=status.HTTP_400_BAD_REQUEST)
        order = Order.objects.create(
            user=request.user,
            vendor=vendor,
            total_price=data.get('total_price', 0),
            order_name=data.get('order_name', None),
            delivery_address=data.get('delivery_address', ''),
            delivery_date=data.get('delivery_date', None)
        )
        order.items.set(menu_items)
        order.save()
        serializer = self.get_serializer(order)
        return Response({
            'message': 'Order created successfully.',
            'order': serializer.data
        }, status=status.HTTP_201_CREATED)

class UserBookingCreateView(generics.CreateAPIView):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        accommodation_id = data.get('accommodation')
        booking_date = data.get('booking_date')
        booking_time = data.get('booking_time')
        number_of_people = data.get('number_of_people')
        if not accommodation_id or not booking_date or not booking_time or not number_of_people:
            return Response({'error': 'Accommodation, booking_date, booking_time, and number_of_people are required.'}, status=status.HTTP_400_BAD_REQUEST)
        from .models import Accommodation, Booking
        try:
            accommodation = Accommodation.objects.get(pk=accommodation_id)
        except Accommodation.DoesNotExist:
            return Response({'error': 'Accommodation does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        booking = Booking.objects.create(
            user=request.user,
            accommodation=accommodation,
            booking_date=booking_date,
            booking_time=booking_time,
            number_of_people=number_of_people,
            room_type=data.get('room_type', ''),
            special_requests=data.get('special_requests', ''),
        )
        serializer = self.get_serializer(booking)
        return Response({
            'message': 'Booking created successfully.',
            'booking': serializer.data
        }, status=status.HTTP_201_CREATED)

# --- Menu Item Management ---
class MenuItemListCreateView(generics.ListCreateAPIView):
    """
    List all menu items for the logged-in vendor, or create a new one.
    """
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return menu items belonging to the logged-in vendor
        return MenuItem.objects.filter(vendor=self.request.user.vendor_profile)

    def perform_create(self, serializer):
        # Automatically associate the new menu item with the logged-in vendor
        serializer.save(vendor=self.request.user.vendor_profile)

class MenuItemCreateView(generics.CreateAPIView):
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(vendor=self.request.user.vendor_profile)

class MenuItemRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific menu item.
    """
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Ensure vendors can only manage their own menu items
        return MenuItem.objects.filter(vendor=self.request.user.vendor_profile)

class OrderReceiptConfirmationView(APIView):
    """Allow users to confirm they have received their order."""
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            # Get the order that belongs to this user
            order = Order.objects.get(id=order_id, user=request.user)
            
            # Check if order is in a state where receipt can be confirmed
            if not order.payment_confirmed:
                return Response({
                    'error': 'Cannot confirm receipt. Payment has not been confirmed yet.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if order.user_receipt_confirmed:
                return Response({
                    'error': 'Receipt has already been confirmed for this order.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if order.status not in ['delivered', 'ready']:
                return Response({
                    'error': f'Cannot confirm receipt. Order status is "{order.status}".'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Confirm receipt
            order.confirm_user_receipt()
            
            return Response({
                'message': 'Order receipt confirmed successfully.',
                'order_id': order.id,
                'status': order.status,
                'confirmed_at': order.user_receipt_confirmed_at
            }, status=status.HTTP_200_OK)
            
        except Order.DoesNotExist:
            return Response({
                'error': 'Order not found or does not belong to you.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'An error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VendorOrderManagementView(APIView):
    """Allow vendors to manage order status."""
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id, action):
        try:
            # Check if user is a vendor
            try:
                vendor = request.user.vendor_profile
            except VendorProfile.DoesNotExist:
                return Response({
                    'error': 'Only vendors can manage orders.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get the order that belongs to this vendor
            order = Order.objects.get(id=order_id, vendor=vendor)
            
            # Handle different actions
            if action == 'confirm-payment':
                if order.payment_confirmed:
                    return Response({
                        'error': 'Payment has already been confirmed for this order.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                order.confirm_payment()
                message = 'Payment confirmed successfully.'
                
            elif action == 'mark-ready':
                if not order.payment_confirmed:
                    return Response({
                        'error': 'Cannot mark as ready. Payment has not been confirmed yet.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                order.mark_as_ready()
                message = 'Order marked as ready for pickup/delivery.'
                
            elif action == 'out-for-delivery':
                if order.status != 'ready':
                    return Response({
                        'error': 'Order must be ready before marking as out for delivery.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                order.mark_out_for_delivery()
                message = 'Order marked as out for delivery.'
                
            elif action == 'mark-delivered':
                if order.status != 'out_for_delivery':
                    return Response({
                        'error': 'Order must be out for delivery before marking as delivered.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                order.mark_as_delivered()
                message = 'Order marked as delivered.'
                
            else:
                return Response({
                    'error': f'Invalid action: {action}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'message': message,
                'order_id': order.id,
                'status': order.status,
                'updated_at': timezone.now()
            }, status=status.HTTP_200_OK)
            
        except Order.DoesNotExist:
            return Response({
                'error': 'Order not found or does not belong to you.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'An error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VendorOrderTrackingView(APIView):
    """Endpoint for vendors to track their food orders."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            vendor = request.user.vendor_profile
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Only vendors can access this endpoint.'}, status=status.HTTP_403_FORBIDDEN)
        orders = Order.objects.filter(vendor=vendor)
        serializer = VendorOrderTrackingSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
