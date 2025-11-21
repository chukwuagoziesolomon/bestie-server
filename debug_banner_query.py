import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.core_features.user.models import Banner
from django.utils import timezone
from django.db.models import Q

# Check all banners with their date fields
print("\n=== BANNER DATE ANALYSIS ===\n")

for banner in Banner.objects.all():
    print(f"Banner ID: {banner.id}")
    print(f"  Title: {banner.title}")
    print(f"  Type: {banner.banner_type}")
    print(f"  Status: {banner.status}")
    print(f"  Is Active: {banner.is_active}")
    print(f"  Start Date: {banner.display_start_date}")
    print(f"  End Date: {banner.display_end_date}")
    print(f"  Currently Active: {banner.is_currently_active()}")
    print()

# Test the query that the API uses
print("\n=== TESTING API QUERY ===\n")
now = timezone.now()
print(f"Current time: {now}")

queryset = Banner.objects.filter(
    is_active=True,
    status='active'
).filter(
    Q(display_start_date__isnull=True) | Q(display_start_date__lte=now)
).filter(
    Q(display_end_date__isnull=True) | Q(display_end_date__gte=now)
)

print(f"\nBanners matching API query: {queryset.count()}")
for banner in queryset:
    print(f"  - {banner.title} (ID: {banner.id})")
