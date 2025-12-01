"""
WhatsApp JWT Cart Service
Handles cart operations for WhatsApp users using JWT tokens
"""
import requests
import logging
from typing import Dict, Optional, List
from django.conf import settings
from django.contrib.auth import get_user_model
from decimal import Decimal

logger = logging.getLogger(__name__)
User = get_user_model()


class WhatsAppCartService:
    """
    Service for managing carts via WhatsApp using JWT tokens
    Stores cart tokens in conversation context
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
    
    def get_cart_token(self, conversation) -> Optional[str]:
        """Get cart token from conversation context"""
        return conversation.context_data.get('cart_token')
    
    def set_cart_token(self, conversation, cart_token: str):
        """Save cart token to conversation context"""
        if not conversation.context_data:
            conversation.context_data = {}
        conversation.context_data['cart_token'] = cart_token
        conversation.save()
    
    def add_to_cart(self, conversation, product_id: int, quantity: int = 1) -> Dict:
        """
        Add product to WhatsApp user's cart
        
        Args:
            conversation: WhatsAppConversation instance
            product_id: Product ID to add
            quantity: Quantity to add
            
        Returns:
            {
                'success': bool,
                'cart_token': str,
                'message': str,
                'total_items': int,
                'error': str (if failed)
            }
        """
        try:
            # Get existing cart token
            cart_token = self.get_cart_token(conversation)
            
            # Prepare request
            url = f"{self.base_url}/api/user/website-cart/add/"
            payload = {
                'product_id': product_id,
                'quantity': quantity
            }
            
            # Include cart token if exists
            if cart_token:
                payload['cart_token'] = cart_token
            
            # Make API request
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    # Save cart token for future use
                    new_cart_token = data.get('cart_token')
                    if new_cart_token:
                        self.set_cart_token(conversation, new_cart_token)
                    
                    return {
                        'success': True,
                        'cart_token': new_cart_token,
                        'message': data.get('message', 'Added to cart'),
                        'total_items': data.get('total_items', 0),
                        'total_amount': data.get('total_amount', 0)
                    }
                else:
                    return {
                        'success': False,
                        'error': data.get('error', 'Failed to add to cart')
                    }
            else:
                logger.error(f"Cart add API returned {response.status_code}: {response.text}")
                return {
                    'success': False,
                    'error': f'API request failed: {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Error adding to WhatsApp cart: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to add item to cart'
            }
    
    def get_cart_items(self, conversation) -> Dict:
        """
        Get all items in WhatsApp user's cart
        
        Returns:
            {
                'success': bool,
                'items': List[dict],
                'total_items': int,
                'total_amount': float,
                'error': str (if failed)
            }
        """
        try:
            cart_token = self.get_cart_token(conversation)
            
            if not cart_token:
                return {
                    'success': True,
                    'items': [],
                    'total_items': 0,
                    'total_amount': 0.0
                }
            
            url = f"{self.base_url}/api/user/website-cart/"
            params = {'cart_token': cart_token}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    return {
                        'success': True,
                        'items': data.get('items', []),
                        'total_items': data.get('total_items', 0),
                        'total_amount': data.get('total_amount', 0.0),
                        'cart_token': data.get('cart_token')
                    }
                else:
                    return {
                        'success': False,
                        'error': data.get('error', 'Failed to fetch cart items')
                    }
            else:
                logger.error(f"Cart list API returned {response.status_code}: {response.text}")
                return {
                    'success': False,
                    'error': f'API request failed: {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Error fetching WhatsApp cart: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to fetch cart items'
            }
    
    def clear_cart(self, conversation) -> Dict:
        """
        Clear all items from WhatsApp user's cart
        
        Returns:
            {
                'success': bool,
                'message': str,
                'error': str (if failed)
            }
        """
        try:
            cart_token = self.get_cart_token(conversation)
            
            if not cart_token:
                return {'success': True, 'message': 'Cart already empty'}
            
            url = f"{self.base_url}/api/user/website-cart/clear/"
            payload = {'cart_token': cart_token}
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    # Clear cart token from conversation
                    if conversation.context_data and 'cart_token' in conversation.context_data:
                        del conversation.context_data['cart_token']
                        conversation.save()
                    
                    return {
                        'success': True,
                        'message': 'Cart cleared successfully'
                    }
                else:
                    return {
                        'success': False,
                        'error': data.get('error', 'Failed to clear cart')
                    }
            else:
                logger.error(f"Cart clear API returned {response.status_code}: {response.text}")
                return {
                    'success': False,
                    'error': f'API request failed: {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Error clearing WhatsApp cart: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to clear cart'
            }
    
    def get_order_summary_for_whatsapp(self, conversation, delivery_address: str, vendor_id: int = None) -> Dict:
        """
        Get order summary using JWT cart system
        Compatible with WhatsApp ordering flow
        
        Args:
            conversation: WhatsAppConversation instance
            delivery_address: User's delivery address
            vendor_id: Optional vendor ID filter
            
        Returns:
            {
                'success': bool,
                'summary': dict,
                'delivery_info': dict,
                'items': List[dict],
                'error': str (if failed)
            }
        """
        try:
            # First get cart items
            cart_result = self.get_cart_items(conversation)
            
            if not cart_result.get('success'):
                return {
                    'success': False,
                    'error': cart_result.get('error', 'Failed to fetch cart items')
                }
            
            cart_items = cart_result.get('items', [])
            
            if not cart_items:
                return {
                    'success': False,
                    'error': 'No items in cart'
                }
            
            # Transform cart items to order summary format
            summary_items = []
            subtotal = Decimal('0.00')
            vendor = None
            
            for item in cart_items:
                product = item.get('product', {})
                quantity = item.get('quantity', 1)
                price = Decimal(str(item.get('total_price', 0)))
                
                summary_items.append({
                    'name': product.get('name', 'Unknown Item'),
                    'quantity': quantity,
                    'price': float(price / quantity) if quantity > 0 else 0,
                    'total': float(price)
                })
                
                subtotal += price
                
                # Get vendor info from first item
                if not vendor and product.get('vendor'):
                    vendor = product['vendor']
            
            # Calculate delivery fee (simplified - could be enhanced)
            delivery_fee = Decimal('500.00')  # Default delivery fee
            platform_fee = Decimal('0.00')  # No platform fee for now
            grand_total = subtotal + delivery_fee + platform_fee
            
            # Build summary response
            summary = {
                'subtotal': float(subtotal),
                'delivery_fee': float(delivery_fee),
                'platform_fee': float(platform_fee),
                'grand_total': float(grand_total)
            }
            
            delivery_info = {
                'vendor': vendor or {'name': 'Unknown Restaurant'},
                'estimated_time': '30-45 minutes',
                'distance_text': 'Calculating...',
                'delivery_address': delivery_address
            }
            
            return {
                'success': True,
                'summary': summary,
                'delivery_info': delivery_info,
                'items': summary_items,
                'cart_token': cart_result.get('cart_token')
            }
            
        except Exception as e:
            logger.error(f"Error getting WhatsApp order summary: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to calculate order summary'
            }