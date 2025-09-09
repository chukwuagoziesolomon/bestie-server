from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from user.models import VendorProfile, VendorAnalytics, Order


class Command(BaseCommand):
    help = 'Populate VendorAnalytics data from existing orders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days back to populate analytics for (default: 30)'
        )
        parser.add_argument(
            '--vendor-id',
            type=int,
            help='Specific vendor ID to populate analytics for (optional)'
        )

    def handle(self, *args, **options):
        days_back = options['days']
        vendor_id = options.get('vendor_id')
        
        # Calculate date range
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        self.stdout.write(f'Populating analytics from {start_date} to {end_date}')
        
        # Get vendors to process
        if vendor_id:
            vendors = VendorProfile.objects.filter(id=vendor_id)
            if not vendors.exists():
                self.stdout.write(self.style.ERROR(f'Vendor with ID {vendor_id} not found'))
                return
        else:
            vendors = VendorProfile.objects.all()
        
        total_analytics_created = 0
        
        for vendor in vendors:
            self.stdout.write(f'Processing vendor: {vendor.business_name}')
            
            # Get all dates that have orders for this vendor
            order_dates = Order.objects.filter(
                vendor=vendor,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            ).values_list('created_at__date', flat=True).distinct()
            
            for order_date in order_dates:
                analytics = VendorAnalytics.update_analytics_for_date(vendor, order_date)
                total_analytics_created += 1
                
                self.stdout.write(
                    f'  {order_date}: {analytics.total_orders} orders, '
                    f'${analytics.total_revenue} revenue'
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created/updated {total_analytics_created} analytics records'
            )
        )
