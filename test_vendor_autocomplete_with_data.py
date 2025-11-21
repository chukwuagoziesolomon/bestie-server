"""
Create test vendors and test autocomplete
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.test import RequestFactory
from bestyy.core_features.user.api.vendor_autocomplete_views import vendor_autocomplete, vendor_suggestions
from bestyy.core_features.user.models import VendorProfile, User
from bestyy.restaurant_features.product.models import Product
from django.contrib.auth.models import AnonymousUser
from decimal import Decimal

def create_test_vendors():
    """Create test vendors for autocomplete testing"""
    
    print("\n" + "="*70)
    print("CREATING TEST VENDORS")
    print("="*70)
    
    # Create test vendors
    vendors_data = [
        {
            'email': 'jollof@example.com',
            'business_name': 'Jollof Kitchen Lagos',
            'business_category': 'Nigerian Restaurant',
            'business_description': 'Authentic Nigerian Jollof rice and local dishes',
            'business_address': '123 Main Street, Lagos',
            'service_areas': 'Lekki, Victoria Island, Ikoyi',
        },
        {
            'email': 'jos@example.com',
            'business_name': 'Jos Suya Spot',
            'business_category': 'Street Food',
            'business_description': 'Best suya in town with special Jos flavors',
            'business_address': '456 Food Avenue, Abuja',
            'service_areas': 'Garki, Wuse, Maitama',
        },
        {
            'email': 'mama@example.com',
            'business_name': 'Mama Nkechi Kitchen',
            'business_category': 'Nigerian Restaurant',
            'business_description': 'Home-cooked Nigerian meals like mama used to make',
            'business_address': '789 Home Road, Port Harcourt',
            'service_areas': 'GRA, Rumuola, Eleme',
        },
        {
            'email': 'joint@example.com',
            'business_name': 'The Joint Restaurant',
            'business_category': 'Continental',
            'business_description': 'Mix of Nigerian and continental cuisine',
            'business_address': '321 Restaurant Lane, Lagos',
            'service_areas': 'Surulere, Yaba, Ikeja',
        },
    ]
    
    created_vendors = []
    for idx, data in enumerate(vendors_data):
        # Get or create user for this vendor
        user, user_created = User.objects.get_or_create(
            email=data['email'],
            defaults={
                'first_name': data['business_name'].split()[0],
                'last_name': 'Restaurant',
                'role': 'vendor',
                'phone': f'+23480123456{idx}'
            }
        )
        
        # Get the auto-created vendor profile and update it
        try:
            vendor = VendorProfile.objects.get(user=user)
            vendor.business_name = data['business_name']
            vendor.phone = f'+23480123456{idx}'
            vendor.business_category = data['business_category']
            vendor.business_description = data['business_description']
            vendor.business_address = data['business_address']
            vendor.service_areas = data['service_areas']
            vendor.delivery_radius = '10km'
            vendor.offers_delivery = True
            vendor.verification_status = 'approved'
            vendor.is_suspended = False
            vendor.save()
            created = user_created
        except VendorProfile.DoesNotExist:
            # Create if it doesn't exist (shouldn't happen with signals)
            vendor = VendorProfile.objects.create(
                user=user,
                business_name=data['business_name'],
                phone=f'+23480123456{idx}',
                business_category=data['business_category'],
                business_description=data['business_description'],
                business_address=data['business_address'],
                service_areas=data['service_areas'],
                delivery_radius='10km',
                offers_delivery=True,
                verification_status='approved',
                is_suspended=False,
            )
            created = True
        
        if created:
            print(f"✅ Created: {vendor.business_name}")
            
            # Add some products to vendors
            if 'Jollof' in vendor.business_name:
                Product.objects.get_or_create(
                    name='Jollof Rice',
                    vendor=vendor,
                    defaults={
                        'price': Decimal('2500.00'),
                        'description': 'Delicious Nigerian Jollof rice',
                        'is_available': True,
                        'stock_quantity': 50,
                    }
                )
            elif 'Suya' in vendor.business_name:
                Product.objects.get_or_create(
                    name='Beef Suya',
                    vendor=vendor,
                    defaults={
                        'price': Decimal('3000.00'),
                        'description': 'Spicy grilled beef',
                        'is_available': True,
                        'stock_quantity': 30,
                    }
                )
        else:
            print(f"⚠️  Already exists: {vendor.business_name}")
        
        created_vendors.append(vendor)
    
    print(f"\n✅ Total vendors in database: {VendorProfile.objects.filter(verification_status='approved').count()}")
    return created_vendors


def test_autocomplete_with_data():
    """Test autocomplete with real data"""
    
    print("\n" + "="*70)
    print("TESTING AUTOCOMPLETE WITH DATA")
    print("="*70)
    
    factory = RequestFactory()
    
    # Test 1: Search for "jo"
    print("\n1. Searching for 'jo'...")
    request = factory.get('/api/user/vendors/autocomplete/', {'q': 'jo', 'limit': 10})
    request.user = AnonymousUser()
    
    response = vendor_autocomplete(request)
    data = response.data
    
    print(f"   Results: {data.get('count')}")
    if data.get('results'):
        for vendor in data['results']:
            print(f"   - {vendor['business_name']} ({vendor['category']})")
            print(f"     Address: {vendor['address']}")
            print(f"     Products: {vendor['product_count']}")
    
    # Test 2: Search for "jollof"
    print("\n2. Searching for 'jollof'...")
    request = factory.get('/api/user/vendors/autocomplete/', {'q': 'jollof', 'limit': 10})
    request.user = AnonymousUser()
    
    response = vendor_autocomplete(request)
    data = response.data
    
    print(f"   Results: {data.get('count')}")
    if data.get('results'):
        for vendor in data['results']:
            print(f"   - {vendor['business_name']} (Score: exact={vendor.get('exact_match', 0)})")
    
    # Test 3: Suggestions
    print("\n3. Getting suggestions for 'ma'...")
    request = factory.get('/api/user/vendors/suggestions/', {'q': 'ma', 'limit': 5})
    request.user = AnonymousUser()
    
    response = vendor_suggestions(request)
    data = response.data
    
    print(f"   Suggestions: {data.get('suggestions')}")
    
    # Test 4: Filter by location
    print("\n4. Searching with location filter 'Lagos'...")
    request = factory.get('/api/user/vendors/autocomplete/', {'q': 'jo', 'location': 'Lagos'})
    request.user = AnonymousUser()
    
    response = vendor_autocomplete(request)
    data = response.data
    
    print(f"   Results: {data.get('count')}")
    if data.get('results'):
        for vendor in data['results']:
            print(f"   - {vendor['business_name']} in {vendor['address']}")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70 + "\n")


if __name__ == '__main__':
    create_test_vendors()
    test_autocomplete_with_data()
