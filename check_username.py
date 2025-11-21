import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.contrib.auth import get_user_model, authenticate
from django.test import RequestFactory

User = get_user_model()

email = 'agozie@gmail.com'

try:
    user = User.objects.get(email=email)
    print(f"✅ User found: {email}")
    print(f"   Username: {user.username}")
    print(f"   Email: {user.email}")
    print(f"   Is superuser: {user.is_superuser}")
    print(f"   Is staff: {user.is_staff}")
    print(f"   Is active: {user.is_active}")
    
    # Test authentication with USERNAME (not email)
    factory = RequestFactory()
    request = factory.post('/login/')
    
    print(f"\n🔐 Testing authentication with USERNAME:")
    test_user = authenticate(request, username=user.username, password='12345678')
    if test_user:
        print(f"   ✅ SUCCESS with username '{user.username}'")
    else:
        print(f"   ❌ FAILED with username '{user.username}'")
    
    print(f"\n🔐 Testing authentication with EMAIL:")
    test_user2 = authenticate(request, username=email, password='12345678')
    if test_user2:
        print(f"   ✅ SUCCESS with email '{email}'")
    else:
        print(f"   ❌ FAILED with email '{email}'")
        
except User.DoesNotExist:
    print(f"❌ User {email} does not exist")
