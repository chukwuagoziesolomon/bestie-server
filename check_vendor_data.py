#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.core_features.user.models import User

user = User.objects.get(id=3)
print("USER INFO:")
print(f"Name: {user.first_name} {user.last_name}")
print(f"Email: {user.email}")
print(f"Phone: {user.phone}")
print(f"Role: {user.role}")

print("\nVENDOR PROFILE:")
vp = user.vendor_profile
print(f"Business Name: '{vp.business_name}'")
print(f"Business Category: '{vp.business_category}'")
print(f"Phone: {vp.phone}")
print(f"Address: '{vp.business_address}'")
print(f"CAC Number: {vp.cac_number}")
print(f"Description: '{vp.business_description}'")