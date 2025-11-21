"""
JWT-Based Cart API Views
Works across ALL browsers without cookies
Cart token is passed in request/response body
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
import logging

from ..cart_utils import (
    get_or_create_cart,
    get_cart_items,
    add_to_cart,
    update_cart_item,
    remove_from_cart,
    clear_cart,
    get_cart_summary,
    merge_carts
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def cart_add_view(request):
    """
    Add product to cart - Works across ALL browsers
    No cookies required, uses cart_token in request/response body
    
    POST /api/user/website-cart/add/
    Body: {
        "product_id": 123,
        "quantity": 2,
        "cart_token": "uuid-string" (optional, for existing carts)
    }
    
    Response: {
        "success": true,
        "cart_token": "uuid-string",  # CRITICAL: Client must save this
        "message": "Product added to cart",
        "total_items": 5,
        "product": {...}
    }
    """
    product_id = request.data.get('product_id')
    quantity = request.data.get('quantity', 1)
    cart_token = request.data.get('cart_token')  # Client sends this
    
    # Validate inputs
    if not product_id:
        return Response({
            'success': False,
            'error': 'product_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        quantity = int(quantity)
        if quantity < 1:
            return Response({
                'success': False,
                'error': 'quantity must be at least 1'
            }, status=status.HTTP_400_BAD_REQUEST)
    except (ValueError, TypeError):
        return Response({
            'success': False,
            'error': 'Invalid quantity'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get user if authenticated
    user = request.user if request.user.is_authenticated else None
    
    try:
        with transaction.atomic():
            # Add to cart
            new_cart_token, cart_item, created = add_to_cart(
                product_id=product_id,
                quantity=quantity,
                cart_token=cart_token,
                user=user
            )
            
            # Get cart summary
            summary = get_cart_summary(cart_token=new_cart_token, user=user)
            
            logger.info(f"[CART_ADD] {'Created' if created else 'Updated'} cart item for product {product_id}")
            
            return Response({
                'success': True,
                'cart_token': new_cart_token,  # CRITICAL: Return this to client
                'message': 'Product added to cart' if created else 'Cart updated',
                'total_items': summary['total_items'],
                'total_amount': summary['total_amount'],
                'product': {
                    'id': cart_item.product.id,
                    'name': cart_item.product.name,
                    'quantity': cart_item.quantity,
                    'price': float(cart_item.price_snapshot),
                    'subtotal': float(cart_item.get_subtotal())
                }
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
    except ValueError as e:
        logger.warning(f"[CART_ADD] Validation error: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"[CART_ADD] Error: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': 'Failed to add to cart'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def cart_list_view(request):
    """
    Get all items in cart - Works across ALL browsers
    Cart token can be passed as query param or in header
    
    GET /api/user/website-cart/
    Query params:
        - cart_token: UUID string (optional for authenticated users)
    OR
    Headers:
        - X-Cart-Token: UUID string (optional for authenticated users)
    
    Response: {
        "cart_token": "uuid-string",
        "products": [...],
        "total_items": 5,
        "total_amount": 12500.00
    }
    """
    # Get cart_token from query params or header
    cart_token = request.GET.get('cart_token') or request.headers.get('X-Cart-Token')
    user = request.user if request.user.is_authenticated else None
    
    try:
        # Get cart items
        cart_items = get_cart_items(cart_token=cart_token, user=user)
        
        # Serialize products
        products_data = []
        for item in cart_items:
            product = item.product
            products_data.append({
                'id': product.id,
                'name': product.name,
                'description': product.description,
                'vendor': {
                    'id': product.vendor.id,
                    'name': product.vendor.business_name,
                },
                'image': product.image,
                'category': product.category.name if product.category else None,
                'price': float(product.price),
                'price_snapshot': float(item.price_snapshot),  # Price when added to cart
                'is_available': product.is_available,
                'stock_quantity': product.stock_quantity,
                'quantity': item.quantity,
                'subtotal': float(item.get_subtotal()),
                'added_at': item.created_at.isoformat()
            })
        
        # Calculate totals
        total_items = sum(item.quantity for item in cart_items)
        total_amount = sum(float(item.get_subtotal()) for item in cart_items)
        
        return Response({
            'success': True,
            'cart_token': cart_token,
            'products': products_data,
            'total_items': total_items,
            'total_amount': total_amount,
            'currency': 'NGN'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"[CART_LIST] Error: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': 'Failed to fetch cart'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def cart_update_view(request):
    """
    Update quantity of item in cart
    
    POST /api/user/website-cart/update/
    Body: {
        "product_id": 123,
        "quantity": 3,
        "cart_token": "uuid-string"
    }
    
    Response: {
        "success": true,
        "cart_token": "uuid-string",
        "product": {...}
    }
    """
    product_id = request.data.get('product_id')
    quantity = request.data.get('quantity', 1)
    cart_token = request.data.get('cart_token')
    
    if not product_id:
        return Response({
            'success': False,
            'error': 'product_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        quantity = int(quantity)
        if quantity < 1:
            return Response({
                'success': False,
                'error': 'quantity must be at least 1'
            }, status=status.HTTP_400_BAD_REQUEST)
    except (ValueError, TypeError):
        return Response({
            'success': False,
            'error': 'Invalid quantity'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user if request.user.is_authenticated else None
    
    try:
        cart_item = update_cart_item(
            product_id=product_id,
            quantity=quantity,
            cart_token=cart_token,
            user=user
        )
        
        logger.info(f"[CART_UPDATE] Updated product {product_id} to quantity {quantity}")
        
        return Response({
            'success': True,
            'cart_token': cart_token,
            'product': {
                'id': cart_item.product.id,
                'name': cart_item.product.name,
                'quantity': cart_item.quantity,
                'price': float(cart_item.price_snapshot),
                'subtotal': float(cart_item.get_subtotal())
            }
        }, status=status.HTTP_200_OK)
        
    except ValueError as e:
        logger.warning(f"[CART_UPDATE] Validation error: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"[CART_UPDATE] Error: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': 'Failed to update cart'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def cart_remove_view(request):
    """
    Remove item from cart
    
    POST /api/user/website-cart/remove/
    Body: {
        "product_id": 123,
        "cart_token": "uuid-string"
    }
    
    Response: {
        "success": true,
        "cart_token": "uuid-string",
        "message": "Product removed from cart"
    }
    """
    product_id = request.data.get('product_id')
    cart_token = request.data.get('cart_token')
    
    if not product_id:
        return Response({
            'success': False,
            'error': 'product_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user if request.user.is_authenticated else None
    
    try:
        remove_from_cart(
            product_id=product_id,
            cart_token=cart_token,
            user=user
        )
        
        logger.info(f"[CART_REMOVE] Removed product {product_id}")
        
        return Response({
            'success': True,
            'cart_token': cart_token,
            'message': 'Product removed from cart'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"[CART_REMOVE] Error: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': 'Failed to remove from cart'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def cart_clear_view(request):
    """
    Clear all items from cart
    
    POST /api/user/website-cart/clear/
    Body: {
        "cart_token": "uuid-string"
    }
    
    Response: {
        "success": true,
        "message": "Cart cleared"
    }
    """
    cart_token = request.data.get('cart_token')
    user = request.user if request.user.is_authenticated else None
    
    try:
        clear_cart(cart_token=cart_token, user=user)
        
        logger.info(f"[CART_CLEAR] Cleared cart")
        
        return Response({
            'success': True,
            'message': 'Cart cleared'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"[CART_CLEAR] Error: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': 'Failed to clear cart'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def cart_summary_view(request):
    """
    Get cart summary (item count and total only)
    
    GET /api/user/website-cart/summary/
    Query params:
        - cart_token: UUID string
    OR
    Headers:
        - X-Cart-Token: UUID string
    
    Response: {
        "total_items": 5,
        "total_amount": 12500.00,
        "cart_token": "uuid-string"
    }
    """
    cart_token = request.GET.get('cart_token') or request.headers.get('X-Cart-Token')
    user = request.user if request.user.is_authenticated else None
    
    try:
        summary = get_cart_summary(cart_token=cart_token, user=user)
        
        return Response({
            'success': True,
            'total_items': summary['total_items'],
            'total_amount': summary['total_amount'],
            'cart_token': summary['cart_token'],
            'currency': 'NGN'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"[CART_SUMMARY] Error: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': 'Failed to fetch cart summary'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def cart_merge_view(request):
    """
    Merge anonymous cart into user's cart after login/registration
    
    POST /api/user/website-cart/merge/
    Body: {
        "cart_token": "uuid-string"
    }
    
    Note: User must be authenticated
    
    Response: {
        "success": true,
        "message": "Cart merged successfully",
        "total_items": 5
    }
    """
    if not request.user.is_authenticated:
        return Response({
            'success': False,
            'error': 'Authentication required'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    cart_token = request.data.get('cart_token')
    
    if not cart_token:
        return Response({
            'success': False,
            'error': 'cart_token is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Merge carts
        merge_carts(cart_token=cart_token, user=request.user)
        
        # Get updated summary
        summary = get_cart_summary(user=request.user)
        
        logger.info(f"[CART_MERGE] Merged cart {cart_token[:8]}... into user {request.user.email}")
        
        return Response({
            'success': True,
            'message': 'Cart merged successfully',
            'total_items': summary['total_items'],
            'total_amount': summary['total_amount']
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"[CART_MERGE] Error: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': 'Failed to merge cart'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
