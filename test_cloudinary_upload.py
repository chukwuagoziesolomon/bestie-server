import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.core_features.user.models import Banner
from django.core.files.storage import default_storage
from django.conf import settings

print("\n=== TESTING FILE STORAGE ===")
print(f"Storage backend: {settings.DEFAULT_FILE_STORAGE}")
print(f"Storage class: {default_storage.__class__}")

# Check existing banners
print("\n=== EXISTING BANNERS ===")
banners = Banner.objects.all()
for banner in banners:
    print(f"\nBanner ID {banner.id}: {banner.title}")
    print(f"  Image field: {banner.banner_image}")
    print(f"  Image URL: {banner.banner_image.url if banner.banner_image else 'None'}")
    print(f"  Storage: {banner.banner_image.storage.__class__ if banner.banner_image else 'None'}")
    
    # Check if URL contains cloudinary
    if banner.banner_image:
        url = banner.banner_image.url
        if 'cloudinary.com' in url:
            print(f"  ✅ Using Cloudinary")
        else:
            print(f"  ❌ NOT using Cloudinary (local file)")

print("\n=== DIAGNOSIS ===")
if 'cloudinary_storage' in settings.DEFAULT_FILE_STORAGE:
    print("✅ Cloudinary storage is configured in settings")
    print(f"Cloud name: {settings.CLOUDINARY.get('cloud_name')}")
    
    # Check if the field storage is actually using cloudinary
    test_banner = Banner.objects.first()
    if test_banner and test_banner.banner_image:
        storage_class = test_banner.banner_image.storage.__class__.__name__
        print(f"Actual storage being used: {storage_class}")
        
        if 'Cloudinary' in storage_class:
            print("✅ Field is using Cloudinary storage")
        else:
            print("❌ Field is NOT using Cloudinary storage despite settings")
            print("This means images were uploaded before Cloudinary was configured")
else:
    print("❌ Cloudinary storage is NOT configured")
