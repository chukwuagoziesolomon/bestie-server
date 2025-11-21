"""
JWT-Based Cart Utility Functions
Works across ALL browsers (Chrome, Safari, Firefox, Edge, iOS, Android)
No cookie dependencies - uses cart_token in request/response body
"""
import uuid
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, F, Q
from decimal import Decimal

from .models import AnonymousCart, WebsiteCartItem, User
from bestyy.restaurant_features.product.models import Product


def generate_cart_token():
    """
    Generate a unique cart token for anonymous users
    Returns: Unique UUID string
    """
    return str(uuid.uuid4())


def get_or_create_cart(cart_token=None, user=None):
    """
    Get or create a cart for anonymous or authenticated user
    
    Args:
        cart_token (str): Existing cart token (optional)
        user (User): Authenticated user (optional)
    
    Returns:
        tuple: (cart_token, is_new)
            - cart_token: JWT token for cart (None for authenticated users)
            - is_new: Boolean indicating if cart was newly created
    """
    if user and user.is_authenticated:
        # For authenticated users, we don't need AnonymousCart
        # Items are directly linked to user
        return None, False
    
    if cart_token:
        # Try to find existing cart
        try:
            cart = AnonymousCart.objects.get(
                cart_token=cart_token,
                expires_at__gt=timezone.now()
            )
            return cart.cart_token, False
        except AnonymousCart.DoesNotExist:
            pass
    
    # Create new cart
    new_token = generate_cart_token()
    cart = AnonymousCart.objects.create(
        cart_token=new_token,
        expires_at=timezone.now() + timedelta(days=30)  # 30 day expiry
    )
    return cart.cart_token, True


def get_available_stock(product):
    """
    Calculate available stock for a product (total stock - reserved stock)
    
    Args:
        product: Product instance
    
    Returns:
        int: Available stock quantity
    """
    from bestyy.restaurant_features.order.models import OrderStockReservation
    
    # Get total reserved stock for this product (only 'reserved' status)
    reserved_quantity = OrderStockReservation.objects.filter(
        product=product,
        status='reserved'
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    # Available stock = total stock - reserved stock
    available = product.stock_quantity - reserved_quantity
    return max(0, available)  # Never return negative


def get_cart_items(cart_token=None, user=None):
    """
    Get all items in the cart
    
    Args:
        cart_token (str): Cart token for anonymous users
        user (User): Authenticated user
    
    Returns:
        QuerySet: WebsiteCartItem objects with product data
    """
    if user and user.is_authenticated:
        return WebsiteCartItem.objects.filter(
            user=user
        ).select_related('product', 'product__vendor')
    
    if cart_token:
        try:
            cart = AnonymousCart.objects.get(
                cart_token=cart_token,
                expires_at__gt=timezone.now()
            )
            return cart.items.all().select_related('product', 'product__vendor')
        except AnonymousCart.DoesNotExist:
            pass
    
    return WebsiteCartItem.objects.none()


def add_to_cart(product_id, quantity, cart_token=None, user=None):
    """
    Add item to cart
    
    Args:
        product_id (int): Product ID to add
        quantity (int): Quantity to add
        cart_token (str): Cart token for anonymous users
        user (User): Authenticated user
    
    Returns:
        tuple: (cart_token, cart_item, created)
            - cart_token: Cart token (None for authenticated users)
            - cart_item: WebsiteCartItem object
            - created: Boolean indicating if item was newly created
    
    Raises:
        ValueError: If product not found or not available
    """
    # Get or create cart
    if not user or not user.is_authenticated:
        cart_token, _ = get_or_create_cart(cart_token)
        cart = AnonymousCart.objects.get(cart_token=cart_token)
    else:
        cart = None
        cart_token = None
    
    # Get product
    try:
        product = Product.objects.get(id=product_id, is_available=True)
    except Product.DoesNotExist:
        raise ValueError("Product not found or not available")
    
    # Check available stock (total - reserved)
    available_stock = get_available_stock(product)
    if available_stock < quantity:
        raise ValueError(f"Only {available_stock} items available in stock (some items are reserved for pending orders)")
    
    # Add or update cart item
    if user and user.is_authenticated:
        cart_item, created = WebsiteCartItem.objects.get_or_create(
            user=user,
            product=product,
            defaults={
                'quantity': quantity,
                'price_snapshot': product.price
            }
        )
    else:
        cart_item, created = WebsiteCartItem.objects.get_or_create(
            anonymous_cart=cart,
            product=product,
            defaults={
                'quantity': quantity,
                'price_snapshot': product.price
            }
        )
    
    if not created:
        # Update quantity if item already exists
        new_quantity = cart_item.quantity + quantity
        
        # Check if new quantity exceeds available stock
        available_stock = get_available_stock(product)
        if available_stock < new_quantity:
            available_to_add = available_stock - cart_item.quantity
            raise ValueError(f"Cannot add {quantity} more. Only {max(0, available_to_add)} available (some items are reserved for pending orders)")
        
        cart_item.quantity = new_quantity
        cart_item.save()
    
    return cart_token, cart_item, created


def update_cart_item(product_id, quantity, cart_token=None, user=None):
    """
    Update quantity of item in cart
    
    Args:
        product_id (int): Product ID to update
        quantity (int): New quantity
        cart_token (str): Cart token for anonymous users
        user (User): Authenticated user
    
    Returns:
        WebsiteCartItem: Updated cart item
    
    Raises:
        WebsiteCartItem.DoesNotExist: If item not in cart
        ValueError: If quantity exceeds stock
    """
    if user and user.is_authenticated:
        cart_item = WebsiteCartItem.objects.get(user=user, product_id=product_id)
    else:
        cart = AnonymousCart.objects.get(cart_token=cart_token)
        cart_item = WebsiteCartItem.objects.get(anonymous_cart=cart, product_id=product_id)
    
    # Check available stock (total - reserved)
    available_stock = get_available_stock(cart_item.product)
    if available_stock < quantity:
        raise ValueError(f"Only {available_stock} items available in stock (some items are reserved for pending orders)")
    
    cart_item.quantity = quantity
    cart_item.save()
    return cart_item


def remove_from_cart(product_id, cart_token=None, user=None):
    """
    Remove item from cart
    
    Args:
        product_id (int): Product ID to remove
        cart_token (str): Cart token for anonymous users
        user (User): Authenticated user
    """
    if user and user.is_authenticated:
        WebsiteCartItem.objects.filter(user=user, product_id=product_id).delete()
    else:
        cart = AnonymousCart.objects.get(cart_token=cart_token)
        WebsiteCartItem.objects.filter(anonymous_cart=cart, product_id=product_id).delete()


def clear_cart(cart_token=None, user=None):
    """
    Clear all items from cart
    
    Args:
        cart_token (str): Cart token for anonymous users
        user (User): Authenticated user
    """
    if user and user.is_authenticated:
        WebsiteCartItem.objects.filter(user=user).delete()
    else:
        cart = AnonymousCart.objects.get(cart_token=cart_token)
        WebsiteCartItem.objects.filter(anonymous_cart=cart).delete()


def merge_carts(cart_token, user):
    """
    Merge anonymous cart into user's cart when they log in
    
    Args:
        cart_token (str): Anonymous cart token
        user (User): User to merge cart into
    
    This is called when:
    1. User logs in with existing cart_token
    2. User registers with existing cart_token
    """
    if not cart_token:
        return
    
    try:
        anonymous_cart = AnonymousCart.objects.get(
            cart_token=cart_token,
            expires_at__gt=timezone.now()
        )
        anonymous_items = anonymous_cart.items.all()
        
        for item in anonymous_items:
            # Try to add to user's cart
            user_item, created = WebsiteCartItem.objects.get_or_create(
                user=user,
                product=item.product,
                defaults={
                    'quantity': item.quantity,
                    'price_snapshot': item.price_snapshot
                }
            )
            
            if not created:
                # If item exists, add quantities
                user_item.quantity += item.quantity
                user_item.save()
        
        # Delete anonymous cart after merging
        anonymous_cart.delete()
        
    except AnonymousCart.DoesNotExist:
        pass


def get_cart_summary(cart_token=None, user=None):
    """
    Get cart summary with totals
    
    Args:
        cart_token (str): Cart token for anonymous users
        user (User): Authenticated user
    
    Returns:
        dict: {
            'total_items': int,
            'total_amount': Decimal,
            'cart_token': str or None
        }
    """
    cart_items = get_cart_items(cart_token=cart_token, user=user)
    
    total_items = sum(item.quantity for item in cart_items)
    total_amount = sum(item.get_subtotal() for item in cart_items)
    
    return {
        'total_items': total_items,
        'total_amount': float(total_amount),
        'cart_token': cart_token
    }


def cleanup_expired_carts():
    """
    Cleanup expired anonymous carts
    Should be run as a periodic task (e.g., daily cron job)
    """
    expired_carts = AnonymousCart.objects.filter(
        expires_at__lte=timezone.now()
    )
    count = expired_carts.count()
    expired_carts.delete()
    return count


def create_stock_reservations_for_order(order):
    """
    Create stock reservations for all items in an order.
    Called when order is placed (status becomes 'pending' or 'confirmed')
    
    Args:
        order: Order instance
    
    Returns:
        list: List of created OrderStockReservation instances
    
    Raises:
        ValueError: If insufficient stock available for any item
    """
    from bestyy.restaurant_features.order.models import OrderStockReservation
    
    reservations = []
    
    # Check stock availability for all items first (validation phase)
    for order_item in order.items.all():
        product = order_item.product
        quantity = order_item.quantity
        
        available_stock = get_available_stock(product)
        if available_stock < quantity:
            raise ValueError(
                f"Insufficient stock for {product.name}. "
                f"Requested: {quantity}, Available: {available_stock}"
            )
    
    # All items have sufficient stock, now create reservations
    for order_item in order.items.all():
        reservation = OrderStockReservation.objects.create(
            order=order,
            product=order_item.product,
            quantity=order_item.quantity,
            status='reserved'
        )
        reservations.append(reservation)
    
    return reservations


def fulfill_stock_reservations(order):
    """
    Fulfill all stock reservations for an order and deduct stock.
    Called when order status changes to 'delivered'.
    
    Args:
        order: Order instance
    
    Returns:
        dict: Results of fulfillment with success count
    """
    from bestyy.restaurant_features.order.models import OrderStockReservation
    
    reservations = OrderStockReservation.objects.filter(
        order=order,
        status='reserved'
    )
    
    fulfilled_count = 0
    failed_items = []
    
    for reservation in reservations:
        if reservation.fulfill():
            fulfilled_count += 1
        else:
            failed_items.append({
                'product': reservation.product.name,
                'quantity': reservation.quantity,
                'available_stock': reservation.product.stock_quantity
            })
    
    return {
        'fulfilled': fulfilled_count,
        'failed': len(failed_items),
        'failed_items': failed_items
    }


def release_stock_reservations(order):
    """
    Release all stock reservations for an order.
    Called when order is cancelled or rejected.
    
    Args:
        order: Order instance
    
    Returns:
        int: Number of reservations released
    """
    from bestyy.restaurant_features.order.models import OrderStockReservation
    
    reservations = OrderStockReservation.objects.filter(
        order=order,
        status='reserved'
    )
    
    released_count = 0
    for reservation in reservations:
        if reservation.release():
            released_count += 1
    
    return released_count
