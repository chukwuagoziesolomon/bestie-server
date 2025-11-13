from django.core.management.base import BaseCommand
from bestyy.core_features.user.models import SystemSettings


class Command(BaseCommand):
    help = 'Set up default system settings'

    def handle(self, *args, **options):
        """Create default system settings required by the application."""

        # Default settings for pricing and fees
        default_settings = [
            {
                'key': 'service_fee_percentage',
                'value': '5.00',  # 5% platform commission
                'description': 'Platform service fee percentage (0.00-100.00)',
                'data_type': 'decimal'
            },
            {
                'key': 'base_delivery_fee',
                'value': '1500.00',  # ₦1,500 base delivery fee
                'description': 'Base delivery fee in Naira',
                'data_type': 'decimal'
            },
            {
                'key': 'delivery_rate_per_km',
                'value': '300.00',  # ₦300 per km
                'description': 'Additional delivery fee per kilometer',
                'data_type': 'decimal'
            },
            {
                'key': 'delivery_max_distance_for_base',
                'value': '5.0',  # 5km
                'description': 'Maximum distance for base delivery fee only',
                'data_type': 'decimal'
            },
            {
                'key': 'platform_commission_rate',
                'value': '0.05',  # 5% commission
                'description': 'Platform commission rate as decimal (0.05 = 5%)',
                'data_type': 'decimal'
            },
            {
                'key': 'default_vendor_fixed_amount',
                'value': '0.00',
                'description': 'Default fixed payout amount for vendors',
                'data_type': 'decimal'
            },
            {
                'key': 'default_courier_fixed_amount',
                'value': '500.00',  # ₦500 fixed for couriers
                'description': 'Default fixed payout amount for couriers',
                'data_type': 'decimal'
            },
            {
                'key': 'max_delivery_distance_km',
                'value': '50.0',
                'description': 'Maximum delivery distance in kilometers',
                'data_type': 'decimal'
            }
        ]

        created_count = 0
        updated_count = 0

        for setting_data in default_settings:
            setting, created = SystemSettings.objects.get_or_create(
                key=setting_data['key'],
                defaults={
                    'value': setting_data['value'],
                    'description': setting_data['description'],
                    'data_type': setting_data['data_type'],
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created setting: {setting.key} = {setting.value}')
                )
            else:
                # Update if description or data_type changed
                updated = False
                if setting.description != setting_data['description']:
                    setting.description = setting_data['description']
                    updated = True
                if setting.data_type != setting_data['data_type']:
                    setting.data_type = setting_data['data_type']
                    updated = True

                if updated:
                    setting.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Updated setting: {setting.key}')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'System settings setup complete. Created: {created_count}, Updated: {updated_count}'
            )
        )