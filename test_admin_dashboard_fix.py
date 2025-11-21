"""
Test script to verify admin dashboard field fixes.
This checks that the Order model uses total_amount correctly.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.db.models import Sum
from bestyy.restaurant_features.order.models import Order

def test_order_model_fields():
    """Test that Order model has the correct field."""
    print("Testing Order model fields...")
    
    # Check if total_amount field exists
    order_fields = [f.name for f in Order._meta.get_fields()]
    
    print(f"\n✓ Order model fields include:")
    relevant_fields = [f for f in order_fields if 'total' in f or 'amount' in f or 'price' in f]
    for field in relevant_fields:
        print(f"  - {field}")
    
    # Check field types
    if 'total_amount' in order_fields:
        print("\n✓ Order model has 'total_amount' field")
    else:
        print("\n✗ Order model missing 'total_amount' field")
    
    if 'total_price' in order_fields:
        print("✗ Order model has 'total_price' field (should not exist)")
    else:
        print("✓ Order model does not have 'total_price' field (correct)")
    
    # Test aggregation query
    try:
        result = Order.objects.aggregate(total=Sum('total_amount'))
        print(f"\n✓ Aggregation with 'total_amount' works: {result}")
    except Exception as e:
        print(f"\n✗ Aggregation with 'total_amount' failed: {e}")
    
    # Test that total_price fails
    try:
        result = Order.objects.aggregate(total=Sum('total_price'))
        print(f"\n✗ Aggregation with 'total_price' should have failed but didn't: {result}")
    except Exception as e:
        print(f"\n✓ Aggregation with 'total_price' correctly fails: {type(e).__name__}")

if __name__ == '__main__':
    print("=" * 60)
    print("Admin Dashboard Field Fix Verification")
    print("=" * 60)
    test_order_model_fields()
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
