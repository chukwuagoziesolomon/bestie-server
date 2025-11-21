import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Reset password for agozie@gmail.com
email = 'agozie@gmail.com'
new_password = '12345678'

try:
    user = User.objects.get(email=email)
    user.set_password(new_password)
    user.save()
    
    print(f"✅ SUCCESS: Password reset for {email}")
    print(f"   New password: {new_password}")
    print(f"\nYou can now login with:")
    print(f"   Email: {email}")
    print(f"   Password: {new_password}")
    
    # Verify it works
    from django.contrib.auth import authenticate
    from django.test import RequestFactory
    
    factory = RequestFactory()
    request = factory.post('/login/')
    test_user = authenticate(request, email=email, password=new_password)
    if test_user:
        print(f"\n✅ VERIFIED: Authentication works with new password")
    else:
        print(f"\n❌ ERROR: Authentication still failing")
        
except User.DoesNotExist:
    print(f"❌ ERROR: User {email} does not exist")
