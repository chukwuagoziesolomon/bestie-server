import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.core_features.user.models import Banner

# Check if any banners exist
total_banners = Banner.objects.count()
active_banners = Banner.objects.filter(is_active=True, status='active').count()

print(f"\nBANNER DATABASE STATUS:")
print(f"   Total banners: {total_banners}")
print(f"   Active banners: {active_banners}")

if total_banners == 0:
    print(f"\nNO BANNERS FOUND")
    print(f"   You need to upload banners via:")
    print(f"   1. Django Admin: http://127.0.0.1:8000/admin/")
    print(f"   2. API POST: /api/user/banners/")
else:
    print(f"\nEXISTING BANNERS:")
    for banner in Banner.objects.all():
        print(f"\n   ID: {banner.id}")
        print(f"   Title: {banner.title}")
        print(f"   Type: {banner.banner_type}")
        print(f"   Status: {banner.status}")
        print(f"   Active: {banner.is_active}")
        print(f"   Has Image: {bool(banner.banner_image)}")
