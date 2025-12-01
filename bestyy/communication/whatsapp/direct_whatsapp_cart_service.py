"""
Direct WhatsApp Cart Integration
Uses Django functions directly instead of HTTP requests
"""
import logging
from typing import Dict, Optional
from django.contrib.auth import get_user_model
from decimal import Decimal

logger = logging.getLogger(__name__)
User = get_user_model()


class DirectWhatsAppCartService:
    """
    Service for managing carts via WhatsApp using direct Django function calls
    """
    
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
        Add product to WhatsApp user's cart using direct Django functions
        """
        try:
            # Import cart utilities directly
            from bestyy.core_features.user.cart_utils import add_to_cart, get_cart_summary
            
            # Get existing cart token
            cart_token = self.get_cart_token(conversation)
            
            # Get user if conversation is linked to a user
            user = conversation.user if conversation.user else None
            
            # Add to cart using direct Django function
            new_cart_token, cart_item, created = add_to_cart(
                product_id=product_id,
                quantity=quantity,
                cart_token=cart_token,
                user=user
            )
            
            # Save cart token for future use
            if new_cart_token:
                self.set_cart_token(conversation, new_cart_token)
            
            # Get updated cart summary
            summary = get_cart_summary(cart_token=new_cart_token, user=user)
            
            message = 'Product added to cart' if created else 'Cart updated'
            
            return {
                'success': True,
                'cart_token': new_cart_token,
                'message': message,
                'total_items': summary['total_items'],
                'total_amount': summary['total_amount']
            }
                
        except Exception as e:
            logger.error(f"Error adding to WhatsApp cart: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f'Failed to add item to cart: {str(e)}'
            }
    
    def get_cart_items(self, conversation) -> Dict:
        """
        Get all items in WhatsApp user's cart using direct Django functions
        """
        try:
            from bestyy.core_features.user.cart_utils import get_cart_items
            
            cart_token = self.get_cart_token(conversation)
            user = conversation.user if conversation.user else None
            
            if not cart_token:
                return {
                    'success': True,
                    'items': [],
                    'total_items': 0,
                    'total_amount': 0.0
                }
            
            # Get cart items using direct Django function
            cart_items = get_cart_items(cart_token=cart_token, user=user)
            
            # Transform to expected format
            items = []
            total_items = 0
            total_amount = Decimal('0.00')
            
            for cart_item in cart_items:
                item_data = {
                    'id': cart_item.id,
                    'product': {
                        'id': cart_item.product.id,
                        'name': cart_item.product.name,
                        'price': float(cart_item.product.price),
                        'vendor': {
                            'id': cart_item.product.vendor.id,
                            'name': cart_item.product.vendor.business_name
                        } if cart_item.product.vendor else None
                    },
                    'quantity': cart_item.quantity,
                    'total_price': float(cart_item.product.price * cart_item.quantity)
                }
                items.append(item_data)
                total_items += cart_item.quantity
                total_amount += cart_item.product.price * cart_item.quantity
            
            return {
                'success': True,
                'items': items,
                'total_items': total_items,
                'total_amount': float(total_amount),
                'cart_token': cart_token
            }
                
        except Exception as e:
            logger.error(f"Error fetching WhatsApp cart: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f'Failed to fetch cart items: {str(e)}'
            }
    
    def clear_cart(self, conversation) -> Dict:
        """
        Clear all items from WhatsApp user's cart using direct Django functions
        """
        try:
            from bestyy.core_features.user.cart_utils import clear_cart
            
            cart_token = self.get_cart_token(conversation)
            user = conversation.user if conversation.user else None
            
            if not cart_token:
                return {'success': True, 'message': 'Cart already empty'}
            
            # Clear cart using direct Django function
            success = clear_cart(cart_token=cart_token, user=user)
            
            if success:
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
                    'error': 'Failed to clear cart'
                }
                
        except Exception as e:
            logger.error(f"Error clearing WhatsApp cart: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f'Failed to clear cart: {str(e)}'
            }
    
    def get_order_summary_for_whatsapp(self, conversation, delivery_address: str, vendor_id: int = None) -> Dict:
        """
        Get order summary using direct Django functions
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
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f'Failed to calculate order summary: {str(e)}'
            }