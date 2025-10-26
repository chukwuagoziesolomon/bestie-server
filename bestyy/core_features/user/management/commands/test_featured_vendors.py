from django.core.management.base import BaseCommand
from user.models import VendorProfile, SubscriptionPlan


class Command(BaseCommand):
    help = 'Test featured vendor functionality'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Testing Featured Vendor Functionality')
        )
        self.stdout.write('=' * 50)

        # Test subscription plans
        try:
            free_plan = SubscriptionPlan.objects.get(plan_type='free')
            pro_plan = SubscriptionPlan.objects.get(plan_type='pro')
            self.stdout.write(
                self.style.SUCCESS(f'[OK] Free plan: {free_plan.name} - {free_plan.price} {free_plan.currency}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'[OK] Pro plan: {pro_plan.name} - {pro_plan.price} {pro_plan.currency}')
            )
        except SubscriptionPlan.DoesNotExist as e:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Error getting plans: {e}')
            )
            return

        # Get vendor stats
        total_vendors = VendorProfile.objects.count()
        pro_vendors = VendorProfile.objects.filter(subscription_plan__plan_type='pro').count()
        free_vendors = VendorProfile.objects.filter(subscription_plan__plan_type='free').count()

        self.stdout.write(f'\nVendor Statistics:')
        self.stdout.write(f'  Total vendors: {total_vendors}')
        self.stdout.write(f'  Pro (featured) vendors: {pro_vendors}')
        self.stdout.write(f'  Free vendors: {free_vendors}')

        # Test featured vendor fields
        featured_vendors = VendorProfile.objects.filter(is_featured=True)
        self.stdout.write(f'  Vendors with is_featured=True: {featured_vendors.count()}')

        if featured_vendors.exists():
            vendor = featured_vendors.first()
            self.stdout.write(f'  Sample featured vendor: {vendor.business_name}')
            self.stdout.write(f'    Featured priority: {vendor.featured_priority}')
            self.stdout.write(f'    Featured expiry: {vendor.featured_expiry}')

        # Test basic queryset filtering
        try:
            # Test filtering by subscription plan
            pro_queryset = VendorProfile.objects.filter(subscription_plan__plan_type='pro')
            self.stdout.write(f'  ✓ Can filter vendors by pro subscription: {pro_queryset.count()} results')

            # Test filtering by is_featured
            featured_queryset = VendorProfile.objects.filter(is_featured=True)
            self.stdout.write(f'  ✓ Can filter vendors by is_featured: {featured_queryset.count()} results')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Error testing queryset filtering: {e}')
            )

        self.stdout.write(
            self.style.SUCCESS('\n[SUCCESS] Basic featured vendor functionality test completed!')
        )
        self.stdout.write(
            self.style.WARNING('Note: Full recommendation testing requires VendorPopularity model to be restored')
        )