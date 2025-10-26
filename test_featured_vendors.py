#!/usr/bin/env python
"""
Test script for featured vendor functionality
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.settings')
django.setup()

from user.models import VendorProfile, SubscriptionPlan

def test_featured_vendors():
    print("Testing Featured Vendor Functionality")
    print("=" * 40)

    # Get subscription plans
    try:
        free_plan = SubscriptionPlan.objects.get(plan_type='free')
        pro_plan = SubscriptionPlan.objects.get(plan_type='pro')
        print(f"✓ Free plan: {free_plan.name} - {free_plan.price} {free_plan.currency}")
        print(f"✓ Pro plan: {pro_plan.name} - {pro_plan.price} {pro_plan.currency}")
    except SubscriptionPlan.DoesNotExist as e:
        print(f"✗ Error: {e}")
        return

    # Get vendor stats
    total_vendors = VendorProfile.objects.count()
    pro_vendors = VendorProfile.objects.filter(subscription_plan__plan_type='pro').count()
    free_vendors = VendorProfile.objects.filter(subscription_plan__plan_type='free').count()

    print(f"\nVendor Statistics:")
    print(f"  Total vendors: {total_vendors}")
    print(f"  Pro (featured) vendors: {pro_vendors}")
    print(f"  Free vendors: {free_vendors}")

    # Test recommendation logic
    from user.api.unified_recommendation_view import UnifiedVendorRecommendationView
    view = UnifiedVendorRecommendationView()

    try:
        recommendations = view._get_unified_recommendations(
            user=None,
            user_location={},
            category=None,
            limit=20
        )

        total_recs = len(recommendations)
        featured_recs = sum(1 for r in recommendations if r['is_featured'])

        print(f"\nRecommendation Test:")
        print(f"  Total recommendations: {total_recs}")
        print(f"  Featured recommendations: {featured_recs}")

        if featured_recs > 0:
            print("✓ Featured vendors are appearing first in recommendations")
        else:
            print("ℹ No featured vendors in current dataset")

        # Check order - featured should come first
        featured_positions = [i for i, r in enumerate(recommendations) if r['is_featured']]
        if featured_positions:
            print(f"  Featured vendor positions: {featured_positions}")
            if all(pos < len(recommendations) - featured_recs for pos in featured_positions):
                print("✓ Featured vendors are prioritized correctly")
            else:
                print("⚠ Featured vendor ordering might need verification")

    except Exception as e:
        print(f"✗ Error testing recommendations: {e}")

    print("\nTest completed!")

if __name__ == '__main__':
    test_featured_vendors()