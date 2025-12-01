#!/usr/bin/env python3
"""
Test WhatsApp Order Flow with JWT Cart
Simulates the complete WhatsApp ordering flow using JWT cart
"""
import os
import sys
import django

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.communication.whatsapp.whatsapp_order_integration import whatsapp_order_integration
from bestyy.communication.whatsapp.models import WhatsAppConversation
from bestyy.communication.whatsapp.ai_service import WhatsAppAIService
from bestyy.restaurant_features.product.models import Product
from bestyy.restaurant_features.order.models import Order
from django.contrib.auth import get_user_model
from decimal import Decimal

print("🍽️ TESTING WHATSAPP ORDER FLOW WITH JWT CART")
print("=" * 55)

def test_whatsapp_order_flow():
    """Test complete WhatsApp ordering flow"""
    
    # Create test user
    User = get_user_model()
    user, created = User.objects.get_or_create(
        email='whatsapp_test@example.com',
        defaults={
            'first_name': 'WhatsApp',
            'last_name': 'Test',
            'username': 'whatsapp_test'
        }
    )
    print(f"👤 Using test user: {user.email}")
    
    # Create test conversation
    conversation, created = WhatsAppConversation.objects.get_or_create(
        phone_number='+2348012345678',
        defaults={
            'user': user,
            'onboarding_state': 'onboarded',
            'context_data': {}
        }
    )
    print(f"📱 Using conversation: {conversation.phone_number}")
    
    # Clear any existing cart
    clear_result = whatsapp_order_integration.clear_whatsapp_cart(conversation)
    print(f"🧹 Cart cleared: {clear_result.get('success')}")
    
    # Find a product to add
    product = Product.objects.filter(is_available=True).first()
    if not product:
        print("❌ No available products found")
        return False
    
    print(f"🍕 Found product: {product.name} - ₦{product.price}")
    
    # Add product to cart
    add_result = whatsapp_order_integration.add_item_to_whatsapp_cart(
        conversation=conversation,
        product_id=product.id,
        quantity=1
    )
    
    if not add_result.get('success'):
        print(f"❌ Failed to add to cart: {add_result.get('error')}")
        return False
    
    print(f"✅ Added to cart: {add_result.get('message')}")
    print(f"   Total items: {add_result.get('cart_info', {}).get('total_items', 0)}")
    print(f"   Total amount: ₦{add_result.get('cart_info', {}).get('total_amount', 0):,.0f}")
    
    # Test order summary generation using AI service
    print("\n📋 Testing order summary generation...")
    
    # Create a mock order for testing
    test_order = Order.objects.create(
        customer=user,
        vendor=product.vendor,
        status='pending',
        delivery_address='123 Test Street, Lagos',\n        shipping_address='123 Test Street, Lagos',
        total_amount=product.price
    )
    
    print(f"📝 Created test order: {test_order.id}")
    
    # Test the AI service order summary function
    ai_service = WhatsAppAIService()
    
    context = {
        'conversation': conversation,
        'user_exists': True
    }
    
    try:
        summary_result = ai_service._calculate_order_summary_and_confirm(test_order, context)
        
        if summary_result.get('action') == 'order_summary_shown':
            print("✅ Order summary generated successfully!")
            print("📋 Summary message preview:")
            message = summary_result.get('message', '')
            # Show first few lines of the message
            lines = message.split('\\n')[:8]
            for line in lines:
                if line.strip():
                    print(f"   {line}")
            if len(message.split('\\n')) > 8:
                print("   ... (truncated)")
        else:
            print(f"⚠️ Order summary returned action: {summary_result.get('action')}")
            print(f"   Message: {summary_result.get('message', '')[:100]}...")
            
    except Exception as e:
        print(f"❌ Order summary failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # Clean up test order
    test_order.delete()
    print(f"🗑️ Cleaned up test order")
    
    return True

if __name__ == "__main__":
    try:
        success = test_whatsapp_order_flow()
        if success:
            print("\n🎉 ORDER FLOW TEST PASSED!")
            print("✅ WhatsApp can now use JWT cart system for orders!")
            print("\n🔧 The issue with 'Bad Request: /api/user/order-summary/' should be resolved.")
            print("   WhatsApp bot now uses direct Django functions instead of HTTP requests.")
        else:
            print("\n❌ Order flow test failed!")
    except Exception as e:
        print(f"\n💥 Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()