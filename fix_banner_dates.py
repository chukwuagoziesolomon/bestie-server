import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.core_features.user.models import Banner

# Remove date restrictions from all banners
banners = Banner.objects.all()

print(f"\nRemoving date restrictions from {banners.count()} banners...\n")

for banner in banners:
    print(f"Banner: {banner.title}")
    print(f"  BEFORE: Start={banner.display_start_date}, End={banner.display_end_date}")
    
    banner.display_start_date = None
    banner.display_end_date = None
    banner.save()
    
    print(f"  AFTER: Start={banner.display_start_date}, End={banner.display_end_date}")
    print(f"  Status: WILL NOW SHOW IN API\n")

print("✅ All banners updated! They will now appear in the API immediately.")
