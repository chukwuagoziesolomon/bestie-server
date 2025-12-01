"""
WhatsApp Order Integration Service
Updates existing WhatsApp ordering to use JWT cart system
"""
import logging
from typing import Dict, Optional
from .direct_whatsapp_cart_service import DirectWhatsAppCartService

logger = logging.getLogger(__name__)


class WhatsAppOrderIntegration:
    """
    Integration service that bridges WhatsApp ordering with JWT cart system
    """
    
    def __init__(self):
        self.cart_service = DirectWhatsAppCartService()
    
    def add_item_to_whatsapp_cart(self, conversation, product_id: int, quantity: int = 1) -> Dict:
        """
        Add item to WhatsApp user's JWT cart
        
        Returns:
            {
                'success': bool,
                'message': str,
                'cart_info': dict,
                'error': str (if failed)
            }
        """
        try:
            result = self.cart_service.add_to_cart(
                conversation=conversation,
                product_id=product_id,
                quantity=quantity
            )
            
            if result.get('success'):
                return {
                    'success': True,
                    'message': f"✅ Added to your cart! You now have {result.get('total_items', 0)} item(s)",
                    'cart_info': {
                        'total_items': result.get('total_items', 0),
                        'total_amount': result.get('total_amount', 0),
                        'cart_token': result.get('cart_token')
                    }
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to add item to cart'),
                    'message': "Sorry, I couldn't add that to your cart. Please try again."
                }
                
        except Exception as e:
            logger.error(f"Error in WhatsApp cart integration: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': "Sorry, there was an issue adding that to your cart."
            }
    
    def get_whatsapp_cart_summary(self, conversation) -> Dict:
        """
        Get cart summary for WhatsApp user
        
        Returns:
            {
                'success': bool,
                'items': List[dict],
                'summary': str,  # Formatted summary text
                'cart_info': dict,
                'error': str (if failed)
            }
        """
        try:
            result = self.cart_service.get_cart_items(conversation)
            
            if result.get('success'):
                items = result.get('items', [])
                total_items = result.get('total_items', 0)
                total_amount = result.get('total_amount', 0)
                
                if not items:
                    return {
                        'success': True,
                        'items': [],
                        'summary': "🛒 Your cart is empty. What would you like to order?",
                        'cart_info': {'total_items': 0, 'total_amount': 0}
                    }
                
                # Format summary text
                summary = f"🛒 *Your Cart Summary:*\\n\\n"
                
                for item in items:
                    product = item.get('product', {})
                    quantity = item.get('quantity', 1)
                    total_price = item.get('total_price', 0)
                    
                    summary += f"• {product.get('name', 'Unknown Item')} x{quantity} = ₦{total_price:,.0f}\\n"
                
                summary += f"\\n💰 *Total: ₦{total_amount:,.0f}*\\n"
                summary += f"📊 *{total_items} item(s) in cart*"
                
                return {
                    'success': True,
                    'items': items,
                    'summary': summary,
                    'cart_info': {
                        'total_items': total_items,
                        'total_amount': total_amount,
                        'cart_token': result.get('cart_token')
                    }
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to get cart items'),
                    'summary': "Sorry, I couldn't fetch your cart right now."
                }
                
        except Exception as e:
            logger.error(f"Error getting WhatsApp cart summary: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'summary': "Sorry, there was an issue fetching your cart."
            }
    
    def clear_whatsapp_cart(self, conversation) -> Dict:
        """
        Clear WhatsApp user's cart
        
        Returns:
            {
                'success': bool,
                'message': str,
                'error': str (if failed)
            }
        """
        try:
            result = self.cart_service.clear_cart(conversation)
            
            if result.get('success'):
                return {
                    'success': True,
                    'message': "🗑️ Cart cleared! Ready to start a new order?"
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to clear cart'),
                    'message': "Sorry, I couldn't clear your cart right now."
                }
                
        except Exception as e:
            logger.error(f"Error clearing WhatsApp cart: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': "Sorry, there was an issue clearing your cart."
            }


# Global instance for easy import
whatsapp_order_integration = WhatsAppOrderIntegration()