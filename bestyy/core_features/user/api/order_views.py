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
from bestyy.core_features.user.models import Address, Order, MenuItem, VendorProfile
from bestyy.core_features.user.serializers.address_serializers import AddressSerializer
from bestyy.core_features.user.serializers.order_serializers import OrderSerializer
from bestyy.core_features.user.services.paystack_service import PaystackService
from bestyy.core_features.user.services.crypto_payment_service import CryptoPaymentManager


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
            delivery_instructions = request.data.get('delivery_instructions', '').strip()
            
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
                user=request.user,
                vendor=cart.vendor,
                delivery_address=delivery_address,
                total_price=cart.total_price,
                status='pending',
                payment_method=payment_method,
                delivery_instructions=delivery_instructions,
                order_date=timezone.now()
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
                    'total_amount': float(order.total_price),
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
                    'delivery_instructions': order.delivery_instructions,
                    'order_date': order.order_date.isoformat(),
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
    """
    permission_classes = [IsAuthenticated]

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
            commission = subtotal * (settings.service_fee_percentage / 100)

            # Calculate shipping fee (base + per km if applicable)
            shipping_fee = settings.base_delivery_fee

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
                            'name': item.menu_item.dish_name,
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
    Get order confirmation details with delivery guidance

    GET /api/user/orders/{order_id}/confirmation/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        """Get order confirmation with delivery OTP and guidance"""
        try:
            # Get order
            order = get_object_or_404(Order, id=order_id, user=request.user)

            # Generate delivery OTP if not exists
            if not order.delivery_otp:
                order.generate_delivery_otp()

            # Get system settings
            settings = SystemSettings.get_active_settings()

            # Calculate totals
            subtotal = sum(item.total_price for item in order.items.all())
            commission = subtotal * (settings.service_fee_percentage / 100)
            shipping_fee = settings.base_delivery_fee
            total = subtotal + commission + shipping_fee

            return Response({
                'success': True,
                'confirmation': {
                    'order': {
                        'id': order.id,
                        'order_number': f"#{order.id}",
                        'status': order.status,
                        'created_at': order.order_placed_at.isoformat() if order.order_placed_at else None
                    },
                    'vendor': {
                        'name': order.vendor.business_name,
                        'phone': getattr(order.vendor, 'phone', 'Not available')
                    },
                    'delivery': {
                        'address': order.delivery_address,
                        'otp': order.delivery_otp,
                        'otp_generated_at': order.delivery_otp_generated_at.isoformat() if order.delivery_otp_generated_at else None,
                        'instructions': 'Give this OTP code to the courier when they deliver your order to confirm receipt.'
                    },
                    'payment': {
                        'method': order.payment_method,
                        'status': 'confirmed' if order.payment_confirmed else 'pending',
                        'receipt_url': f"/orders/{order.id}/receipt" if order.payment_confirmed else None
                    },
                    'summary': {
                        'subtotal': float(subtotal),
                        'commission': float(commission),
                        'shipping_fee': float(shipping_fee),
                        'total': float(total),
                        'currency': 'NGN'
                    },
                    'next_steps': [
                        '1. Your order is being prepared by the vendor',
                        '2. A courier will be assigned for delivery',
                        '3. You will receive updates on order status',
                        '4. When courier arrives, provide the delivery OTP to confirm receipt',
                        '5. Payment will be processed upon successful delivery'
                    ],
                    'support': {
                        'phone': '0800-BESTYY',
                        'email': 'support@bestyy.com',
                        'whatsapp': 'https://wa.me/234800BESTYY'
                    }
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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


class UnifiedCheckoutView(APIView):
    """
    Unified editable /checkout endpoint for all user checkout logic.

    POST /api/user/checkout/
    Payload:
    - items: [{menu_item_id, quantity}] (required; acts as session-backed cart input)
    - address_id (optional) OR address fields for new address
    - payment_method: 'bank_transfer'|'debit_card'|'crypto' (optional, to proceed)
    - crypto_currency (optional, defaults to 'usdt')
    - promo_code (optional)
    - order_note (optional)

    Returns:
    - Editable summary, address options (if not selected), and payment method choices
    - When payment is selected: payment instructions and pending order info
    - Error/status info as needed
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user = request.user
        data = request.data

        # Step 1: Items payload (acts as session-backed cart contents)
        raw_items = data.get('items') or []
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

        menu_items = list(MenuItem.objects.filter(id__in=menu_item_ids, available_now=True).select_related('vendor'))
        if len(menu_items) == 0:
            return Response({'success': False, 'error': 'No valid items found'}, status=status.HTTP_400_BAD_REQUEST)

        # Enforce single-vendor cart
        vendor_ids = {mi.vendor_id for mi in menu_items}
        if len(vendor_ids) > 1:
            return Response({'success': False, 'error': 'Cart contains items from multiple vendors'}, status=status.HTTP_400_BAD_REQUEST)
        vendor = menu_items[0].vendor

        summary_items = []
        subtotal = 0.0
        for mi in menu_items:
            qty = quantities_by_id.get(mi.id, 0)
            line_total = float(mi.price) * qty
            subtotal += line_total
            summary_items.append({
                'menu_item_id': mi.id,
                'name': mi.dish_name,
                'quantity': qty,
                'unit_price': float(mi.price),
                'total_price': line_total,
            })

        promo_code = data.get('promo_code')
        order_note = data.get('order_note') or ''
        fee = 0.0  # Extend for service/delivery fees if needed
        grand_total = subtotal + fee

        # Step 2: Address selection/creation
        address_id = data.get('address_id')
        address_fields = data.get('address')
        selected_address = None
        if address_id:
            selected_address = Address.objects.filter(user=user, id=address_id).first()
            if not selected_address:
                return Response({'success': False, 'error': 'Invalid address selected'}, status=status.HTTP_400_BAD_REQUEST)
        elif address_fields:
            addr_serializer = AddressSerializer(data=address_fields, context={'request': request})
            if addr_serializer.is_valid():
                selected_address = addr_serializer.save(user=user)
            else:
                return Response({'success': False, 'error': 'Invalid address data', 'details': addr_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # No address provided yet → return address options to select
            addresses = Address.objects.filter(user=user).order_by('-is_default', '-created_at')
            return Response({
                'success': True,
                'stage': 'select_address',
                'addresses': AddressSerializer(addresses, many=True).data,
                'summary': {
                    'items': summary_items,
                    'subtotal': subtotal,
                    'fee': fee,
                    'grand_total': grand_total,
                    'promo_applied': promo_code or None,
                    'order_note': order_note,
                    'vendor': {'id': vendor.id, 'name': vendor.business_name},
                }
            })

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
                    'fee': fee,
                    'grand_total': grand_total,
                    'promo_applied': promo_code or None,
                    'order_note': order_note,
                    'vendor': {'id': vendor.id, 'name': vendor.business_name},
                },
                'payment_methods': available_methods
            })

        # Step 4: Create Order now (pending), add items (M2M), then generate payment instructions
        # Persist delivery address as text (flattened from Address model)
        delivery_address_text = f"{selected_address.street} {selected_address.city} {selected_address.state} {selected_address.postal_code}".strip()

        order = Order.objects.create(
            user=user,
            vendor=vendor,
            delivery_address=delivery_address_text,
            total_price=grand_total,
            status='pending'
        )
        # Add unique items to M2M (quantities are reflected in total only due to schema)
        order.items.add(*[mi for mi in menu_items])

        payment_instructions = None
        if payment_method == 'bank_transfer':
            paystack_service = PaystackService()
            result = paystack_service.create_dedicated_account(user)
            if not result.get('success'):
                return Response({'success': False, 'error': result.get('error', 'Could not create dedicated bank account')}, status=status.HTTP_400_BAD_REQUEST)
            payment_instructions = {'type': 'bank_transfer', 'details': result['account']}
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
        return Response({
            'success': True,
            'order': order_data,
            'payment': payment_instructions,
            'summary': {
                'items': summary_items,
                'address': AddressSerializer(selected_address).data,
                'subtotal': subtotal,
                'fee': fee,
                'grand_total': grand_total,
                'promo_applied': promo_code or None,
                'order_note': order_note,
                'vendor': {'id': vendor.id, 'name': vendor.business_name},
            }
        }, status=status.HTTP_201_CREATED)
