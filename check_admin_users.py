import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Check both email addresses
emails = ['agozie@gmail.com', 'Admin1@gmail.com']

print("\n=== CHECKING LOGIN CREDENTIALS ===\n")

for email in emails:
    try:
        user = User.objects.get(email=email)
        print(f"Email: {email}")
        print(f"  EXISTS: YES")
        print(f"  Staff: {user.is_staff}")
        print(f"  Superuser: {user.is_superuser}")
        print(f"  Active: {user.is_active}")
        
        if not user.is_superuser:
            print(f"  ❌ PROBLEM: User is NOT a superuser (required for /api/user/admin/login/)")
        else:
            print(f"  ✅ OK: User is a superuser")
        print()
    except User.DoesNotExist:
        print(f"Email: {email}")
        print(f"  EXISTS: NO")
        print(f"  ❌ PROBLEM: User does not exist in database")
        print()

# Show all superusers
print("\n=== ALL SUPERUSERS IN DATABASE ===\n")
superusers = User.objects.filter(is_superuser=True)
print(f"Total superusers: {superusers.count()}\n")
for su in superusers:
    print(f"  - {su.email}")
    print(f"    Staff: {su.is_staff}, Active: {su.is_active}")
