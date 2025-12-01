#!/usr/bin/env python3
"""
Test WhatsApp JWT Cart Integration
Verifies that WhatsApp bot can use JWT cart system
"""
import os
import sys
import django

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.communication.whatsapp.direct_whatsapp_cart_service import DirectWhatsAppCartService
from bestyy.communication.whatsapp.whatsapp_order_integration import whatsapp_order_integration
from bestyy.communication.whatsapp.models import WhatsAppConversation
from bestyy.restaurant_features.product.models import Product
from django.contrib.auth import get_user_model

print("🛒 TESTING WHATSAPP JWT CART INTEGRATION")
print("=" * 50)

def test_jwt_cart_integration():
    """Test JWT cart integration for WhatsApp"""
    
    # Create or get test conversation
    conversation, created = WhatsAppConversation.objects.get_or_create(
        phone_number='+2348012345678',
        defaults={'context_data': {}}
    )
    
    print(f"📱 Using conversation: {conversation.phone_number}")
    if created:
        print("✨ Created new conversation")
    else:
        print("🔄 Using existing conversation")
    
    # Test 1: Clear cart first
    print("\n🧹 Test 1: Clear cart")
    clear_result = whatsapp_order_integration.clear_whatsapp_cart(conversation)
    print(f"Clear result: {clear_result}")
    
    # Test 2: Get empty cart summary
    print("\n📊 Test 2: Get empty cart summary")
    summary_result = whatsapp_order_integration.get_whatsapp_cart_summary(conversation)
    print(f"Empty cart summary: {summary_result.get('summary', 'No summary')}")
    
    # Test 3: Try to find a product to add
    print("\n🔍 Test 3: Find product to add")
    product = Product.objects.filter(is_available=True).first()
    if not product:
        print("❌ No available products found. Create some test products first.")
        return False
    
    print(f"Found product: {product.name} (ID: {product.id}) - ₦{product.price}")
    
    # Test 4: Add product to cart
    print("\n➕ Test 4: Add product to cart")
    add_result = whatsapp_order_integration.add_item_to_whatsapp_cart(
        conversation=conversation,
        product_id=product.id,
        quantity=1
    )
    print(f"Add result: {add_result}")
    
    if not add_result.get('success'):
        print(f"❌ Failed to add to cart: {add_result.get('error')}")
        return False
    
    # Test 5: Get cart summary with items
    print("\n📊 Test 5: Get cart summary with items")
    summary_result = whatsapp_order_integration.get_whatsapp_cart_summary(conversation)
    print(f"Cart with items:")
    print(summary_result.get('summary', 'No summary'))
    
    # Test 6: Test order summary
    print("\n📋 Test 6: Test order summary")
    cart_service = DirectWhatsAppCartService()
    order_summary = cart_service.get_order_summary_for_whatsapp(
        conversation=conversation,
        delivery_address="123 Test Street, Lagos"
    )
    
    if order_summary.get('success'):
        print("✅ Order summary generated successfully!")
        summary = order_summary.get('summary', {})
        print(f"   Subtotal: ₦{summary.get('subtotal', 0):,.2f}")
        print(f"   Delivery Fee: ₦{summary.get('delivery_fee', 0):,.2f}")
        print(f"   Grand Total: ₦{summary.get('grand_total', 0):,.2f}")
        
        items = order_summary.get('items', [])
        print(f"   Items: {len(items)} item(s)")
        for item in items:
            print(f"     • {item.get('name')} x{item.get('quantity')} = ₦{item.get('total'):,.2f}")
    else:
        print(f"❌ Order summary failed: {order_summary.get('error')}")
        return False
    
    # Test 7: Clear cart again
    print("\n🧹 Test 7: Clear cart again")
    clear_result = whatsapp_order_integration.clear_whatsapp_cart(conversation)
    print(f"Final clear result: {clear_result}")
    
    return True

if __name__ == "__main__":
    try:
        success = test_jwt_cart_integration()
        if success:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ WhatsApp JWT cart integration is working correctly!")
        else:
            print("\n❌ Some tests failed!")
    except Exception as e:
        print(f"\n💥 Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()