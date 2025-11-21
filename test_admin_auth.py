import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.contrib.auth import authenticate

print("\n=== TESTING AUTHENTICATION ===\n")

# Test agozie@gmail.com with password 12345678
email = 'agozie@gmail.com'
password = '12345678'

print(f"Attempting to authenticate:")
print(f"  Email: {email}")
print(f"  Password: {password}")
print()

user = authenticate(email=email, password=password)

if user:
    print(f"✅ SUCCESS: Authentication successful!")
    print(f"   User: {user.email}")
    print(f"   Superuser: {user.is_superuser}")
    print(f"   Staff: {user.is_staff}")
else:
    print(f"❌ FAILED: Authentication failed")
    print(f"   Possible reasons:")
    print(f"   1. Wrong password")
    print(f"   2. User is inactive")
    print(f"   3. Authentication backend issue")
    
    # Let's check if user exists and is active
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(email=email)
        print(f"\n   User exists in database:")
        print(f"   - Active: {user.is_active}")
        print(f"   - Has usable password: {user.has_usable_password()}")
        
        # Try to check password manually
        if user.check_password(password):
            print(f"   - Password check: ✅ CORRECT")
        else:
            print(f"   - Password check: ❌ WRONG PASSWORD")
            print(f"\n   🔑 SOLUTION: Reset the password or use correct password")
    except User.DoesNotExist:
        print(f"\n   User does not exist")
