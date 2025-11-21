"""
Order placement and management API
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from decimal import Decimal
from django.db import transaction
from bestyy.core_features.user.models import Address, VendorProfile, Cart, CartItem
from bestyy.restaurant_features.order.models import Order, OrderItem
from bestyy.restaurant_features.product.models import Product as MenuItem
from bestyy.core_features.user.serializers.address_serializers import AddressSerializer
from bestyy.core_features.user.serializers.order_serializers import OrderSerializer
from bestyy.core_features.user.services.paystack_service import PaystackService
from bestyy.core_features.user.services.crypto_payment_service import CryptoPaymentManager
from bestyy.core_features.user.services.automatic_account_service import AutomaticAccountService
from bestyy.core_features.user.services.alternative_suggestions_service import AlternativeSuggestionsService


class PlaceOrderView(APIView):
    """
    Place order from cart and send notifications to vendor
    
    POST /api/user/orders/place/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Place order from cart"""
        try:
            cart_id = request.data.get('cart_id')
            delivery_address_id = request.data.get('delivery_address_id')
            payment_method = request.data.get('payment_method', 'cash')
            delivery_instructions = (request.data.get('delivery_instructions') or '').strip()
            
            if not cart_id:
                return Response({
                    'success': False,
                    'error': 'Cart ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get cart
            cart = get_object_or_404(Cart, id=cart_id, user=request.user, is_active=True)
            
            # Get delivery address
            if delivery_address_id:
                delivery_address = get_object_or_404(Address, id=delivery_address_id, user=request.user)
            else:
                # Get default address
                delivery_address = Address.objects.filter(user=request.user, is_default=True).first()
                if not delivery_address:
                    return Response({
                        'success': False,
                        'error': 'Please select a delivery address'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create order
            order = Order.objects.create(
                customer=request.user,
                vendor=cart.vendor,
                shipping_address=f"{delivery_address.street_address}, {delivery_address.city}, {delivery_address.state}",
                delivery_address=f"{delivery_address.street_address}, {delivery_address.city}, {delivery_address.state}",
                total_amount=cart.total_price,
                status='pending',
                payment_method=payment_method,
                notes=delivery_instructions
            )
            
            # Transfer cart items to order items
            order_items = []
            for cart_item in cart.items.all():
                order_item = OrderItem.objects.create(
                    order=order,
                    menu_item=cart_item.menu_item,
                    quantity=cart_item.quantity,
                    base_price=cart_item.base_price,
                    variants=cart_item.variants,
                    special_instructions=cart_item.special_instructions,
                    total_price=cart_item.total_price
                )
                order_items.append(order_item)
            
            # Deactivate cart
            cart.is_active = False
            cart.save()
            
            # Send notifications to vendor
            notification_results = self._send_vendor_notifications(order, order_items)
            
            # Send automatic reply to vendor
            automatic_reply_results = self._send_automatic_reply(order, order_items)
            
            return Response({
                'success': True,
                'message': 'Order placed successfully',
                'order': {
                    'id': order.id,
                    'order_number': f"#{order.id}",
                    'vendor': {
                        'id': order.vendor.id,
                        'name': order.vendor.business_name,
                        'logo': self._get_optimized_image_url(order.vendor.logo),
                        'delivery_time': self._estimate_delivery_time(order.vendor),
                    },
                    'total_amount': float(order.total_amount),
                    'currency': 'NGN',
                    'status': order.status,
                    'payment_method': order.payment_method,
                    'delivery_address': {
                        'street': delivery_address.street,
                        'city': delivery_address.city,
                        'state': delivery_address.state,
                        'postal_code': delivery_address.postal_code,
                        'landmark': delivery_address.landmark,
                    },
                    'delivery_instructions': order.notes,
                    'order_date': order.created_at.isoformat(),
                    'estimated_delivery': self._calculate_estimated_delivery(order),
                    'items_count': len(order_items),
                },
                'notifications': notification_results,
                'automatic_replies': automatic_reply_results,
                'tracking': {
                    'order_id': order.id,
                    'tracking_url': f"/orders/{order.id}/track",
                    'vendor_contact': {
                        'phone': getattr(order.vendor, 'contact_phone', 'Not available'),
                        'whatsapp': getattr(order.vendor, 'whatsapp_number', 'Not available'),
                    }
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _send_vendor_notifications(self, order, order_items):
        """Send notifications to vendor"""
        try:
            # Prepare order data for notifications
            order_data = {
                'vendor': order.vendor,
                'order': order,
                'order_items': [
                    {
                        'name': item.menu_item.name,
                        'quantity': item.quantity,
                        'base_price': float(item.base_price),
                        'variants': item.variants,
                        'special_instructions': item.special_instructions,
                        'total_price': float(item.total_price)
                    }
                    for item in order_items
                ],
                'customer': {
                    'name': f"{order.user.first_name} {order.user.last_name}".strip(),
                    'email': order.user.email,
                    'phone': getattr(order.user, 'phone', 'Not provided')
                },
                'total_amount': float(order.total_price)
            }
            
            # Send notifications
            results = OrderNotificationService.send_order_placed_notification(order)
            
            return results
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_automatic_reply(self, order, order_items):
        """Send automatic reply to vendor"""
        try:
            # Prepare order data for automatic replies
            order_data = {
                'vendor': order.vendor,
                'order': order,
                'order_items': [
                    {
                        'name': item.menu_item.name,
                        'quantity': item.quantity,
                        'base_price': float(item.base_price),
                        'variants': item.variants,
                        'special_instructions': item.special_instructions,
                        'total_price': float(item.total_price)
                    }
                    for item in order_items
                ],
                'customer': {
                    'name': f"{order.user.first_name} {order.user.last_name}".strip(),
                    'email': order.user.email,
                    'phone': getattr(order.user, 'phone', 'Not provided')
                },
                'total_amount': float(order.total_price)
            }
            
            # Send automatic reply
            results = AutomaticVendorReplyService.send_automatic_reply(order_data, 'order_confirmation')
            
            return results
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_optimized_image_url(self, image_field):
        """Get optimized Cloudinary URL for images"""
        if image_field:
            try:
                if hasattr(image_field, 'url'):
                    url = image_field.url
                    if 'cloudinary.com' in url:
                        return url.replace('/upload/', '/upload/w_200,h_200,c_fill,f_auto,q_auto/')
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
    
    def _calculate_estimated_delivery(self, order):
        """Calculate estimated delivery time"""
        from datetime import timedelta
        base_time = timedelta(minutes=30)
        estimated_delivery = order.order_date + base_time
        return estimated_delivery.isoformat()


class InitializeOrderPaymentView(APIView):
    """
    Initialize payment for an existing order with conditional payouts

    POST /api/user/orders/{order_id}/initialize-payment/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        """Initialize Paystack payment for order with conditional payouts"""
        try:
            # Get order
            order = get_object_or_404(Order, id=order_id, user=request.user)

            # Check if payment already confirmed
            if order.payment_confirmed:
                return Response({
                    'success': False,
                    'error': 'Payment already confirmed for this order'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Calculate distance and delivery fee first
            order.calculate_distance_and_fee()

            # Calculate payout amounts
            payouts = order.calculate_payouts()
            total_amount = payouts['vendor_amount'] + payouts['courier_amount'] + payouts['platform_commission']

            # Create payment reference
            reference = f"order_{order.id}_{int(timezone.now().timestamp())}"

            # Initialize Paystack transaction
            paystack_service = PaystackService()

            payment_data = {
                'email': request.user.email,
                'amount': int(total_amount * 100),  # Convert to kobo
                'reference': reference,
                'callback_url': f"{request.build_absolute_uri('/')}api/user/orders/{order.id}/payment-callback/",
                'metadata': {
                    'order_id': order.id,
                    'user_id': request.user.id,
                    'vendor_amount': float(payouts['vendor_amount']),
                    'courier_amount': float(payouts['courier_amount']),
                    'platform_commission': float(payouts['platform_commission'])
                }
            }

            result = paystack_service.initialize_transaction(payment_data)

            if result['success']:
                # Store payment reference in order (you might want to add a field for this)
                # For now, we'll handle it in the webhook

                return Response({
                    'success': True,
                    'message': 'Payment initialized successfully',
                    'payment': {
                        'reference': reference,
                        'authorization_url': result['authorization_url'],
                        'total_amount': float(total_amount),
                        'breakdown': {
                            'vendor_amount': float(payouts['vendor_amount']),
                            'courier_amount': float(payouts['courier_amount']),
                            'platform_commission': float(payouts['platform_commission'])
                        }
                    },
                    'order': {
                        'id': order.id,
                        'status': order.status
                    }
                }, status=status.HTTP_200_OK)

            return Response({
                'success': False,
                'error': result.get('error', 'Failed to initialize payment')
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyPickupCodeView(APIView):
    """
    Verify pickup code entered by vendor

    POST /api/user/orders/{order_id}/verify-pickup/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        """Verify pickup code and trigger vendor payout"""
        try:
            order = get_object_or_404(Order, id=order_id)
            code = request.data.get('code')

            if not code:
                return Response({
                    'success': False,
                    'error': 'Pickup code is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if user is the vendor
            if request.user != order.vendor.user:
                return Response({
                    'success': False,
                    'error': 'Only the assigned vendor can verify pickup codes'
                }, status=status.HTTP_403_FORBIDDEN)

            # Verify the code
            if order.verify_pickup_code(code):
                # Trigger vendor payout
                payout_success = order.trigger_vendor_payout()

                return Response({
                    'success': True,
                    'message': 'Pickup code verified successfully',
                    'payout_triggered': payout_success,
                    'order': {
                        'id': order.id,
                        'status': order.status,
                        'vendor_paid': order.vendor_paid
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': 'Invalid pickup code'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyDeliveryCodeView(APIView):
    """
    Verify delivery code entered by courier

    POST /api/user/orders/{order_id}/verify-delivery/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        """Verify delivery code and trigger courier payout"""
        try:
            order = get_object_or_404(Order, id=order_id)
            code = request.data.get('code')

            if not code:
                return Response({
                    'success': False,
                    'error': 'Delivery code is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if user is the courier
            if order.courier and request.user != order.courier.user:
                return Response({
                    'success': False,
                    'error': 'Only the assigned courier can verify delivery codes'
                }, status=status.HTTP_403_FORBIDDEN)

            # Verify the code
            if order.verify_delivery_otp(code):
                # Mark order as delivered
                order.mark_as_delivered()

                # Trigger courier payout
                payout_success = order.trigger_courier_payout()

                return Response({
                    'success': True,
                    'message': 'Delivery code verified successfully',
                    'payout_triggered': payout_success,
                    'order': {
                        'id': order.id,
                        'status': order.status,
                        'courier_paid': order.courier_paid
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': 'Invalid delivery code'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderSummaryView(APIView):
    """
    Get order summary with commission and shipping calculations

    GET /api/user/orders/summary/{cart_id}/
    POST /api/user/orders/summary/{cart_id}/ (for guest checkout with account creation)
    """
    permission_classes = []  # Allow anonymous access for guest checkout

    def get(self, request, cart_id):
        """Get order summary with all calculations"""
        try:
            # Get cart
            cart = get_object_or_404(Cart, id=cart_id, user=request.user, is_active=True)

            # Get system settings for calculations
            settings = SystemSettings.get_active_settings()

            # Calculate item totals
            subtotal = cart.total_price
            items_count = cart.items.count()

            # Calculate commission (platform fee)
            commission = subtotal * (settings['service_fee_percentage'] / Decimal('100'))

            # Calculate shipping fee (base + per km if applicable)
            shipping_fee = settings['base_delivery_fee']

            # Calculate total
            total = subtotal + commission + shipping_fee

            # Get delivery address if available
            delivery_address = None
            default_address = Address.objects.filter(user=request.user, is_default=True).first()
            if default_address:
                delivery_address = {
                    'id': default_address.id,
                    'full_name': default_address.full_name,
                    'street_address': default_address.street_address,
                    'city': default_address.city,
                    'state': default_address.state,
                    'phone': default_address.phone_number
                }

            return Response({
                'success': True,
                'summary': {
                    'cart_id': cart.id,
                    'vendor': {
                        'id': cart.vendor.id,
                        'name': cart.vendor.business_name,
                        'logo': self._get_optimized_image_url(cart.vendor.logo)
                    },
                    'items': [
                        {
                            'id': item.id,
                            'name': item.menu_item.name,
                            'quantity': item.quantity,
                            'unit_price': float(item.base_price),
                            'total_price': float(item.total_price),
                            'image': self._get_optimized_image_url(item.menu_item.image)
                        }
                        for item in cart.items.all()
                    ],
                    'calculations': {
                        'subtotal': float(subtotal),
                        'commission_percentage': float(settings.service_fee_percentage),
                        'commission_amount': float(commission),
                        'shipping_fee': float(shipping_fee),
                        'total': float(total),
                        'currency': 'NGN'
                    },
                    'items_count': items_count,
                    'delivery_address': delivery_address,
                    'estimated_delivery_time': self._estimate_delivery_time(cart.vendor)
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderConfirmationView(APIView):
    """
    Order confirmation and tracking page endpoint

    GET /api/user/orders/{order_id}/confirmation/
    POST /api/user/orders/{order_id}/confirm-payment/
    Returns complete order details with real-time tracking information
    """
    permission_classes = []  # Allow public access for order tracking and payment confirmation

    def get(self, request, pk):
        """Get complete order confirmation and tracking data"""
        try:
            # Get order - allow access without authentication for tracking
            order = get_object_or_404(Order, id=pk)

            # If user is authenticated, check ownership (optional security)
            if hasattr(request, 'user') and request.user.is_authenticated:
                if order.customer != request.user and not request.user.is_staff:
                    # Allow access but mark as public view
                    pass

            # Generate delivery OTP if not exists
            if not getattr(order, 'delivery_otp', None):
                try:
                    # Generate OTP using the model's method
                    otp = order.generate_delivery_otp()
                    print(f"Generated delivery OTP for order {order.id}: {otp}")
                except Exception as e:
                    # Log error but don't fail the request
                    print(f"Failed to generate delivery OTP: {e}")
                    # Fallback: generate OTP manually
                    import random
                    otp = ''.join(random.choices('0123456789', k=6))
                    order.delivery_otp = otp
                    order.save()
                    print(f"Generated fallback delivery OTP for order {order.id}: {otp}")

            # Get order items
            order_items = []
            subtotal = 0
            for item in order.items.all():
                item_data = {
                    'id': item.id,
                    'name': item.product.name if item.product else 'Unknown Item',
                    'description': getattr(item.product, 'description', '') if item.product else '',
                    'quantity': item.quantity,
                    'unit_price': float(item.price),
                    'total_price': float(item.total_price),
                    'image': self._get_optimized_image_url(getattr(item.product, 'image', None)) if item.product else None,
                    'customizations': getattr(item, 'variants', {}) or {}
                }
                order_items.append(item_data)
                subtotal += item.total_price

            # Calculate fees (match OrderSummaryView calculation)
            from bestyy.core_features.user.models import SystemSettings
            settings = SystemSettings.get_active_settings()

            # Calculate commission (platform fee)
            service_fee_percentage = Decimal(str(settings['service_fee_percentage'])) / Decimal('100')
            service_fee = subtotal * service_fee_percentage

            # Calculate shipping fee (base + per km if applicable)
            delivery_fee = Decimal(str(settings['base_delivery_fee']))

            # Calculate total (match OrderSummaryView)
            total_amount = subtotal + service_fee + delivery_fee

            # Build order timeline
            timeline = self._build_order_timeline(order)

            # Get payment status
            payment_status = self._get_payment_status(order)

            # Get PwT details for bank transfer orders
            pwt_details = None
            if order.payment_method == 'bank_transfer' and not getattr(order, 'payment_confirmed', False):
                dva_details = self._get_dva_details(order)

            # Get courier info if assigned
            courier_info = None
            if hasattr(order, 'courier') and order.courier:
                courier_info = {
                    'id': order.courier.id,
                    'name': f"{order.courier.user.first_name} {order.courier.user.last_name}".strip(),
                    'phone': getattr(order.courier, 'phone', 'Not available'),
                    'vehicle_type': getattr(order.courier, 'vehicle_type', 'Bike'),
                    'rating': 4.5  # Placeholder
                }

            # Get vendor info
            vendor_info = {
                'id': order.vendor.id,
                'name': order.vendor.business_name,
                'logo': self._get_optimized_image_url(order.vendor.logo),
                'phone': getattr(order.vendor, 'phone', 'Not available'),
                'address': order.vendor.business_address,
                'rating': 4.2  # Placeholder
            }

            response_data = {
                'success': True,
                'order': {
                    'id': order.id,
                    'order_number': f"#{order.id}",
                    'status': order.status,
                    'status_display': self._get_status_display(order.status),
                    'created_at': order.created_at.isoformat() if order.created_at else None,
                    'estimated_delivery': self._calculate_estimated_delivery(order),
                    'special_instructions': getattr(order, 'notes', ''),
                    'payment_method': order.payment_method,
                    'payment_confirmed': getattr(order, 'payment_confirmed', False),
                    'payment_confirmed_at': getattr(order, 'payment_confirmed_at', None).isoformat() if getattr(order, 'payment_confirmed_at', None) else None,
                    'delivery_otp': getattr(order, 'delivery_otp', None),
                    'pickup_code': getattr(order, 'pickup_code', None)
                },
                'customer': {
                    'name': f"{order.customer.first_name} {order.customer.last_name}".strip() if order.customer else 'Anonymous User',
                    'phone': getattr(order.customer, 'phone', None) if order.customer else None,
                    'email': order.customer.email if order.customer else 'Not provided'
                },
                'vendor': vendor_info,
                'courier': courier_info,
                'items': order_items,
                'pricing': {
                    'subtotal': float(subtotal),
                    'delivery_fee': float(delivery_fee),
                    'service_fee': float(service_fee),
                    'total': float(total_amount),
                    'currency': 'NGN'
                },
                'delivery': {
                    'address': order.delivery_address,
                    'otp_instructions': 'Give this OTP code to the courier when they deliver your order',
                    'estimated_time': '30-45 minutes'
                },
                'timeline': timeline,
                'payment': payment_status,
                'dva_details': dva_details,
                'login_instructions': None,
                'actions': self._get_available_actions(order),
                'support': {
                    'phone': '0800-BESTYY',
                    'email': 'support@bestyy.com',
                    'whatsapp': 'https://wa.me/234800BESTYY',
                    'chat_url': '/support/chat'
                },
                'websocket': {
                    'url': f'/ws/orders/{order.id}/track/',
                    'enabled': True
                }
            }

            if dva_details and not (request.user and request.user.is_authenticated):
                # Preserve any guest user credentials if generated at order placement
                if hasattr(order, 'guest_login') and order.guest_login:
                    response_data['login_instructions'] = {
                        'login_url': '/login/',
                        'username': order.guest_login.get('username'),
                        'password': order.guest_login.get('password'),
                        'note': 'Use these credentials to log in and track your order, or update your account information.'
                    }
                else:
                    response_data['login_instructions'] = {
                        'login_url': '/login/',
                        'note': 'If you placed this order as a guest, log in to manage your order using the account created with your order email/phone.'
                    }

            return Response(response_data, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Order not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _build_order_timeline(self, order):
        """Build order status timeline"""
        timeline = []

        # Helper function to safely get timestamp
        def get_timestamp(field_name, fallback=None):
            value = getattr(order, field_name, fallback or order.created_at)
            if value:
                return value.isoformat()
            return order.created_at.isoformat() if order.created_at else None

        # Order placed
        if order.created_at:
            timeline.append({
                'status': 'placed',
                'title': 'Order Placed',
                'description': 'Your order has been received',
                'timestamp': order.created_at.isoformat(),
                'completed': True,
                'icon': 'shopping-cart'
            })

        # Payment confirmed
        if getattr(order, 'payment_confirmed', False):
            timeline.append({
                'status': 'payment_confirmed',
                'title': 'Payment Confirmed',
                'description': 'Payment has been received and confirmed',
                'timestamp': get_timestamp('payment_confirmed_at'),
                'completed': True,
                'icon': 'credit-card'
            })

        # Order confirmed/accepted
        if order.status in ['confirmed', 'preparing', 'ready', 'out_for_delivery', 'delivered']:
            timeline.append({
                'status': 'confirmed',
                'title': 'Order Confirmed',
                'description': 'Vendor has accepted your order',
                'timestamp': get_timestamp('confirmed_at'),
                'completed': True,
                'icon': 'check-circle'
            })

        # Preparing
        if order.status in ['preparing', 'ready', 'out_for_delivery', 'delivered']:
            timeline.append({
                'status': 'preparing',
                'title': 'Preparing Order',
                'description': 'Your order is being prepared',
                'timestamp': get_timestamp('preparing_at'),
                'completed': order.status != 'confirmed',
                'icon': 'chef-hat'
            })

        # Ready for pickup
        if order.status in ['ready', 'out_for_delivery', 'delivered']:
            timeline.append({
                'status': 'ready',
                'title': 'Ready for Delivery',
                'description': 'Order is ready and waiting for courier pickup',
                'timestamp': get_timestamp('ready_at'),
                'completed': order.status != 'preparing',
                'icon': 'package'
            })

        # Out for delivery
        if order.status in ['out_for_delivery', 'delivered']:
            timeline.append({
                'status': 'out_for_delivery',
                'title': 'Out for Delivery',
                'description': 'Courier is on the way with your order',
                'timestamp': get_timestamp('out_for_delivery_at'),
                'completed': order.status != 'ready',
                'icon': 'truck'
            })

        # Delivered
        if order.status == 'delivered':
            timeline.append({
                'status': 'delivered',
                'title': 'Delivered',
                'description': 'Order has been delivered successfully',
                'timestamp': get_timestamp('delivered_at'),
                'completed': True,
                'icon': 'check-circle'
            })

        return timeline

    def _get_payment_status(self, order):
        """Get detailed payment status"""
        if getattr(order, 'payment_confirmed', False):
            return {
                'status': 'confirmed',
                'message': 'Payment confirmed',
                'confirmed_at': getattr(order, 'payment_confirmed_at', None),
                'method': order.payment_method,
                'reference': getattr(order, 'payment_reference', None)
            }
        else:
            return {
                'status': 'pending',
                'message': 'Waiting for payment confirmation',
                'method': order.payment_method,
                'reference': getattr(order, 'payment_reference', None)
            }

    def _get_status_display(self, status):
        """Get human-readable status"""
        status_map = {
            'pending': 'Order Received',
            'confirmed': 'Order Confirmed',
            'preparing': 'Preparing Order',
            'ready': 'Ready for Delivery',
            'out_for_delivery': 'Out for Delivery',
            'delivered': 'Delivered',
            'cancelled': 'Cancelled'
        }
        return status_map.get(status, status.title())

    def _calculate_estimated_delivery(self, order):
        """Calculate estimated delivery time"""
        from datetime import timedelta
        if not order.created_at:
            return None
        base_time = timedelta(minutes=45)  # 45 minutes total
        estimated_delivery = order.created_at + base_time
        return estimated_delivery.isoformat()

    def _get_available_actions(self, order):
        """Get available actions for the current order status"""
        actions = []

        # Payment actions for bank transfer orders
        if (order.payment_method == 'bank_transfer' and
            not getattr(order, 'payment_confirmed', False)):
            actions.append({
                'type': 'payment_transferred',
                'label': 'I\'ve Transferred the Money',
                'description': 'Click here after transferring money to verify payment',
                'primary': True
            })

        if order.status == 'pending':
            actions.append({
                'type': 'cancel',
                'label': 'Cancel Order',
                'description': 'Cancel this order'
            })

        if order.status in ['ready', 'out_for_delivery']:
            actions.append({
                'type': 'call_courier',
                'label': 'Call Courier',
                'description': 'Contact your delivery courier'
            })

        if order.status == 'delivered':
            actions.append({
                'type': 'rate_order',
                'label': 'Rate Order',
                'description': 'Rate your order experience'
            })
            actions.append({
                'type': 'reorder',
                'label': 'Reorder',
                'description': 'Order these items again'
            })

        # Always available
        actions.extend([
            {
                'type': 'call_support',
                'label': 'Contact Support',
                'description': 'Get help with your order'
            },
            {
                'type': 'call_vendor',
                'label': 'Call Vendor',
                'description': 'Contact the restaurant'
            }
        ])

        return actions

    def post(self, request, pk):
        """Handle manual payment confirmation trigger"""
        try:
            # Get order
            order = get_object_or_404(Order, id=pk)

            # Check action type
            action = request.data.get('action')
            if action != 'payment_transferred':
                return Response({
                    'success': False,
                    'error': f'Invalid action: {action}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if payment is already confirmed
            if getattr(order, 'payment_confirmed', False):
                return Response({
                    'success': False,
                    'error': 'Payment already confirmed'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if payment method is bank transfer
            if order.payment_method != 'bank_transfer':
                return Response({
                    'success': False,
                    'error': 'This action is only available for bank transfer payments'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Trigger manual payment verification
            verification_result = self._trigger_payment_verification(order)

            if verification_result.get('success'):
                return Response({
                    'success': True,
                    'message': 'Payment verification initiated. Please wait...',
                    'verification_status': verification_result.get('status', 'processing')
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': verification_result.get('error', 'Verification failed'),
                    'message': 'Please try again or contact support if the issue persists'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Order.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Order not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        """Handle guest checkout with automatic account creation"""
        try:
            # Get cart
            cart = get_object_or_404(Cart, id=cart_id, is_active=True)

            # Check if cart has a user (should be anonymous)
            if cart.user and cart.user.is_authenticated:
                return Response({
                    'success': False,
                    'error': 'This endpoint is for guest checkout only'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get guest info from request
            guest_info = request.data.get('guest_info', {})
            if not guest_info:
                return Response({
                    'success': False,
                    'error': 'Guest information required for checkout'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get delivery address
            delivery_address_id = request.data.get('delivery_address_id')
            address_fields = request.data.get('address')

            if delivery_address_id:
                # This shouldn't happen for guest checkout, but handle it
                return Response({
                    'success': False,
                    'error': 'Address ID not supported for guest checkout'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not address_fields:
                return Response({
                    'success': False,
                    'error': 'Delivery address required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate address fields
            street_address = address_fields.get('street_address', '').strip()
            city = address_fields.get('city', '').strip()
            state = address_fields.get('state', '').strip()

            if not street_address or not city or not state:
                return Response({
                    'success': False,
                    'error': 'Street address, city, and state are required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create order (similar to PlaceOrderView but for guest)
            delivery_address_text = f"{street_address}, {city}, {state}"
            postal_code = address_fields.get('postal_code')
            if postal_code:
                delivery_address_text += f" {postal_code}"

            order = Order.objects.create(
                customer=None,  # Will be set by account creation service
                vendor=cart.vendor,
                shipping_address=delivery_address_text,
                delivery_address=delivery_address_text,
                total_amount=cart.total_price,
                status='pending',
                payment_method='bank_transfer',  # Default for guest checkout
                notes=request.data.get('order_note', '')
            )

            # Transfer cart items to order items
            order_items = []
            for cart_item in cart.items.all():
                order_item = OrderItem.objects.create(
                    order=order,
                    menu_item=cart_item.menu_item,
                    quantity=cart_item.quantity,
                    base_price=cart_item.base_price,
                    variants=cart_item.variants,
                    special_instructions=cart_item.special_instructions,
                    total_price=cart_item.total_price
                )
                order_items.append(order_item)

            # Deactivate cart
            cart.is_active = False
            cart.save()

            # Create account and assign to order
            account_user, account_message, credentials = AutomaticAccountService.create_or_reuse_account_for_order(order, guest_info)

            # Calculate fees for response
            subtotal = cart.total_price
            service_fee = subtotal * Decimal('0.05')  # 5% service fee
            total_amount = subtotal + service_fee

            return Response({
                'success': True,
                'message': 'Order placed successfully',
                'order': {
                    'id': order.id,
                    'order_number': f"#{order.id}",
                    'vendor': {
                        'id': order.vendor.id,
                        'name': order.vendor.business_name,
                        'logo': self._get_optimized_image_url(order.vendor.logo),
                    },
                    'total_amount': float(order.total_amount),
                    'currency': 'NGN',
                    'status': order.status,
                    'payment_method': order.payment_method,
                    'delivery_address': delivery_address_text,
                    'order_date': order.created_at.isoformat(),
                    'items_count': len(order_items),
                },
                'account': {
                    'account_created': account_user is not None,
                    'message': account_message,
                    'credentials': credentials if account_user else {}
                },
                'pricing': {
                    'subtotal': float(subtotal),
                    'service_fee': float(service_fee),
                    'total': float(total_amount),
                    'currency': 'NGN'
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _trigger_payment_verification(self, order):
        """Trigger manual payment verification using Paystack or demo confirmation"""
        try:
            from bestyy.core_features.user.services.paystack_service import PaystackService

            # Generate reference if not exists
            reference = getattr(order, 'payment_reference', None)
            if not reference:
                reference = f"order_{order.id}_{int(timezone.now().timestamp())}"
                order.payment_reference = reference
                order.save()

            # Check if this is a demo account (fake account number)
            dva_details = self._get_dva_details(order)
            is_demo = dva_details.get('is_demo', False)

            if is_demo:
                # For demo accounts, auto-confirm payment immediately
                order.payment_confirmed = True
                order.payment_confirmed_at = timezone.now()
                order.status = 'confirmed'
                order.save()

                # Trigger post-payment processes
                self._process_payment_confirmation(order)

                return {
                    'success': True,
                    'status': 'confirmed',
                    'message': 'Demo payment confirmed successfully'
                }

            # For real accounts, verify with Paystack
            paystack_service = PaystackService()
            result = paystack_service.verify_transaction(reference)

            if result.get('success'):
                data = result.get('data', {})
                transaction_status = data.get('status')

                if transaction_status == 'success':
                    # Auto-confirm the payment
                    order.payment_confirmed = True
                    order.payment_confirmed_at = timezone.now()
                    order.status = 'confirmed'
                    order.save()

                    # Trigger post-payment processes
                    self._process_payment_confirmation(order)

                    return {
                        'success': True,
                        'status': 'confirmed',
                        'message': 'Payment confirmed successfully'
                    }
                else:
                    return {
                        'success': False,
                        'status': transaction_status,
                        'error': f'Payment status: {transaction_status}'
                    }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Could not verify payment'),
                    'status': 'verification_failed'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Verification error: {str(e)}',
                'status': 'error'
            }

    def _process_payment_confirmation(self, order):
        """Process payment confirmation (extracted from webhook handler)"""
        try:
            # Generate codes for conditional payouts
            if hasattr(order, 'generate_pickup_code'):
                order.generate_pickup_code()
            if hasattr(order, 'generate_delivery_otp'):
                order.generate_delivery_otp()

            # Send WhatsApp notifications
            from bestyy.core_features.user.api.paystack_webhooks import _send_code_notifications, _send_payment_receipt
            _send_code_notifications(order)
            _send_payment_receipt(order)

            # Broadcast payment confirmation via WebSocket
            from bestyy.core_features.user.services.order_status_broadcast_service import OrderStatusBroadcastService
            OrderStatusBroadcastService.broadcast_payment_confirmed(order)

            # Notify vendor about new order
            from bestyy.core_features.user.services.vendor_order_notification_service import VendorOrderNotificationService
            VendorOrderNotificationService.notify_vendor_new_order(order)

            # Find and assign nearby courier
            from bestyy.core_features.user.services.courier_location_service import CourierLocationService
            try:
                # Get delivery location coordinates (simplified)
                delivery_lat = 6.5244  # Lagos latitude
                delivery_lon = 3.3792  # Lagos longitude

                nearby_couriers = CourierLocationService.find_nearby_couriers(
                    delivery_lat, delivery_lon,
                    max_distance_km=15.0,
                    max_results=3,
                    require_active=True,
                    require_verified=True
                )

                if nearby_couriers:
                    closest_courier, distance = nearby_couriers[0]
                    order.courier = closest_courier
                    order.save()

                    # Send notification to assigned courier
                    _send_code_notifications(order)

                    # Broadcast courier assignment
                    OrderStatusBroadcastService.broadcast_new_delivery_request(order, nearby_couriers)

            except Exception as e:
                pass  # Continue even if courier assignment fails

        except Exception as e:
            pass  # Continue even if post-processing fails

    def _get_dva_details(self, order):
        """Get Pay with Transfer bank details for the order"""
        try:
            from bestyy.core_features.user.services.paystack_service import PaystackService

            # Generate payment reference if not exists
            reference = getattr(order, 'payment_reference', None)
            if not reference:
                reference = f"order_{order.id}_{int(timezone.now().timestamp())}"
                order.payment_reference = reference
                order.save()

            # Use Pay with Transfer for all users
            paystack_service = PaystackService()
            amount_kobo = int(order.total_amount * 100)  # Convert to kobo

            result = paystack_service.initialize_pay_with_transfer(
                email=order.customer.email if order.customer else 'guest@bestyy.com',
                amount=amount_kobo,
                reference=reference,
                expiry_hours=8
            )

            if result.get('success') and result.get('account_details'):
                account_details = result['account_details']
                return {
                    'account_number': account_details['account_number'],
                    'account_name': account_details['account_name'],
                    'bank_name': account_details['bank_name'],
                    'amount': account_details['amount_expected'],
                    'reference': reference,
                    'instructions': [
                        '1. Copy the account details above',
                        '2. Transfer the exact amount to this account',
                        '3. Use the reference number as payment reference',
                        '4. Click "I\'ve Transferred the Money" button below',
                        '5. Your payment will be verified automatically'
                    ],
                    'expires_at': account_details.get('expires_at'),
                    'expires_in': '8 hours',
                    'support_contact': '0800-BESTYY'
                }
            else:
                # Fallback to generic account if PwT fails
                import random
                account_number = f"{random.randint(200, 999)}{random.randint(1000000, 9999999)}"

                return {
                    'account_number': account_number,
                    'account_name': 'Bestyy Customer Account',
                    'bank_name': 'Titan Paystack',
                    'amount': float(order.total_amount),
                    'reference': reference,
                    'instructions': [
                        '1. Copy the account details above',
                        '2. Transfer the exact amount to this account',
                        '3. Use the reference number as payment reference',
                        '4. Click "I\'ve Transferred the Money" button below',
                        '5. Your payment will be verified automatically',
                        '6. If you\'re not logged in, please login/register to confirm payment'
                    ],
                    'expires_in': '8 hours',
                    'support_contact': '0800-BESTYY'
                }

        except Exception as e:
            return {
                'error': 'Payment setup failed',
                'message': 'Please contact support for assistance',
                'support_contact': '0800-BESTYY'
            }

    def _get_optimized_image_url(self, image_field):
        """Get optimized Cloudinary URL for images"""
        if image_field:
            try:
                if hasattr(image_field, 'url'):
                    url = image_field.url
                    if 'cloudinary.com' in url:
                        return url.replace('/upload/', '/upload/w_200,h_200,c_fill,f_auto,q_auto/')
                    return url
                else:
                    return str(image_field)
            except Exception:
                return None
        return None


class OrderStatusView(APIView):
    """
    Update order status (for vendors)
    
    PUT /api/user/orders/{order_id}/status/
    """
    permission_classes = [IsAuthenticated]
    
    def put(self, request, order_id):
        """Update order status"""
        try:
            order = get_object_or_404(Order, id=order_id)
            
            # Check if user is the vendor or admin
            if not (request.user == order.vendor.user or request.user.is_staff):
                return Response({
                    'success': False,
                    'error': 'Permission denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            new_status = request.data.get('status')
            status_choices = ['pending', 'confirmed', 'preparing', 'ready', 'out_for_delivery', 'delivered', 'cancelled']
            
            if new_status not in status_choices:
                return Response({
                    'success': False,
                    'error': f'Invalid status. Must be one of: {", ".join(status_choices)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            old_status = order.status
            order.status = new_status
            
            # Add status update timestamp
            if new_status == 'confirmed':
                order.confirmed_at = timezone.now()
            elif new_status == 'preparing':
                order.preparing_at = timezone.now()
            elif new_status == 'ready':
                order.ready_at = timezone.now()
            elif new_status == 'out_for_delivery':
                order.out_for_delivery_at = timezone.now()
            elif new_status == 'delivered':
                order.delivered_at = timezone.now()
            elif new_status == 'cancelled':
                order.cancelled_at = timezone.now()
            
            order.save()

            # If order was cancelled, automatically send similar food suggestions to customer
            if new_status == 'cancelled' and old_status != 'cancelled':
                self._send_similar_food_suggestions(order)

            return Response({
                'success': True,
                'message': f'Order status updated from {old_status} to {new_status}',
                'order': {
                    'id': order.id,
                    'status': order.status,
                    'status_updated_at': timezone.now().isoformat(),
                    'estimated_delivery': self._calculate_estimated_delivery(order),
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _calculate_estimated_delivery(self, order):
        """Calculate estimated delivery time"""
        from datetime import timedelta
        base_time = timedelta(minutes=30)
        estimated_delivery = order.order_date + base_time
        return estimated_delivery.isoformat()

    def _send_similar_food_suggestions(self, order):
        """Send similar food suggestions to customer when order is cancelled"""
        try:
            # Get order items to find similar suggestions
            order_items = order.items.all()
            if not order_items:
                return

            # Get the most expensive item as the primary reference (or first item)
            primary_item = order_items.order_by('-total_price').first()
            if not primary_item or not primary_item.product:
                return

            item_name = primary_item.product.dish_name or primary_item.product.name

            # Use AlternativeSuggestionsService to generate recommendations
            alt_service = AlternativeSuggestionsService()
            suggestions = alt_service.generate_item_alternatives(
                unavailable_item=item_name,
                user_budget=float(order.total_amount) if order.total_amount else None
            )

            # Format suggestions for customer notification
            if suggestions and (suggestions.get('substitutes') or suggestions.get('similar_category')):
                self._notify_customer_similar_suggestions(order, suggestions, item_name)

        except Exception as e:
            # Log error but don't fail the order status update
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send similar food suggestions for cancelled order {order.id}: {str(e)}")

    def _notify_customer_similar_suggestions(self, order, suggestions, original_item_name):
        """Send notification to customer with similar food suggestions"""
        try:
            # Prepare rich notification data with complete item details
            notification_data = {
                'type': 'order.cancelled_suggestions',
                'order_id': order.id,
                'original_item': original_item_name,
                'suggestions': suggestions,
                'message': f"We're sorry your order for {original_item_name} was cancelled. Here are some similar alternatives you might enjoy:",
                'timestamp': timezone.now().isoformat(),
                'action_required': 'Choose an alternative or contact support',
                'support_options': {
                    'email': 'support@bestyy.com',
                    'phone': '0800-BESTYY',
                    'chat': '/support/chat'
                },
                'quick_actions': [
                    {'type': 'reorder', 'label': 'Reorder Original', 'item': original_item_name},
                    {'type': 'view_suggestions', 'label': 'View All Suggestions', 'url': f'/suggestions?item={original_item_name}'},
                    {'type': 'contact_support', 'label': 'Contact Support', 'url': '/support'}
                ]
            }

            # Send WebSocket notification to customer
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer:
                customer_group_name = f'customer_{order.customer.id}'
                async_to_sync(channel_layer.group_send)(
                    customer_group_name,
                    {
                        'type': 'similar_food_suggestions',
                        'data': notification_data
                    }
                )

            # Also send email notification if customer has email
            if order.customer and order.customer.email:
                self._send_suggestions_email(order, suggestions, original_item_name)

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to notify customer of similar suggestions: {str(e)}")

    def _send_suggestions_email(self, order, suggestions, original_item_name):
        """Send email with similar food suggestions"""
        try:
            from django.core.mail import send_mail
            from django.conf import settings

            customer = order.customer
            if not customer or not customer.email:
                return

            # Create email content
            subject = f"Alternative Food Suggestions - Order #{order.id}"

            # Build rich suggestions text with complete details
            suggestions_text = ""
            substitutes = suggestions.get('substitutes', [])[:3]  # Top 3 substitutes
            similar_category = suggestions.get('similar_category', [])[:2]  # Top 2 similar
            budget_alternatives = suggestions.get('budget_alternatives', [])[:2]  # Top 2 budget options

            if substitutes:
                suggestions_text += "\n🍽️ *Exact Substitutes (Same Item, Different Vendors):*\n"
                for i, sub in enumerate(substitutes, 1):
                    suggestions_text += f"""
{i}. 🍕 {sub.get('name', 'N/A')}
   💰 Price: ₦{sub.get('price', 'N/A'):,}
   🏪 Vendor: {sub.get('vendor_name', 'N/A')} ({sub.get('vendor_rating', 4.0)}⭐)
   🕐 Delivery: {sub.get('delivery_time', '20-45 min')}
   📍 Location: {sub.get('vendor_address', 'N/A')[:50]}...
"""
                    if sub.get('image'):
                        suggestions_text += f"   🖼️ Image: {sub.get('image')}\n"
                    if sub.get('description'):
                        suggestions_text += f"   📝 Description: {sub.get('description')[:100]}...\n"

            if similar_category:
                suggestions_text += "\n🥘 *Similar Dishes (Same Category):*\n"
                for i, sim in enumerate(similar_category, 1):
                    suggestions_text += f"""
{i}. 🍽️ {sim.get('name', 'N/A')}
   💰 Price: ₦{sim.get('price', 'N/A'):,}
   🏪 Vendor: {sim.get('vendor_name', 'N/A')} ({sim.get('vendor_rating', 4.0)}⭐)
   🕐 Delivery: {sim.get('delivery_time', '20-45 min')}
   📍 Location: {sim.get('vendor_address', 'N/A')[:50]}...
"""
                    if sim.get('image'):
                        suggestions_text += f"   🖼️ Image: {sim.get('image')}\n"
                    if sim.get('description'):
                        suggestions_text += f"   📝 Description: {sim.get('description')[:100]}...\n"

            if budget_alternatives:
                suggestions_text += "\n💰 *Budget-Friendly Alternatives:*\n"
                for i, alt in enumerate(budget_alternatives, 1):
                    savings = alt.get('savings', 0)
                    suggestions_text += f"""
{i}. 🍲 {alt.get('name', 'N/A')}
   💰 Price: ₦{alt.get('price', 'N/A'):,} (Save ₦{savings:,.0f}!)
   🏪 Vendor: {alt.get('vendor_name', 'N/A')} ({alt.get('vendor_rating', 4.0)}⭐)
   🕐 Delivery: {alt.get('delivery_time', '20-45 min')}
   📍 Location: {alt.get('vendor_address', 'N/A')[:50]}...
"""
                    if alt.get('image'):
                        suggestions_text += f"   🖼️ Image: {alt.get('image')}\n"
                    if alt.get('description'):
                        suggestions_text += f"   📝 Description: {alt.get('description')[:100]}...\n"

            body = f"""
Dear {customer.first_name or 'Valued Customer'},

We're sorry to inform you that your order for "{original_item_name}" has been cancelled.

To help you find something delicious to enjoy instead, here are some similar food suggestions from our partner vendors:

{suggestions_text}

You can browse these alternatives in the Bestyy app or visit our website to place a new order.

If you have any questions about your order or need assistance, please don't hesitate to contact our support team.

Best regards,
The Bestyy Team

---
This is an automated message. For support, please contact us through the Bestyy platform.
"""

            # Send email
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[customer.email],
                fail_silently=True,
            )

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send suggestions email: {str(e)}")


class UnifiedCheckoutView(APIView):
    """
    Unified endpoint for order operations.

    GET /api/user/orders/ - List user's orders (authenticated users only)
    POST /api/user/orders/ - Create new order (checkout)

    GET Payload: None (uses authentication)
    Returns: List of user's orders with pagination and filtering

    POST Payload:
    - items: [{menu_item_id, quantity}] (required; acts as session-backed cart input)
    - address_id (optional) OR address fields for new address
    - payment_method: 'bank_transfer'|'debit_card'|'crypto' (optional, to proceed)
    - crypto_currency (optional, defaults to 'usdt')
    - promo_code (optional)
    - order_note (optional)
    - guest_info (optional): {first_name, last_name, email, phone} for automatic account creation

    Returns:
    - Editable summary, address options (if not selected), and payment method choices
    - When payment is selected: payment instructions and pending order info
    - For guest users: account creation results with login credentials
    - Error/status info as needed
    """
    permission_classes = []  # Allow anonymous checkout for POST, authenticated for GET

    def get(self, request):
        """List user's orders with pagination and filtering"""
        # Require authentication for listing orders
        if not request.user or not request.user.is_authenticated:
            return Response({
                'success': False,
                'error': 'Authentication required to view orders'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Get query parameters
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)  # Max 100
        status_filter = request.query_params.get('status')
        sort_by = request.query_params.get('sort_by', '-created_at')

        # Build queryset
        queryset = Order.objects.filter(customer=request.user).select_related('vendor')

        # Apply status filter
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Apply sorting
        valid_sort_fields = ['created_at', 'total_amount', 'status']
        if sort_by.startswith('-'):
            sort_field = sort_by[1:]
            if sort_field in valid_sort_fields:
                queryset = queryset.order_by(sort_by)
        else:
            if sort_by in valid_sort_fields:
                queryset = queryset.order_by(sort_by)

        # Paginate
        from django.core.paginator import Paginator
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        # Serialize orders
        orders_data = []
        for order in page_obj:
            # Get vendor info
            vendor_info = None
            if order.vendor:
                vendor_info = {
                    'id': order.vendor.id,
                    'name': order.vendor.business_name,
                    'logo': self._get_optimized_image_url(getattr(order.vendor, 'logo', None))
                }

            # Get order items count
            items_count = order.items.count()

            orders_data.append({
                'id': order.id,
                'order_number': f"#{order.id}",
                'status': order.status,
                'total_amount': float(order.total_amount or 0),
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'delivery_address': order.delivery_address,
                'payment_method': order.payment_method,
                'payment_confirmed': order.payment_confirmed,
                'vendor': vendor_info,
                'items_count': items_count,
                'estimated_delivery': self._calculate_estimated_delivery(order)
            })

        return Response({
            'success': True,
            'count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'results': orders_data,
            'filters_applied': {
                'status': status_filter,
                'sort_by': sort_by
            }
        }, status=status.HTTP_200_OK)

    @transaction.atomic
    def post(self, request):
        # Allow anonymous checkout - no authentication required initially
        user = getattr(request, 'user', None)
        if not (user and user.is_authenticated):
            # For anonymous users, create a temporary session-based order
            # They can authenticate later to claim the order
            pass  # Allow anonymous checkout
        data = request.data

        # Step 1: Items payload (acts as session-backed cart contents)
        raw_items = data.get('items') or data.get('cart_items') or []
        if not isinstance(raw_items, list) or len(raw_items) == 0:
            return Response({'success': False, 'error': 'No items provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate items and compute summary
        menu_item_ids = []
        quantities_by_id = {}
        for entry in raw_items:
            try:
                mid = int(entry.get('menu_item_id'))
                qty = int(entry.get('quantity', 1))
            except Exception:
                return Response({'success': False, 'error': 'Invalid item payload'}, status=status.HTTP_400_BAD_REQUEST)
            if qty < 1:
                continue
            menu_item_ids.append(mid)
            quantities_by_id[mid] = quantities_by_id.get(mid, 0) + qty

        if not menu_item_ids:
            return Response({'success': False, 'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        menu_items = list(MenuItem.objects.filter(id__in=menu_item_ids, is_available=True).select_related('vendor'))
        if len(menu_items) == 0:
            return Response({'success': False, 'error': 'No valid items found'}, status=status.HTTP_400_BAD_REQUEST)

        # Enforce single-vendor cart
        vendor_ids = {mi.vendor_id for mi in menu_items}
        if len(vendor_ids) > 1:
            return Response({'success': False, 'error': 'Cart contains items from multiple vendors'}, status=status.HTTP_400_BAD_REQUEST)
        vendor = menu_items[0].vendor

        summary_items = []
        subtotal = Decimal('0.00')
        for mi in menu_items:
            qty = quantities_by_id.get(mi.id, 0)
            line_total = mi.price * qty
            subtotal += line_total
            summary_items.append({
                'menu_item_id': mi.id,
                'name': mi.name,
                'quantity': qty,
                'unit_price': float(mi.price),
                'total_price': float(line_total),
            })

        promo_code = data.get('promo_code')
        order_note = data.get('order_note') or ''

        # Calculate fees (match OrderSummaryView calculation)
        from bestyy.core_features.user.models import SystemSettings
        settings = SystemSettings.get_active_settings()

        # Calculate commission (platform fee)
        service_fee = subtotal * (settings['service_fee_percentage'] / Decimal('100'))

        # Calculate shipping fee (base + per km if applicable)
        delivery_fee = settings['base_delivery_fee']

        # Calculate total (match OrderSummaryView)
        grand_total = subtotal + service_fee + delivery_fee

        # Step 2: Address selection/creation
        address_id = data.get('address_id')
        address_fields = data.get('address')
        selected_address = None
        delivery_address_text = ""

        if address_id and user and user.is_authenticated:
            selected_address = Address.objects.filter(user=user, id=address_id).first()
            if not selected_address:
                return Response({'success': False, 'error': 'Invalid address selected'}, status=status.HTTP_400_BAD_REQUEST)
            # Create address text from Address model
            delivery_address_text = f"{selected_address.street_address}, {selected_address.city}, {selected_address.state} {selected_address.postal_code}".strip()
        elif address_fields:
            # For authenticated users, create address model
            if user and user.is_authenticated:
                addr_serializer = AddressSerializer(data=address_fields, context={'request': request})
                if addr_serializer.is_valid():
                    selected_address = addr_serializer.save(user=user)
                    delivery_address_text = f"{selected_address.street_address}, {selected_address.city}, {selected_address.state} {selected_address.postal_code}".strip()
                else:
                    return Response({'success': False, 'error': 'Invalid address data', 'details': addr_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Anonymous user - just store address as text, don't create Address model
                street_address = address_fields.get('street_address', '').strip()
                city = address_fields.get('city', '').strip()
                state = address_fields.get('state', '').strip()
                postal_code = address_fields.get('postal_code', '').strip()

                if not street_address or not city or not state:
                    return Response({'success': False, 'error': 'Street address, city, and state are required'}, status=status.HTTP_400_BAD_REQUEST)

                delivery_address_text = f"{street_address}, {city}, {state}"
                if postal_code:
                    delivery_address_text += f" {postal_code}"

                # Create a mock address object for serializer compatibility
                selected_address = type('MockAddress', (), {
                    'address_type': 'home',
                    'street_address': street_address,
                    'city': city,
                    'state': state,
                    'postal_code': postal_code,
                    'full_name': 'Anonymous User',
                    'phone_number': '',
                    'is_default': False,
                    'id': None
                })()
        else:
            # No address provided yet → return address options to select (only for authenticated users)
            if user and user.is_authenticated:
                addresses = Address.objects.filter(user=user).order_by('-is_default', '-created_at')
                return Response({
                    'success': True,
                    'stage': 'select_address',
                    'addresses': AddressSerializer(addresses, many=True).data,
                    'summary': {
                        'items': summary_items,
                        'subtotal': subtotal,
                        'service_fee': float(service_fee),
                        'delivery_fee': float(delivery_fee),
                        'grand_total': float(grand_total),
                        'promo_applied': promo_code or None,
                        'order_note': order_note,
                        'vendor': {'id': vendor.id, 'name': vendor.business_name},
                    }
                })
            else:
                # Anonymous user - require address fields
                return Response({'success': False, 'error': 'Address information required for anonymous checkout'}, status=status.HTTP_400_BAD_REQUEST)

        # Step 3: If no payment method yet, return summary and choices
        payment_method = data.get('payment_method')
        crypto_currency = data.get('crypto_currency', 'usdt')
        if not payment_method:
            available_methods = ['bank_transfer', 'debit_card', 'crypto']
            return Response({
                'success': True,
                'stage': 'choose_payment',
                'summary': {
                    'items': summary_items,
                    'address': AddressSerializer(selected_address).data,
                    'subtotal': subtotal,
                    'service_fee': float(service_fee),
                    'delivery_fee': float(delivery_fee),
                    'grand_total': float(grand_total),
                    'promo_applied': promo_code or None,
                    'order_note': order_note,
                    'vendor': {'id': vendor.id, 'name': vendor.business_name},
                },
                'payment_methods': available_methods
            })

        # Step 4: Validate stock availability before creating order
        from bestyy.core_features.user.cart_utils import get_available_stock
        
        stock_errors = []
        for mi in menu_items:
            qty = quantities_by_id.get(mi.id, 0)
            if qty > 0:
                available = get_available_stock(mi)
                if available < qty:
                    stock_errors.append({
                        'product': mi.name,
                        'requested': qty,
                        'available': available
                    })
        
        if stock_errors:
            error_msg = "Insufficient stock for: " + ", ".join(
                [f"{e['product']} (requested: {e['requested']}, available: {e['available']})" 
                 for e in stock_errors]
            )
            return Response({
                'success': False,
                'error': error_msg,
                'stock_errors': stock_errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create Order now (pending), add items (M2M), then generate payment instructions
        # Persist delivery address as text (flattened from Address model)
        # Note: Stock reservations will be created automatically when payment_confirmed=True (via signal)
        delivery_address_text = f"{selected_address.street_address or ''} {selected_address.city or ''} {selected_address.state or ''} {selected_address.postal_code or ''}".strip()

        order = Order.objects.create(
            customer=user if user and user.is_authenticated else None,
            vendor=vendor,
            shipping_address=delivery_address_text,
            delivery_address=delivery_address_text,
            total_amount=grand_total,
            status='pending',
            payment_method=payment_method,
            notes=order_note
        )

        # Create OrderItem instances for each menu item with quantities
        for mi in menu_items:
            qty = quantities_by_id.get(mi.id, 0)
            if qty > 0:
                OrderItem.objects.create(
                    order=order,
                    product=mi,
                    quantity=qty,
                    price=mi.price
                )

        # Handle automatic account creation for guest users
        account_result = None
        if not (user and user.is_authenticated):
            guest_info = data.get('guest_info', {})
            if guest_info:
                account_user, account_message, credentials = AutomaticAccountService.create_or_reuse_account_for_order(order, guest_info)
                account_result = {
                    'account_created': account_user is not None,
                    'message': account_message,
                    'credentials': credentials if account_user else {}
                }

        payment_instructions = None
        if payment_method == 'bank_transfer':
            if user and user.is_authenticated:
                paystack_service = PaystackService()
                result = paystack_service.create_dedicated_account(user)
                if not result.get('success'):
                    return Response({'success': False, 'error': result.get('error', 'Could not create dedicated bank account')}, status=status.HTTP_400_BAD_REQUEST)
                payment_instructions = {'type': 'bank_transfer', 'details': result['account']}
            else:
                # Anonymous user - provide generic bank transfer instructions
                payment_instructions = {
                    'type': 'bank_transfer',
                    'details': {
                        'account_number': '1234567890',
                        'account_name': 'Bestyy Express',
                        'bank_name': 'Sample Bank',
                        'amount': grand_total,
                        'reference': f"order_{order.id}",
                        'instructions': [
                            '1. Copy the account details above',
                            '2. Transfer the exact amount to this account',
                            '3. Use the reference number as payment reference',
                            '4. Login/register to confirm payment',
                            '5. Your payment will be verified automatically'
                        ]
                    }
                }
        elif payment_method == 'debit_card':
            # Placeholder redirect URL; integrate paylink/card init as needed
            payment_instructions = {'type': 'debit_card', 'redirect_url': 'https://paystack.com/pay/initialize'}
        elif payment_method == 'crypto':
            crypto_manager = CryptoPaymentManager()
            try:
                crypto_payment = crypto_manager.create_crypto_payment(order, crypto_currency)
                payment_instructions = {
                    'type': 'crypto',
                    'currency': crypto_currency,
                    'pay_address': crypto_payment.pay_address,
                    'pay_amount': float(crypto_payment.pay_amount),
                    'payment_id': crypto_payment.nowpayments_payment_id,
                }
            except Exception as e:
                return Response({'success': False, 'error': f'Could not create crypto payment: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'success': False, 'error': 'Unsupported payment method'}, status=status.HTTP_400_BAD_REQUEST)

        order_data = OrderSerializer(order).data
        response_data = {
            'success': True,
            'order': order_data,
            'payment': payment_instructions,
            'summary': {
                'items': summary_items,
                'address': AddressSerializer(selected_address).data,
                'subtotal': subtotal,
                'service_fee': float(service_fee),
                'delivery_fee': float(delivery_fee),
                'grand_total': float(grand_total),
                'promo_applied': promo_code or None,
                'order_note': order_note,
                'vendor': {'id': vendor.id, 'name': vendor.business_name},
            }
        }

        # Include account creation results if applicable
        if account_result:
            response_data['account'] = account_result

        return Response(response_data, status=status.HTTP_201_CREATED)


class OrderPaymentStatusView(APIView):
    """
    Check payment status for an order (for frontend polling)

    GET /api/user/orders/{order_id}/payment-status/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        """Get current payment status for an order"""
        try:
            # Get order
            order = get_object_or_404(Order, id=order_id)

            # Check if user can access this order
            if order.customer != request.user and not request.user.is_staff:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)

            # If payment method is bank_transfer and not confirmed, check with Paystack
            paystack_status = None
            if order.payment_method == 'bank_transfer' and not order.payment_confirmed:
                paystack_status = self._verify_paystack_transaction(order)

            return Response({
                'success': True,
                'payment_status': {
                    'confirmed': order.payment_confirmed,
                    'confirmed_at': order.payment_confirmed_at.isoformat() if order.payment_confirmed_at else None,
                    'method': order.payment_method,
                    'amount': float(order.total_amount),
                    'reference': getattr(order, 'payment_reference', None),
                    'paystack_status': paystack_status  # Additional status from Paystack if available
                },
                'order_status': order.status,
                'can_receive_updates': True  # Frontend can connect to WebSocket for real-time updates
            }, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Order not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _verify_paystack_transaction(self, order):
        """Verify transaction status with Paystack API"""
        try:
            from bestyy.core_features.user.services.paystack_service import PaystackService

            # Generate reference if not exists (for orders created with bank transfer)
            reference = getattr(order, 'payment_reference', None)
            if not reference:
                reference = f"order_{order.id}_{int(timezone.now().timestamp())}"
                order.payment_reference = reference
                order.save()

            paystack_service = PaystackService()
            result = paystack_service.verify_transaction(reference)

            if result.get('success'):
                data = result.get('data', {})
                transaction_status = data.get('status')

                # If transaction is successful but not yet confirmed in our system, confirm it
                if transaction_status == 'success' and not order.payment_confirmed:
                    # Auto-confirm the payment
                    order.payment_confirmed = True
                    order.payment_confirmed_at = timezone.now()
                    order.status = 'confirmed'
                    order.save()

                    # Trigger post-payment processes
                    self._process_payment_confirmation(order)

                return {
                    'status': transaction_status,
                    'gateway_response': data.get('gateway_response'),
                    'paid_at': data.get('paid_at'),
                    'message': self._get_status_message(transaction_status)
                }
            else:
                return {
                    'status': 'unknown',
                    'error': result.get('error', 'Could not verify transaction')
                }

        except Exception as e:
            return {
                'status': 'error',
                'error': f'Verification failed: {str(e)}'
            }

    def _get_status_message(self, status):
        """Get user-friendly status message"""
        messages = {
            'success': 'Payment completed successfully',
            'pending': 'Payment is being processed',
            'failed': 'Payment failed',
            'abandoned': 'Payment was abandoned',
            'ongoing': 'Payment is in progress',
            'processing': 'Payment is being processed',
            'queued': 'Payment is queued for processing',
            'reversed': 'Payment was reversed'
        }
        return messages.get(status, f'Payment status: {status}')

    def _process_payment_confirmation(self, order):
        """Process payment confirmation (extracted from webhook handler)"""
        try:
            # Generate codes for conditional payouts
            if hasattr(order, 'generate_pickup_code'):
                order.generate_pickup_code()
            if hasattr(order, 'generate_delivery_otp'):
                order.generate_delivery_otp()

            # Send WhatsApp notifications
            from bestyy.core_features.user.api.paystack_webhooks import _send_code_notifications, _send_payment_receipt
            _send_code_notifications(order)
            _send_payment_receipt(order)

            # Broadcast payment confirmation via WebSocket
            from bestyy.core_features.user.services.order_status_broadcast_service import OrderStatusBroadcastService
            OrderStatusBroadcastService.broadcast_payment_confirmed(order)

            # Notify vendor about new order
            from bestyy.core_features.user.services.vendor_order_notification_service import VendorOrderNotificationService
            VendorOrderNotificationService.notify_vendor_new_order(order)

            # Find and assign nearby courier
            from bestyy.core_features.user.services.courier_location_service import CourierLocationService
            try:
                # Get delivery location coordinates (simplified)
                delivery_lat = 6.5244  # Lagos latitude
                delivery_lon = 3.3792  # Lagos longitude

                nearby_couriers = CourierLocationService.find_nearby_couriers(
                    delivery_lat, delivery_lon,
                    max_distance_km=15.0,
                    max_results=3,
                    require_active=True,
                    require_verified=True
                )

                if nearby_couriers:
                    closest_courier, distance = nearby_couriers[0]
                    order.courier = closest_courier
                    order.save()

                    # Send notification to assigned courier
                    _send_code_notifications(order)

                    # Broadcast courier assignment
                    OrderStatusBroadcastService.broadcast_new_delivery_request(order, nearby_couriers)

            except Exception as e:
                pass  # Continue even if courier assignment fails

        except Exception as e:
            pass  # Continue even if post-processing fails


class OrderReceiptView(APIView):
    """
    Get order receipt details

    GET /api/user/orders/{order_id}/receipt/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        """Get order receipt"""
        try:
            # Get order
            order = get_object_or_404(Order, id=order_id)

            # Check if user can access this order
            if order.customer != request.user and not request.user.is_staff:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)

            # Check if payment is confirmed
            if not order.payment_confirmed:
                return Response({
                    'success': False,
                    'error': 'Payment not confirmed yet'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Generate receipt data
            from ..services.receipt_service import ReceiptService
            receipt_data = ReceiptService.generate_receipt_data(order)

            if not receipt_data:
                return Response({
                    'success': False,
                    'error': 'Failed to generate receipt data'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({
                'success': True,
                'receipt': receipt_data,
                'order': {
                    'id': order.id,
                    'status': order.status,
                    'payment_confirmed_at': order.payment_confirmed_at.isoformat() if order.payment_confirmed_at else None,
                    'created_at': order.created_at.isoformat()
                }
            }, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Order not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderTrackingView(APIView):
    """
    Get order tracking information - Public endpoint (no auth required)
    Anyone with the order ID can track it
    
    GET /api/user/orders/{order_id}/tracking/
    """
    permission_classes = []  # No authentication required
    authentication_classes = []  # No authentication required
    
    def get(self, request, pk):
        """Get order tracking details"""
        try:
            order = get_object_or_404(Order, id=pk)
            
            # Public endpoint - anyone with order ID can track
            # No permission check needed for tracking
            
            # Build tracking timeline
            timeline = []
            timeline.append({'status': 'placed', 'label': 'Order Placed', 'timestamp': order.created_at.isoformat() if order.created_at else None, 'completed': True, 'icon': ''})
            if order.payment_confirmed:
                timeline.append({'status': 'payment_confirmed', 'label': 'Payment Confirmed', 'timestamp': order.payment_confirmed_at.isoformat() if order.payment_confirmed_at else None, 'completed': True, 'icon': ''})
            if order.confirmed_at:
                timeline.append({'status': 'confirmed', 'label': 'Vendor Confirmed', 'timestamp': order.confirmed_at.isoformat(), 'completed': True, 'icon': ''})
            elif order.status in ['confirmed', 'preparing', 'ready', 'out_for_delivery', 'delivered']:
                timeline.append({'status': 'confirmed', 'label': 'Vendor Confirmed', 'timestamp': None, 'completed': True, 'icon': ''})
            else:
                timeline.append({'status': 'confirmed', 'label': 'Waiting for Vendor', 'timestamp': None, 'completed': False, 'icon': ''})
            if order.status == 'delivered':
                timeline.append({'status': 'delivered', 'label': 'Delivered', 'timestamp': getattr(order, 'delivered_at', timezone.now()).isoformat(), 'completed': True, 'icon': ''})
            completed_steps = sum(1 for step in timeline if step['completed'])
            progress_percentage = int((completed_steps / len(timeline)) * 100) if timeline else 0
            return Response({'success': True, 'order': {'id': str(order.id), 'order_number': order.order_number, 'status': order.status, 'created_at': order.created_at.isoformat() if order.created_at else None, 'total_amount': float(order.total_amount) if order.total_amount else 0, 'delivery_address': order.delivery_address, 'vendor': {'name': order.vendor.business_name if order.vendor else None, 'phone': order.vendor.phone if order.vendor else None}, 'timeline': timeline, 'progress_percentage': progress_percentage}}, status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            return Response({'success': False, 'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
