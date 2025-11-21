"""
WhatsApp Order Processing Service
Handles order creation, vendor search, and payment processing for WhatsApp users
"""
import logging
import requests
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import models
from bestyy.core_features.user.models import (
    VendorProfile, Address
)
from bestyy.restaurant_features.product.models import Product as MenuItem
from bestyy.restaurant_features.vendor.models import Vendor
from bestyy.restaurant_features.order.models import Order, OrderItem
from django.db.models import Avg
from bestyy.core_features.user.services.paystack_service import PaystackService

User = get_user_model()
logger = logging.getLogger(__name__)


class WhatsAppOrderService:
    """
    Service to handle order processing from WhatsApp messages
    """

    def __init__(self):
        self.paystack_service = PaystackService()
        self.base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')

    def _get_optimized_image_url(self, image_field):
        """Get optimized Cloudinary URL for images"""
        if image_field:
            try:
                if hasattr(image_field, 'url'):
                    url = image_field.url
                    if 'cloudinary.com' in url:
                        return url.replace('/upload/', '/upload/w_400,h_300,c_fill,f_auto,q_auto/')
                    return url
                else:
                    return str(image_field)
            except Exception:
                return None
        return None
    
    def search_vendors_by_food(self, food_type, limit=3, offset=0, vendor_ids=None):
        """
        Search for vendors that serve a specific food type
        Returns list of vendors with menu items, pictures, prices, and ratings

        Args:
            food_type: Type of food to search for
            limit: Maximum number of vendors to return
            offset: Offset for pagination
            vendor_ids: Optional list of specific vendor IDs to filter by
        """
        try:
            # Map food types to vendor categories
            category_mapping = {
                'okoro soup': 'nigerian_food',
                'okra soup': 'nigerian_food',
                'egusi soup': 'nigerian_food',
                'egwusi': 'nigerian_food',
                'egwusi soup': 'nigerian_food',
                'efo riro': 'nigerian_food',
                'afang soup': 'nigerian_food',
                'pepper soup': 'nigerian_food',
                'jollof rice': 'nigerian_food',
                'fried rice': 'nigerian_food',
                'eba': 'nigerian_food',
                'fufu': 'nigerian_food',
                'amala': 'nigerian_food',
                'pounded yam': 'nigerian_food',
                'moi moi': 'nigerian_food',
                'akara': 'nigerian_food',
                'suya': 'nigerian_food',
                'plantain': 'nigerian_food',
            }

            # Get the vendor category from mapping, or use food_type directly
            search_category = category_mapping.get(food_type.lower(), food_type.lower())

            # Get total count first
            total_vendors = VendorProfile.objects.filter(
                verification_status='approved',
                is_suspended=False,
                business_category__icontains=search_category
            ).count()

            # Get vendors with pagination
            vendor_query = VendorProfile.objects.filter(
                verification_status='approved',
                is_suspended=False,
                business_category__icontains=search_category
            )

            # Filter by specific vendor IDs if provided
            if vendor_ids:
                vendor_query = vendor_query.filter(id__in=vendor_ids)

            vendors = vendor_query[offset:offset + limit]

            vendor_data = []
            for vendor in vendors:
                # Search for menu items by food type or category
                # Handle egusi/egwusi variations
                search_terms = [food_type]
                if food_type.lower() in ['egusi soup', 'egwusi', 'egwusi soup']:
                    search_terms.extend(['egusi', 'egwusi', 'melon'])
                elif food_type.lower() in ['okoro soup', 'okra soup']:
                    search_terms.extend(['okoro', 'okra'])
                
                # Build query with multiple search terms
                query = models.Q()
                for term in search_terms:
                    query |= (
                        models.Q(category__icontains=term) |
                        models.Q(dish_name__icontains=term) |
                        models.Q(item_description__icontains=term)
                    )
                
                menu_items = MenuItem.objects.filter(
                    vendor=vendor,
                    available_now=True
                ).filter(query)[:5]

                # If no items found with specific search, get any available items
                if not menu_items:
                    menu_items = MenuItem.objects.filter(
                        vendor=vendor,
                        available_now=True
                    )[:5]

                # Calculate average rating - simplified without VendorRating model
                avg_rating = 4.5  # Default rating

                # Get vendor logo/picture
                vendor_picture = None
                if vendor.logo:
                    vendor_picture = vendor.logo.url

                vendor_data.append({
                    'id': vendor.id,
                    'name': vendor.business_name,
                    'rating': float(avg_rating),
                    'delivery_time': '30-45 min',
                    'picture': vendor_picture,
                    'description': vendor.business_description,
                    'menu_items': [
                        {
                            'id': item.id,
                            'name': item.name,
                            'price': float(item.price),
                            'description': item.description,
                            'picture': self._get_optimized_image_url(item.image) if hasattr(item, 'image') and item.image else None,
                            'available': item.is_available
                        }
                        for item in menu_items
                    ]
                })

            return {
                'success': True,
                'vendors': vendor_data,
                'count': len(vendor_data),
                'total_vendors': total_vendors,
                'has_more': (offset + limit) < total_vendors
            }
        except Exception as e:
            logger.error(f"Error searching vendors: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def create_awaiting_order_from_whatsapp(self, user, vendor_id, items_data):
        """
        Create an awaiting order from WhatsApp user input (without delivery address)
        Order will be in 'awaiting' state until user confirms and provides special instructions
        
        Args:
            user: User object
            vendor_id: ID of vendor
            items_data: List of {'menu_item_id': int, 'quantity': int}
        
        Returns:
            Order data with awaiting status
        """
        try:
            # Get vendor
            vendor = VendorProfile.objects.get(id=vendor_id)
            
            # Create cart - Cart model was removed, using Order directly
            # cart = Cart.objects.create(user=user, vendor=vendor)

            total_price = Decimal('0.00')
            order_items_data = []

            # Add items to cart - Cart model removed, using OrderItem directly
            for item_data in items_data:
                menu_item = MenuItem.objects.get(id=item_data['menu_item_id'])
                quantity = item_data.get('quantity', 1)

                logger.info(f"Processing menu item {menu_item.id}: {menu_item.name}, price: {menu_item.price}, quantity: {quantity}")

                # Create OrderItem without cart reference
                # cart_item = OrderItem.objects.create(
                #     cart=cart,
                #     menu_item=menu_item,
                #     quantity=quantity,
                #     price=menu_item.price
                # )

                item_total = menu_item.price * quantity
                total_price += item_total

                logger.info(f"Item total: {item_total}, running total: {total_price}")

                order_items_data.append({
                    'name': menu_item.name,
                    'quantity': quantity,
                    'price': float(menu_item.price),
                    'total': float(item_total)
                })
            
            # Ensure minimum order amount
            logger.info(f"Calculated total_price: {total_price}")
            if total_price <= 0:
                logger.warning(f"Order total is {total_price}, setting minimum amount to ₦2500")
                total_price = Decimal('2500.00')  # Minimum order amount
            else:
                logger.info(f"Order total is {total_price}, using calculated amount")

            # Ensure minimum order amount
            if total_price <= 0:
                logger.warning(f"Order total is {total_price}, setting minimum amount of 2500")
                total_price = Decimal('2500.00')  # Minimum order amount

            # Create order in awaiting state
            order = Order.objects.create(
                customer=user,
                vendor=vendor,
                delivery_address="To be provided",  # Placeholder
                total_amount=total_price,
                status='awaiting',  # Set to awaiting state
                created_at=timezone.now()
            )

            logger.info(f"Created order {order.id} with total_amount: {total_price}")
            
            # Add menu items to order (after order is saved)
            menu_items_to_add = []
            for item_data in items_data:
                menu_item = MenuItem.objects.get(id=item_data['menu_item_id'])
                menu_items_to_add.append(menu_item)
            
            # Add all items at once
            order.items.set(menu_items_to_add)
            
            return {
                'success': True,
                'order': {
                    'id': order.id,
                    'order_number': f"#{order.id}",
                    'vendor': vendor.business_name,
                    'items': order_items_data,
                    'total_amount': float(total_price),
                    'currency': 'NGN',
                    'status': order.status,
                    'estimated_delivery': '30-45 minutes'
                }
            }
        
        except Exception as e:
            logger.error(f"Error creating awaiting order: {str(e)}")
            return {'success': False, 'error': str(e)}

    def create_order_from_whatsapp(self, user, vendor_id, items_data, delivery_address_text, payment_method='bank_transfer'):
        """
        Create an order from WhatsApp user input
        
        Args:
            user: User object
            vendor_id: ID of vendor
            items_data: List of {'menu_item_id': int, 'quantity': int}
            delivery_address_text: Delivery address as text
            payment_method: 'card' or 'cash'
        
        Returns:
            Order data with payment link if needed
        """
        try:
            # Get vendor
            vendor = VendorProfile.objects.get(id=vendor_id)
            
            # Create or get address
            address, _ = Address.objects.get_or_create(
                user=user,
                street_address=delivery_address_text,
                defaults={
                    'full_name': user.get_full_name() or user.email,
                    'phone_number': getattr(user, 'phone', '+2340000000000') or '+2340000000000',
                    'city': 'Lagos',
                    'state': 'Lagos',
                    'postal_code': '000000',
                    'address_type': 'other',
                    'is_default': False
                }
            )
            
            # Create cart
            cart = Cart.objects.create(user=user, vendor=vendor)
            
            total_price = Decimal('0.00')
            order_items_data = []
            
            # Validate stock availability first
            from bestyy.core_features.user.cart_utils import get_available_stock
            
            stock_errors = []
            for item_data in items_data:
                menu_item = MenuItem.objects.get(id=item_data['menu_item_id'])
                quantity = item_data.get('quantity', 1)
                available = get_available_stock(menu_item)
                
                if available < quantity:
                    stock_errors.append({
                        'product': menu_item.name,
                        'requested': quantity,
                        'available': available
                    })
            
            if stock_errors:
                error_msg = "Insufficient stock for: " + ", ".join(
                    [f"{e['product']} (requested: {e['requested']}, available: {e['available']})" 
                     for e in stock_errors]
                )
                return {'success': False, 'error': error_msg}
            
            # Add items to cart
            for item_data in items_data:
                menu_item = MenuItem.objects.get(id=item_data['menu_item_id'])
                quantity = item_data.get('quantity', 1)
                
                cart_item = OrderItem.objects.create(
                    cart=cart,
                    menu_item=menu_item,
                    quantity=quantity,
                    price=menu_item.price
                )
                
                item_total = menu_item.price * quantity
                total_price += item_total
                
                order_items_data.append({
                    'name': menu_item.name,
                    'quantity': quantity,
                    'price': float(menu_item.price),
                    'total': float(item_total)
                })
            
            # Create order
            # Note: Stock reservations will be created automatically when payment_confirmed=True (via signal)
            order = Order.objects.create(
                user=user,
                vendor=vendor,
                delivery_address=address.street_address,
                total_price=total_price,
                status='pending',
                order_placed_at=timezone.now()
            )
            
            # Add menu items to order (after order is saved)
            menu_items_to_add = []
            for item_data in items_data:
                menu_item = MenuItem.objects.get(id=item_data['menu_item_id'])
                menu_items_to_add.append(menu_item)
            
            # Add all items at once
            order.items.set(menu_items_to_add)
            
            # Calculate distance and delivery fee
            order.calculate_distance_and_fee()

            # Calculate total amount including delivery fee
            total_with_delivery = total_price + order.delivery_fee

            # Generate dedicated bank account for payment
            bank_account = None
            if payment_method == 'bank_transfer':
                # Use Pay with Transfer
                amount_kobo = int((order.total_amount or 0) * 100)  # Convert to kobo for Paystack
                account_result = self.paystack_service.initialize_pay_with_transfer(
                    email=user.email,
                    amount=amount_kobo,
                    reference=f"order_{order.id}",
                    expiry_hours=8
                )
                if account_result.get('success'):
                    bank_account = account_result.get('account_details', {})
                    # Store reference for webhook processing
                    order.payment_reference = bank_account.get('reference') if bank_account else f"order_{order.id}"
                    order.save()
            
            # Safe conversions to handle None values
            delivery_fee = order.delivery_fee or 0
            total_amount = (total_with_delivery or 0) if total_with_delivery else total_price
            distance_km = order.delivery_distance_km or 0

            return {
                'success': True,
                'order': {
                    'id': order.id,
                    'order_number': f"#{order.id}",
                    'vendor': vendor.business_name if vendor else 'Unknown Vendor',
                    'items': order_items_data,
                    'food_amount': float(total_price),
                    'delivery_fee': float(delivery_fee),
                    'total_amount': float(total_amount),
                    'currency': 'NGN',
                    'delivery_address': address.street_address,
                    'distance_km': float(distance_km),
                    'status': order.status,
                    'payment_method': payment_method,
                    'bank_account': bank_account,
                    'estimated_delivery': '30-45 minutes'
                }
            }
        
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_order_status(self, order_id, user):
        """Get current order status"""
        try:
            order = Order.objects.get(id=order_id, customer=user)
            return {
                'success': True,
                'order': {
                    'id': order.id,
                    'status': order.status,
                    'vendor': order.vendor.business_name if order.vendor else 'Unknown Vendor',
                    'total_amount': float(order.total_amount or 0),
                    'estimated_delivery': '30-45 minutes'
                }
            }
        except Order.DoesNotExist:
            return {'success': False, 'error': 'Order not found'}
        except Exception as e:
            logger.error(f"Error getting order status: {str(e)}")
            return {'success': False, 'error': str(e)}
