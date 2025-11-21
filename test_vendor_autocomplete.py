"""
Test vendor autocomplete endpoints
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.test import RequestFactory
from bestyy.core_features.user.api.vendor_autocomplete_views import (
    vendor_autocomplete,
    vendor_suggestions,
    vendor_by_cuisine
)
from bestyy.core_features.user.models import VendorProfile, User
from django.contrib.auth.models import AnonymousUser

def test_autocomplete():
    """Test vendor autocomplete endpoint"""
    
    print("\n" + "="*70)
    print("VENDOR AUTOCOMPLETE TEST")
    print("="*70)
    
    # Create test request
    factory = RequestFactory()
    
    # Test 1: Autocomplete search
    print("\n1. Testing autocomplete search...")
    request = factory.get('/api/user/vendors/autocomplete/', {'q': 'jo', 'limit': 5})
    request.user = AnonymousUser()
    
    try:
        response = vendor_autocomplete(request)
        data = response.data
        
        print(f"✅ Status: {response.status_code}")
        print(f"   Success: {data.get('success')}")
        print(f"   Query: {data.get('query')}")
        print(f"   Results: {data.get('count')}")
        
        if data.get('results'):
            for vendor in data['results'][:3]:
                print(f"   - {vendor['business_name']} ({vendor['category']})")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Simple suggestions
    print("\n2. Testing simple suggestions...")
    request = factory.get('/api/user/vendors/suggestions/', {'q': 'jo', 'limit': 5})
    request.user = AnonymousUser()
    
    try:
        response = vendor_suggestions(request)
        data = response.data
        
        print(f"✅ Status: {response.status_code}")
        print(f"   Success: {data.get('success')}")
        print(f"   Suggestions: {data.get('suggestions')}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Search by cuisine
    print("\n3. Testing cuisine search...")
    request = factory.get('/api/user/vendors/by-cuisine/', {'cuisine': 'Nigerian', 'limit': 5})
    request.user = AnonymousUser()
    
    try:
        response = vendor_by_cuisine(request)
        data = response.data
        
        print(f"✅ Status: {response.status_code}")
        print(f"   Success: {data.get('success')}")
        print(f"   Cuisine: {data.get('cuisine')}")
        print(f"   Results: {data.get('count')}")
        
        if data.get('results'):
            for vendor in data['results'][:3]:
                print(f"   - {vendor['business_name']} ({vendor['product_count']} products)")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Error handling - missing query
    print("\n4. Testing error handling...")
    request = factory.get('/api/user/vendors/autocomplete/', {})
    request.user = AnonymousUser()
    
    try:
        response = vendor_autocomplete(request)
        data = response.data
        
        print(f"✅ Status: {response.status_code}")
        print(f"   Success: {data.get('success')}")
        print(f"   Error: {data.get('error')}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 5: Check vendor data
    print("\n5. Checking vendor data in database...")
    vendors = VendorProfile.objects.filter(
        verification_status='approved',
        is_suspended=False
    )[:5]
    
    print(f"   Total approved vendors: {VendorProfile.objects.filter(verification_status='approved', is_suspended=False).count()}")
    print(f"   Sample vendors:")
    for v in vendors:
        print(f"   - {v.business_name} ({v.business_category})")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70 + "\n")


if __name__ == '__main__':
    test_autocomplete()
