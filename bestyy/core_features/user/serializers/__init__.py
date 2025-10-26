"""
Package for all serializers used in the user app.

This module uses lazy imports to prevent circular import issues.
Import the serializers directly from their respective modules when needed.
"""
# Define __all__ for public API
__all__ = [
    # User serializers
    'UserSerializer',
    'UserProfileSerializer',
    'UserSignupSerializer',
    'UserLoginSerializer',
    'ChangePasswordSerializer',
    'UserDetailSerializer',
    'UserRegistrationSerializer',
    
    # Vendor serializers
    'VendorProfileSerializer',
    # 'VendorApplicationSerializer',  # Not available; keep exports minimal
    
    # Courier serializers
    'CourierProfileSerializer',
    # 'CourierSignupSerializer',
    'CourierListSerializer',
    'CourierApplicationSerializer',
    
    # Menu serializers
    'MenuItemSerializer',
    
    # Order serializers
    'OrderSerializer',
    'UserOrderSerializer',
    'VendorOrderTrackingSerializer',
    
    # Address serializers
    'AddressSerializer',
    
    # Favorite serializers
    'FavoriteSerializer',
    

]

def __getattr__(name):
    """
    Lazy import of serializers to prevent circular imports.
    This allows importing serializers directly from this module while
    avoiding circular imports by only importing them when actually needed.
    """
    if name in ('UserSerializer', 'UserProfileSerializer', 'UserSignupSerializer', 'UserLoginSerializer', 'ChangePasswordSerializer', 'UserDetailSerializer', 'UserRegistrationSerializer'):
        from .user_serializers import (
            UserSerializer, UserProfileSerializer, UserSignupSerializer,
            UserLoginSerializer, ChangePasswordSerializer, UserDetailSerializer,
            UserRegistrationSerializer
        )
        if name == 'UserSerializer':
            return UserSerializer
        elif name == 'UserProfileSerializer':
            return UserProfileSerializer
        elif name == 'UserSignupSerializer':
            return UserSignupSerializer
        elif name == 'UserLoginSerializer':
            return UserLoginSerializer
        elif name == 'ChangePasswordSerializer':
            return ChangePasswordSerializer
        elif name == 'UserDetailSerializer':
            return UserDetailSerializer
        return UserRegistrationSerializer
        
    elif name in ('VendorProfileSerializer',):
        from .vendor_serializers import VendorProfileSerializer
        if name == 'VendorProfileSerializer':
            return VendorProfileSerializer
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
        
    elif name in ('CourierProfileSerializer', 'CourierListSerializer'):
        from .courier_serializers import (
            CourierProfileSerializer,
            CourierListSerializer,
        )
        if name == 'CourierProfileSerializer':
            return CourierProfileSerializer
        elif name == 'CourierListSerializer':
            return CourierListSerializer
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
        
    elif name == 'MenuItemSerializer':
        from .menu_serializers import MenuItemSerializer
        return MenuItemSerializer
        
    elif name in ('OrderSerializer', 'UserOrderSerializer', 'VendorOrderTrackingSerializer'):
        from .order_serializers import OrderSerializer, UserOrderSerializer, VendorOrderTrackingSerializer
        if name == 'OrderSerializer':
            return OrderSerializer
        elif name == 'UserOrderSerializer':
            return UserOrderSerializer
        elif name == 'VendorOrderTrackingSerializer':
            return VendorOrderTrackingSerializer
            
    elif name == 'AddressSerializer':
        from .address_serializers import AddressSerializer
        return AddressSerializer
        
    elif name == 'FavoriteSerializer':
        from .favorite_serializers import FavoriteSerializer
        return FavoriteSerializer
        
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
