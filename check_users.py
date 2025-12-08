#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.core_features.user.models import User

users = User.objects.all()
print("All users in the database:")
for u in users:
    print(f"ID: {u.id}, Email: {u.email}, Role: {u.role}")
    print(f"  Has vendor profile: {hasattr(u, 'vendor_profile')}")
    print(f"  Has courier profile: {hasattr(u, 'courier_profile')}")
    print(f"  Has user profile: {hasattr(u, 'profile')}")
    if hasattr(u, 'vendor_profile'):
        try:
            vp = u.vendor_profile
            print(f"  Vendor profile: {vp.business_name}, Status: {vp.verification_status}")
        except Exception as e:
            print(f"  Vendor profile error: {e}")
    print("---")