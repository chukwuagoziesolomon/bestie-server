import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.core_features.user.models import Banner
from django.core.files import File
from django.core.files.storage import default_storage
import cloudinary
import cloudinary.uploader
from django.conf import settings

# Configure cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY['cloud_name'],
    api_key=settings.CLOUDINARY['api_key'],
    api_secret=settings.CLOUDINARY['api_secret']
)

print("\n=== MIGRATING EXISTING BANNERS TO CLOUDINARY ===\n")

banners = Banner.objects.all()
for banner in banners:
    if banner.banner_image:
        image_path = banner.banner_image.path if hasattr(banner.banner_image, 'path') else None
        
        if image_path and os.path.exists(image_path):
            print(f"Migrating Banner #{banner.id}: {banner.title}")
            print(f"  Current: {banner.banner_image.url}")
            
            try:
                # Upload to Cloudinary
                result = cloudinary.uploader.upload(
                    image_path,
                    folder="banners",
                    resource_type="image"
                )
                
                cloudinary_url = result['secure_url']
                print(f"  ✅ Uploaded to Cloudinary: {cloudinary_url}")
                
                # Update banner with cloudinary URL
                # We need to save the cloudinary public_id for future reference
                banner.banner_image = cloudinary_url.split('/')[-1]
                banner.save()
                
                print(f"  ✅ Banner updated\n")
                
            except Exception as e:
                print(f"  ❌ Error: {e}\n")
        else:
            print(f"Banner #{banner.id}: No local file found\n")

print("=== MIGRATION COMPLETE ===")
print("\nNow test with: python test_cloudinary_upload.py")
