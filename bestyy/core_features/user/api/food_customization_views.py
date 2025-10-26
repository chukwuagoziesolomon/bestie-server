"""
Food customization API for menu item variants and cart management
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q

from bestyy.core_features.user.models import (
    MenuItem, MenuItemVariant, Cart, CartItem, VendorProfile, User
)


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
            
            # Get variants organized by type
            variants = MenuItemVariant.objects.filter(
                menu_item=menu_item,
                is_available=True
            ).order_by('type', 'sort_order', 'name')
            
            # Organize variants by type
            variants_by_type = {}
            for variant in variants:
                if variant.type not in variants_by_type:
                    variants_by_type[variant.type] = []
                
                variants_by_type[variant.type].append({
                    'id': variant.id,
                    'name': variant.name,
                    'type': variant.type,
                    'price_modifier': float(variant.price_modifier),
                    'is_required': variant.is_required,
                    'formatted_price': f"+₦{variant.price_modifier}" if variant.price_modifier > 0 else "Free"
                })
            
            # Get menu item details
            item_data = {
                'id': menu_item.id,
                'name': menu_item.name,
                'description': menu_item.description,
                'base_price': float(menu_item.price),
                'currency': 'NGN',
                'image': self._get_optimized_image_url(menu_item.image),
                'preparation_time': menu_item.preparation_time,
                'ingredients': menu_item.ingredients.split(',') if menu_item.ingredients else [],
                'allergens': menu_item.allergens.split(',') if menu_item.allergens else [],
                'is_vegetarian': menu_item.is_vegetarian,
                'is_spicy': menu_item.is_spicy,
                'calories': menu_item.calories,
            }
            
            return Response({
                'success': True,
                'menu_item': item_data,
                'variants': variants_by_type,
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
    Add customized menu item to cart
    
    POST /api/user/cart/add/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Add customized item to cart"""
        try:
            menu_item_id = request.data.get('menu_item_id')
            quantity = int(request.data.get('quantity', 1))
            selected_variants = request.data.get('variants', [])
            special_instructions = request.data.get('special_instructions', '').strip()
            
            if not menu_item_id:
                return Response({
                    'success': False,
                    'error': 'Menu item ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get menu item and vendor
            menu_item = get_object_or_404(MenuItem, id=menu_item_id, available_now=True)
            vendor = menu_item.vendor
            
            # Validate variants
            validated_variants = self._validate_variants(menu_item, selected_variants)
            if 'error' in validated_variants:
                return Response({
                    'success': False,
                    'error': validated_variants['error']
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get or create cart for this vendor
            cart, created = Cart.objects.get_or_create(
                user=request.user,
                vendor=vendor,
                is_active=True
            )
            
            # Calculate total price
            variant_total = sum(variant['price_modifier'] for variant in validated_variants['variants'])
            total_price = (float(menu_item.price) + variant_total) * quantity
            
            # Create cart item
            cart_item = CartItem.objects.create(
                cart=cart,
                menu_item=menu_item,
                quantity=quantity,
                base_price=menu_item.price,
                variants=validated_variants['variants'],
                special_instructions=special_instructions,
                total_price=total_price
            )
            
            # Update cart totals
            cart.save()
            
            return Response({
                'success': True,
                'message': 'Item added to cart successfully',
                'cart_item': {
                    'id': cart_item.id,
                    'menu_item_name': cart_item.menu_item.name,
                    'quantity': cart_item.quantity,
                    'variants': cart_item.variants,
                    'special_instructions': cart_item.special_instructions,
                    'total_price': float(cart_item.total_price),
                    'currency': 'NGN'
                },
                'cart_summary': {
                    'cart_id': cart.id,
                    'vendor_name': vendor.business_name,
                    'total_items': cart.total_items,
                    'total_price': float(cart.total_price),
                    'currency': 'NGN'
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _validate_variants(self, menu_item, selected_variants):
        """Validate selected variants"""
        try:
            # Get all available variants for this menu item
            available_variants = MenuItemVariant.objects.filter(
                menu_item=menu_item,
                is_available=True
            )
            
            # Check required variants
            required_variants = available_variants.filter(is_required=True)
            required_types = set(required_variants.values_list('type', flat=True))
            
            selected_types = set(variant.get('type') for variant in selected_variants)
            
            # Check if all required types are selected
            missing_required = required_types - selected_types
            if missing_required:
                return {
                    'error': f'Required variants missing: {", ".join(missing_required)}'
                }
            
            # Validate each selected variant
            validated_variants = []
            for variant_data in selected_variants:
                variant_id = variant_data.get('id')
                if not variant_id:
                    continue
                
                try:
                    variant = MenuItemVariant.objects.get(
                        id=variant_id,
                        menu_item=menu_item,
                        is_available=True
                    )
                    
                    validated_variants.append({
                        'id': variant.id,
                        'name': variant.name,
                        'type': variant.type,
                        'price_modifier': float(variant.price_modifier)
                    })
                except MenuItemVariant.DoesNotExist:
                    return {
                        'error': f'Invalid variant ID: {variant_id}'
                    }
            
            return {'variants': validated_variants}
            
        except Exception as e:
            return {'error': str(e)}


class CartView(APIView):
    """
    Get user's cart and manage cart items
    
    GET /api/user/cart/
    PUT /api/user/cart/items/{item_id}/
    DELETE /api/user/cart/items/{item_id}/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user's active cart"""
        try:
            vendor_id = request.query_params.get('vendor_id')
            
            if vendor_id:
                # Get cart for specific vendor
                try:
                    cart = Cart.objects.get(
                        user=request.user,
                        vendor_id=vendor_id,
                        is_active=True
                    )
                except Cart.DoesNotExist:
                    return Response({
                        'success': True,
                        'cart': None,
                        'message': 'No active cart for this vendor'
                    })
            else:
                # Get most recent active cart
                cart = Cart.objects.filter(
                    user=request.user,
                    is_active=True
                ).order_by('-created_at').first()
                
                if not cart:
                    return Response({
                        'success': True,
                        'cart': None,
                        'message': 'No active cart found'
                    })
            
            # Get cart items
            cart_items = CartItem.objects.filter(cart=cart).select_related('menu_item')
            
            items_data = []
            for item in cart_items:
                items_data.append({
                    'id': item.id,
                    'menu_item': {
                        'id': item.menu_item.id,
                        'name': item.menu_item.name,
                        'description': item.menu_item.description,
                        'image': self._get_optimized_image_url(item.menu_item.image),
                    },
                    'quantity': item.quantity,
                    'base_price': float(item.base_price),
                    'variants': item.variants,
                    'special_instructions': item.special_instructions,
                    'total_price': float(item.total_price),
                    'currency': 'NGN'
                })
            
            return Response({
                'success': True,
                'cart': {
                    'id': cart.id,
                    'vendor': {
                        'id': cart.vendor.id,
                        'name': cart.vendor.business_name,
                        'logo': self._get_optimized_image_url(cart.vendor.logo),
                        'delivery_time': self._estimate_delivery_time(cart.vendor),
                        'offers_delivery': cart.vendor.offers_delivery,
                    },
                    'items': items_data,
                    'total_items': cart.total_items,
                    'total_price': float(cart.total_price),
                    'currency': 'NGN',
                    'created_at': cart.created_at.isoformat(),
                    'updated_at': cart.updated_at.isoformat(),
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, item_id):
        """Update cart item quantity"""
        try:
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
            
            new_quantity = int(request.data.get('quantity', 1))
            if new_quantity < 1:
                return Response({
                    'success': False,
                    'error': 'Quantity must be at least 1'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            cart_item.quantity = new_quantity
            cart_item.save()
            
            return Response({
                'success': True,
                'message': 'Cart item updated successfully',
                'cart_item': {
                    'id': cart_item.id,
                    'quantity': cart_item.quantity,
                    'total_price': float(cart_item.total_price),
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, item_id):
        """Remove item from cart"""
        try:
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
            cart = cart_item.cart
            cart_item.delete()
            
            return Response({
                'success': True,
                'message': 'Item removed from cart successfully',
                'cart_summary': {
                    'total_items': cart.total_items,
                    'total_price': float(cart.total_price),
                }
            }, status=status.HTTP_200_OK)
            
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
