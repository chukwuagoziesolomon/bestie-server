"""
Automatic superuser creation script for Render deployment
Creates a superuser on first deployment using environment variables
"""
import os
import django
import sys

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.contrib.auth import get_user_model
from bestyy.core_features.user.models import VendorProfile

User = get_user_model()

def create_superuser():
    """Create superuser if it doesn't exist"""
    
    # Get credentials from environment variables
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@bestyy.com')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
    phone = os.environ.get('DJANGO_SUPERUSER_PHONE', '+2348000000000')
    
    print("="*80)
    print("SUPERUSER CREATION SCRIPT")
    print("="*80)
    
    # Check if superuser already exists
    if User.objects.filter(email=email).exists():
        print(f"✅ Superuser with email {email} already exists")
        superuser = User.objects.get(email=email)
        print(f"   Username: {superuser.email}")
        print(f"   Role: {superuser.role}")
        print(f"   Is Superuser: {superuser.is_superuser}")
        print(f"   Is Staff: {superuser.is_staff}")
        return superuser
    
    # Create superuser
    try:
        print(f"\n📝 Creating superuser with email: {email}")
        
        superuser = User.objects.create_superuser(
            email=email,
            password=password,
            phone=phone,
            first_name='Super',
            last_name='Admin',
            role='admin'  # Multi-role: admin role
        )
        
        print(f"✅ Superuser created successfully!")
        print(f"   Email: {superuser.email}")
        print(f"   Phone: {superuser.phone}")
        print(f"   Role: {superuser.role}")
        print(f"   Is Superuser: {superuser.is_superuser}")
        print(f"   Is Staff: {superuser.is_staff}")
        
        # Ensure all profiles are created (VendorProfile, CourierProfile, etc.)
        print(f"\n📋 Checking profiles...")
        if hasattr(superuser, 'vendor_profile'):
            print(f"   ✅ VendorProfile: {superuser.vendor_profile}")
        if hasattr(superuser, 'courier_profile'):
            print(f"   ✅ CourierProfile: {superuser.courier_profile}")
        
        print("\n" + "="*80)
        print("🎉 SUPERUSER SETUP COMPLETE")
        print("="*80)
        print(f"\nLogin Credentials:")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        print(f"\nAdmin Dashboard: https://your-app.onrender.com/admin/")
        print("="*80)
        
        return superuser
        
    except Exception as e:
        print(f"❌ Error creating superuser: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    create_superuser()
