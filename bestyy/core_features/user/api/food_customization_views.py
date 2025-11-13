"""
Food customization API for menu item variants and cart management
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.contrib.sessions.models import Session
from django.contrib.auth import login
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from bestyy.restaurant_features.product.models import Product as MenuItem
from bestyy.core_features.user.models import VendorProfile, User, Cart, CartItem, Address
from bestyy.restaurant_features.order.models import Order
from bestyy.core_features.user.services.paystack_service import PaystackService
from bestyy.core_features.user.services.crypto_payment_service import CryptoPaymentManager
from bestyy.core_features.user.services.vendor_order_notification_service import VendorOrderNotificationService
from bestyy.core_features.user.services.proximity_courier_service import ProximityCourierService
from bestyy.core_features.user.services.google_maps_service import GoogleMapsService


class MenuItemCustomizationView(APIView):
    """
    Get menu item with available variants for customization modal

    GET /api/user/menu-items/{item_id}/customize/
    """
    permission_classes = [AllowAny]  # Allow viewing customization options

    def get(self, request, item_id):
        """Get menu item with variants for customization"""
        try:
            menu_item = get_object_or_404(MenuItem, id=item_id, available_now=True)

            # Get menu item details (simplified without variants since model was removed)
            item_data = {
                'id': menu_item.id,
                'name': menu_item.name,
                'description': menu_item.description,
                'base_price': float(menu_item.price),
                'currency': 'NGN',
                'image': None,  # Product model doesn't have image field
                'preparation_time': 15,  # Default
                'ingredients': [],  # Product model doesn't have ingredients
                'allergens': [],  # Product model doesn't have allergens
                'is_vegetarian': False,  # Product model doesn't have this
                'is_spicy': False,  # Product model doesn't have this
                'calories': 0,  # Product model doesn't have this
            }

            return Response({
                'success': True,
                'menu_item': item_data,
                'variants': {},  # Empty since MenuItemVariant was removed
                'customization_options': {
                    'allows_special_instructions': True,
                    'max_instructions_length': 500,
                    'special_instructions_placeholder': "Any special requests? (e.g., no onions, extra spicy)"
                }
            }, status=status.HTTP_200_OK)

        except MenuItem.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Menu item not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_optimized_image_url(self, image_field):
        """Get optimized Cloudinary URL for images"""
        if image_field:
            try:
                if hasattr(image_field, 'url'):
                    url = image_field.url
                    if 'cloudinary.com' in url:
                        return url.replace('/upload/', '/upload/w_400,h_400,c_fill,f_auto,q_auto/')
                    return url
                else:
                    return str(image_field)
            except Exception:
                return None
        return None


class AddToCartView(APIView):
    """
    Add customized menu item to session-based cart

    POST /api/user/cart/add/
    """
    permission_classes = [AllowAny]  # Allow anonymous users to add to cart

    def post(self, request):
        """Add customized item to cart with session support"""
        try:
            menu_item_id = request.data.get('menu_item_id')
            quantity = int(request.data.get('quantity', 1))
            special_instructions = (request.data.get('special_instructions') or '').strip()
            variants = request.data.get('variants', {})

            if not menu_item_id:
                return Response({
                    'success': False,
                    'error': 'Menu item ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get menu item and vendor
            menu_item = get_object_or_404(MenuItem, id=menu_item_id, is_available=True)
            vendor = menu_item.vendor

            # Get or create cart for user/vendor combination
            session_key = self._get_session_key(request)
            cart, created = Cart.get_or_create_cart(
                user=request.user if request.user.is_authenticated else None,
                vendor=vendor,
                session_key=session_key
            )

            # Add item to cart
            cart_item, item_created = cart.add_item(
                menu_item=menu_item,
                quantity=quantity,
                variants=variants,
                special_instructions=special_instructions
            )

            return Response({
                'success': True,
                'message': f'{"Added" if item_created else "Updated"} {getattr(menu_item, "dish_name", menu_item.name)} to cart',
                'cart': {
                    'id': cart.id,
                    'item_count': cart.item_count,
                    'total_price': float(cart.total_price),
                    'currency': 'NGN'
                },
                'item': {
                    'id': cart_item.id,
                    'menu_item_id': menu_item.id,
                    'name': getattr(menu_item, 'dish_name', menu_item.name),
                    'quantity': cart_item.quantity,
                    'unit_price': float(cart_item.base_price),
                    'total_price': float(cart_item.total_price),
                    'special_instructions': cart_item.special_instructions
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_session_key(self, request):
        """Get session key for anonymous users"""
        if hasattr(request, 'session'):
            # Accessing request.session creates a session if one doesn't exist
            session_key = request.session.session_key
            if not session_key:
                # Force session creation by setting a dummy value
                request.session['_force_create'] = True
                request.session.save()
                session_key = request.session.session_key
            return session_key
        return None


class CartView(APIView):
    """
    Get user's cart with session support for anonymous users

    GET /api/user/cart/
    POST /api/user/cart/remove/ - Remove item from cart
    """
    permission_classes = [AllowAny]  # Allow anonymous users to view cart

    def get(self, request):
        """Get user's cart contents"""
        try:
            # Get all active carts for the user/session
            session_key = self._get_session_key(request)

            if request.user.is_authenticated:
                # Get all carts for authenticated user
                carts = Cart.objects.filter(
                    user=request.user,
                    is_active=True
                ).select_related('vendor')
            elif session_key:
                # Get carts for anonymous user session
                carts = Cart.objects.filter(
                    session_key=session_key,
                    is_active=True
                ).select_related('vendor')
            else:
                carts = Cart.objects.none()

            cart_data = []
            total_cart_value = 0
            total_items = 0

            for cart in carts:
                items = cart.get_items()
                cart_items_data = []

                for item in items:
                    cart_items_data.append({
                        'id': item.id,
                        'menu_item': {
                            'id': item.menu_item.id,
                            'name': getattr(item.menu_item, 'dish_name', item.menu_item.name),
                            'price': float(item.base_price),
                            'image': self._get_optimized_image_url(getattr(item.menu_item, 'image', None))
                        },
                        'quantity': item.quantity,
                        'variants': item.variants,
                        'special_instructions': item.special_instructions,
                        'total_price': float(item.total_price)
                    })

                cart_data.append({
                    'id': cart.id,
                    'vendor': {
                        'id': cart.vendor.id,
                        'name': cart.vendor.business_name,
                        'logo': self._get_optimized_image_url(cart.vendor.logo)
                    },
                    'items': cart_items_data,
                    'item_count': cart.item_count,
                    'total_price': float(cart.total_price),
                    'currency': 'NGN'
                })

                total_cart_value += float(cart.total_price)
                total_items += cart.item_count

            return Response({
                'success': True,
                'carts': cart_data,
                'summary': {
                    'total_carts': len(cart_data),
                    'total_items': total_items,
                    'total_value': total_cart_value,
                    'currency': 'NGN'
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """Remove item from cart"""
        try:
            cart_item_id = request.data.get('cart_item_id')
            quantity = request.data.get('quantity')  # Optional: remove specific quantity

            if not cart_item_id:
                return Response({
                    'success': False,
                    'error': 'Cart item ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get cart item
            cart_item = get_object_or_404(CartItem, id=cart_item_id)

            # Check ownership
            session_key = self._get_session_key(request)
            if request.user.is_authenticated:
                if cart_item.cart.user != request.user:
                    return Response({
                        'success': False,
                        'error': 'Permission denied'
                    }, status=status.HTTP_403_FORBIDDEN)
            elif cart_item.cart.session_key != session_key:
                return Response({
                    'success': False,
                    'error': 'Permission denied'
                }, status=status.HTTP_403_FORBIDDEN)

            # Remove item from cart
            success, removed_quantity = cart_item.cart.remove_item(
                cart_item.menu_item,
                quantity=quantity
            )

            if success:
                return Response({
                    'success': True,
                    'message': f'Removed {removed_quantity} item(s) from cart',
                    'cart': {
                        'id': cart_item.cart.id,
                        'item_count': cart_item.cart.item_count,
                        'total_price': float(cart_item.cart.total_price),
                        'currency': 'NGN'
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': 'Item not found in cart'
                }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_session_key(self, request):
        """Get session key for anonymous users"""
        if hasattr(request, 'session'):
            # Accessing request.session creates a session if one doesn't exist
            session_key = request.session.session_key
            if not session_key:
                # Force session creation by setting a dummy value
                request.session['_force_create'] = True
                request.session.save()
                session_key = request.session.session_key
            return session_key
        return None

    def _get_optimized_image_url(self, image_field):
        """Get optimized Cloudinary URL for images"""
        if image_field:
            try:
                if hasattr(image_field, 'url'):
                    url = image_field.url
                    if 'cloudinary.com' in url:
                        return url.replace('/upload/', '/upload/w_300,h_300,c_fill,f_auto,q_auto/')
                    return url
                else:
                    return str(image_field)
            except Exception:
                return None
        return None

    def _estimate_delivery_time(self, vendor):
        """Estimate delivery time based on vendor data"""
        base_time = 30
        if hasattr(vendor, 'popularity'):
            if vendor.popularity.orders_last_7_days > 50:
                base_time += 15
            elif vendor.popularity.orders_last_7_days > 20:
                base_time += 10
        return f"{base_time}-{base_time + 10} min"


class CheckoutView(APIView):
    """
    Complete checkout process for web users

    POST /api/user/checkout/
    """
    permission_classes = [AllowAny]  # Allow anonymous checkout (will create account)

    def post(self, request):
        """Process complete checkout with user creation, address saving, and payment"""
        try:
            data = request.data

            # Step 1: Validate cart items
            cart_items = data.get('cart_items', [])
            if not cart_items:
                return Response({
                    'success': False,
                    'error': 'No items in cart'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate and get menu items
            menu_item_ids = []
            quantities_by_id = {}
            for item in cart_items:
                try:
                    mid = int(item.get('menu_item_id'))
                    qty = int(item.get('quantity', 1))
                    if qty < 1:
                        continue
                    menu_item_ids.append(mid)
                    quantities_by_id[mid] = qty
                except (ValueError, TypeError):
                    continue

            if not menu_item_ids:
                return Response({
                    'success': False,
                    'error': 'No valid items found'
                }, status=status.HTTP_400_BAD_REQUEST)

            menu_items = list(MenuItem.objects.filter(id__in=menu_item_ids, is_available=True).select_related('vendor'))
            if len(menu_items) == 0:
                return Response({
                    'success': False,
                    'error': 'No valid items found'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Enforce single vendor
            vendor_ids = {mi.vendor.id for mi in menu_items}
            if len(vendor_ids) > 1:
                return Response({
                    'success': False,
                    'error': 'Cart contains items from multiple vendors'
                }, status=status.HTTP_400_BAD_REQUEST)

            vendor = menu_items[0].vendor

            # Calculate delivery fee based on distance
            delivery_address = data.get('address', {})
            delivery_address_text = f"{delivery_address.get('street_address', '')}, {delivery_address.get('city', '')}, {delivery_address.get('state', '')}"

            # Calculate distance and delivery fee
            maps_service = GoogleMapsService()
            distance_result = maps_service.get_distance_and_price(vendor.business_address, delivery_address_text)

            if distance_result:
                delivery_fee = distance_result['delivery_price']
                estimated_delivery_time = distance_result['duration_text']
            else:
                # Fallback to fixed fee if distance calculation fails
                delivery_fee = 700.0
                estimated_delivery_time = "30-45 minutes"

            # Calculate totals
            subtotal = sum(float(mi.price) * quantities_by_id.get(mi.pk, 0) for mi in menu_items)
            platform_fee = subtotal * 0.05  # 5% platform fee
            grand_total = subtotal + delivery_fee + platform_fee

            # Step 2: Handle user account creation/login
            user = None
            if request.user.is_authenticated:
                user = request.user
            else:
                # Create account for anonymous user
                user_data = data.get('user', {})
                email = user_data.get('email')
                phone = user_data.get('phone')
                first_name = user_data.get('first_name')
                last_name = user_data.get('last_name')
                password = user_data.get('password')

                if not all([email, phone, first_name, last_name, password]):
                    return Response({
                        'success': False,
                        'error': 'User information required for account creation'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Check if user exists
                existing_user = User.objects.filter(email=email).first()
                if existing_user:
                    return Response({
                        'success': False,
                        'error': 'Account with this email already exists. Please login first.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Create new user
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    role='user'
                )

                # Create user profile
                from bestyy.core_features.user.models import UserProfile
                UserProfile.objects.create(
                    user=user,
                    phone=phone
                )

                # Log user in
                login(request, user)

            # Step 3: Handle address creation/saving
            address_data = data.get('address', {})
            address_type = address_data.get('address_type', 'home')
            address_label = address_data.get('label', address_type.title())

            # Check if address already exists
            existing_address = Address.objects.filter(
                user=user,
                address_type=address_type,
                street_address=address_data.get('street_address'),
                city=address_data.get('city')
            ).first()

            if existing_address:
                selected_address = existing_address
            else:
                # Create new address
                selected_address = Address.objects.create(
                    user=user,
                    address_type=address_type,
                    full_name=f"{user.first_name} {user.last_name}",
                    phone_number=address_data.get('phone', user.phone),
                    street_address=address_data.get('street_address'),
                    city=address_data.get('city'),
                    state=address_data.get('state'),
                    postal_code=address_data.get('postal_code', ''),
                    landmark=address_data.get('landmark', ''),
                    is_default=address_data.get('is_default', False)
                )

            # Step 4: Create order
            delivery_address_text = f"{selected_address.street_address}, {selected_address.city}, {selected_address.state}"

            order = Order.objects.create(
                user=user,
                vendor=vendor,
                delivery_address=delivery_address_text,
                total_price=grand_total,
                status='pending',
                payment_method='pending'
            )

            # Add order items
            order_items = []
            for menu_item in menu_items:
                qty = quantities_by_id.get(menu_item.pk, 0)
                if qty > 0:
                    from bestyy.restaurant_features.order.models import OrderItem
                    order_item = OrderItem.objects.create(
                        order=order,
                        menu_item=menu_item,
                        quantity=qty,
                        base_price=menu_item.price,
                        total_price=float(menu_item.price) * qty
                    )
                    order_items.append(order_item)

            # Step 5: Handle payment method
            payment_method = data.get('payment_method')
            payment_instructions = None

            if payment_method == 'bank_transfer':
                paystack_service = PaystackService()
                account_result = paystack_service.create_dedicated_account(user)
                if account_result.get('success'):
                    payment_instructions = {
                        'type': 'bank_transfer',
                        'account_number': account_result['account']['account_number'],
                        'bank_name': account_result['account']['bank_name'],
                        'account_name': account_result['account']['account_name'],
                        'amount': float(grand_total),
                        'reference': f"order_{order.id}"
                    }
                else:
                    return Response({
                        'success': False,
                        'error': 'Failed to create payment account'
                    }, status=status.HTTP_400_BAD_REQUEST)

            elif payment_method == 'debit_card':
                # Initialize Paystack payment
                paystack_service = PaystackService()
                payment_data = {
                    'email': user.email,
                    'amount': int(grand_total * 100),  # Convert to kobo
                    'reference': f"order_{order.id}_{int(timezone.now().timestamp())}",
                    'callback_url': f"{request.build_absolute_uri('/')}api/user/orders/{order.id}/payment-callback/",
                    'metadata': {
                        'order_id': order.id,
                        'user_id': user.id
                    }
                }

                payment_result = paystack_service.initialize_transaction(payment_data)
                if payment_result.get('success'):
                    payment_instructions = {
                        'type': 'debit_card',
                        'authorization_url': payment_result['authorization_url'],
                        'reference': payment_data['reference'],
                        'amount': float(grand_total)
                    }
                else:
                    return Response({
                        'success': False,
                        'error': 'Failed to initialize card payment'
                    }, status=status.HTTP_400_BAD_REQUEST)

            elif payment_method == 'crypto':
                crypto_currency = data.get('crypto_currency', 'usdt')
                crypto_manager = CryptoPaymentManager()
                try:
                    crypto_payment = crypto_manager.create_crypto_payment(order, crypto_currency)
                    payment_instructions = {
                        'type': 'crypto',
                        'currency': crypto_currency,
                        'pay_address': crypto_payment.pay_address,
                        'pay_amount': float(crypto_payment.pay_amount),
                        'payment_id': crypto_payment.nowpayments_payment_id,
                        'amount': float(grand_total)
                    }
                except Exception as e:
                    return Response({
                        'success': False,
                        'error': f'Failed to create crypto payment: {str(e)}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'success': False,
                    'error': 'Invalid payment method'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Step 6: Send vendor notification
            try:
                VendorOrderNotificationService.notify_vendor_new_order(order)
            except Exception as e:
                # Don't fail checkout for notification errors
                print(f"Vendor notification failed: {e}")

            # Step 7: Assign courier (background task would be better)
            try:
                # Convert UUID to int for courier service
                order_id_int = int(str(order.id).replace('-', '')[:8], 16) if hasattr(order.id, 'hex') else int(order.id)
                ProximityCourierService().notify_closest_courier(
                    vendor_id=vendor.id,
                    order_id=order_id_int,
                    notification_type='delivery_assignment'
                )
            except Exception as e:
                # Don't fail checkout for courier assignment errors
                print(f"Courier assignment failed: {e}")

            return Response({
                'success': True,
                'message': 'Order placed successfully! Check your email for confirmation.',
                'order': {
                    'id': order.id,
                    'order_number': f"#{order.id}",
                    'status': order.status,
                    'total_amount': float(grand_total),
                    'currency': 'NGN'
                },
                'payment': payment_instructions,
                'delivery': {
                    'address': {
                        'type': address_type,
                        'label': address_label,
                        'full_address': delivery_address_text
                    },
                    'estimated_time': estimated_delivery_time,
                    'delivery_fee': float(delivery_fee)
                },
                'summary': {
                    'subtotal': float(subtotal),
                    'delivery_fee': float(delivery_fee),
                    'platform_fee': float(platform_fee),
                    'grand_total': float(grand_total),
                    'items_count': len(order_items)
                },
                'next_steps': [
                    '1. Complete payment using the provided instructions',
                    '2. Your order will be prepared by the vendor',
                    '3. A courier will be assigned for delivery',
                    '4. Track your order status in real-time'
                ]
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
