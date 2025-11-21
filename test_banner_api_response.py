import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.test import RequestFactory
from bestyy.core_features.user.api.banner_views import BannerListView

# Simulate the API request
factory = RequestFactory()
request = factory.get('/api/user/banners/', {'limit': 5})

# Call the view
view = BannerListView.as_view()
response = view(request)

print("\n=== ACTUAL API RESPONSE ===\n")
print(json.dumps(response.data, indent=2))
print(f"\nStatus Code: {response.status_code}")
