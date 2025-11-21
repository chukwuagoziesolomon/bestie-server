"""
Test script for multi-role authentication:
1. Register user with multiple roles (same email/phone)
2. Login and receive all profiles
3. Select specific profile
"""
import os
import sys
import django

# Add project to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from bestyy.core_features.user.models import VendorProfile, CourierProfile
from django.conf import settings
import json

User = get_user_model()

def test_multi_role_registration_and_login():
    """Test multi-role registration and login flow"""
    
    # Add testserver to ALLOWED_HOSTS for testing
    original_allowed_hosts = settings.ALLOWED_HOSTS
    if 'testserver' not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']
    
    print("="*70)
    print("TESTING MULTI-ROLE AUTHENTICATION SYSTEM")
    print("="*70)
    
    client = Client()
    test_email = "testmultirole@example.com"
    test_password = "SecurePass123!"
    test_phone = "+2348012345678"
    
    # Clean up any existing test data
    User.objects.filter(email=test_email).delete()
    
    print("\n📝 Step 1: Register as USER")
    print("-" * 70)
    
    user_data = {
        'email': test_email,
        'password': test_password,
        'confirm_password': test_password,
        'first_name': 'John',
        'last_name': 'Doe',
        'phone': test_phone,
        'roles': ['user']
    }
    
    response = client.post(
        '/api/user/register/multi-role/',
        data=json.dumps(user_data),
        content_type='application/json'
    )
    
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.content.decode()[:500]}")
    
    if response.status_code == 201:
        print("✅ User registration successful!")
    else:
        print("❌ User registration failed!")
        settings.ALLOWED_HOSTS = original_allowed_hosts
        return
    
    print("\n📝 Step 2: Register as VENDOR (same email/phone/password)")
    print("-" * 70)
    
    vendor_data = {
        'email': test_email,
        'password': test_password,
        'confirm_password': test_password,
        'first_name': 'John',
        'last_name': 'Doe',
        'phone': test_phone,
        'roles': ['vendor'],
        'business_name': 'John\'s Restaurant',
        'business_category': 'Nigerian',
        'business_address': '123 Lagos Street, Lagos',
        'opening_hours': '09:00:00',
        'closing_hours': '22:00:00'
    }
    
    response = client.post(
        '/api/user/register/multi-role/',
        data=json.dumps(vendor_data),
        content_type='application/json'
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201:
        print("✅ Vendor registration pending verification!")
        print("⚠️ Note: Vendor requires WhatsApp verification")
    else:
        print("❌ Vendor registration failed!")
    
    print("\n📝 Step 3: Register as COURIER (same email/phone/password)")
    print("-" * 70)
    
    courier_data = {
        'email': test_email,
        'password': test_password,
        'confirm_password': test_password,
        'first_name': 'John',
        'last_name': 'Doe',
        'phone': test_phone,
        'roles': ['courier'],
        'vehicle_type': 'motorcycle',
        'license_number': 'ABC123456',
        'vehicle_registration': 'REG789'
    }
    
    response = client.post(
        '/api/user/register/multi-role/',
        data=json.dumps(courier_data),
        content_type='application/json'
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201:
        print("✅ Courier registration pending verification!")
        print("⚠️ Note: Courier requires WhatsApp verification")
    else:
        print("❌ Courier registration failed!")
    
    print("\n📝 Step 4: Login with email/password")
    print("-" * 70)
    
    login_data = {
        'email': test_email,
        'password': test_password
    }
    
    response = client.post(
        '/api/user/login/',
        data=json.dumps(login_data),
        content_type='application/json'
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        response_data = response.json()
        
        if response_data.get('multiple_profiles'):
            print(f"✅ Login successful! Found {len(response_data['profiles'])} profiles")
            print(f"Profiles: {[p['role'] for p in response_data['profiles']]}")
            
            print("\n📝 Step 5: Select USER profile")
            print("-" * 70)
            
            user_profile = next((p for p in response_data['profiles'] if p['role'] == 'user'), None)
            if user_profile:
                select_data = {
                    'email': test_email,
                    'password': test_password,
                    'profile_id': user_profile['id']
                }
                
                response = client.post(
                    '/api/user/login/select-profile/',
                    data=json.dumps(select_data),
                    content_type='application/json'
                )
                
                print(f"Status Code: {response.status_code}")
                print(f"Response: {json.dumps(response.json(), indent=2)}")
                
                if response.status_code == 200:
                    print("✅ Profile selected successfully!")
                    print(f"Access Token: {response.json()['access'][:50]}...")
                else:
                    print("❌ Profile selection failed!")
        else:
            print("✅ Login successful! Single profile")
            print(f"Role: {response_data['user']['role']}")
            print(f"Access Token: {response_data['access'][:50]}...")
    else:
        print("❌ Login failed!")
    
    print("\n📊 Step 6: Check Database State")
    print("-" * 70)
    
    users = User.objects.filter(email=test_email)
    print(f"Total user accounts with email '{test_email}': {users.count()}")
    
    for user in users:
        print(f"\n  User ID: {user.id}")
        print(f"  Role: {user.role}")
        print(f"  Name: {user.first_name} {user.last_name}")
        print(f"  Phone: {user.phone}")
        print(f"  Active: {user.is_active}")
        
        if user.role == 'vendor' and hasattr(user, 'vendor_profile'):
            print(f"  Vendor Business: {user.vendor_profile.business_name}")
            print(f"  Vendor Verified: {user.vendor_profile.is_verified}")
        
        if user.role == 'courier' and hasattr(user, 'courier_profile'):
            print(f"  Courier Vehicle: {user.courier_profile.vehicle_type}")
            print(f"  Courier Verified: {user.courier_profile.is_verified}")
    
    print("\n" + "="*70)
    print("TEST COMPLETED")
    print("="*70)
    
    # Cleanup
    print("\n🧹 Cleaning up test data...")
    User.objects.filter(email=test_email).delete()
    print("✅ Cleanup complete!")
    
    # Restore ALLOWED_HOSTS
    settings.ALLOWED_HOSTS = original_allowed_hosts

if __name__ == '__main__':
    test_multi_role_registration_and_login()
