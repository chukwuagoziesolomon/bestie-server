from django.core.management.base import BaseCommand
from user.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Set up default subscription plans for vendor featured status'

    def handle(self, *args, **options):
        # Default subscription plans
        plans_data = [
            {
                'plan_type': 'free',
                'name': 'Free Plan',
                'price': 0.00,
                'description': 'Basic plan with standard recommendations',
                'features': ['Basic listing', 'Standard recommendations'],
                'is_active': True
            },
            {
                'plan_type': 'pro',
                'name': 'Pro Plan (Featured)',
                'price': 5000.00,
                'description': 'Premium plan with featured status - appear first in recommendations',
                'features': ['Featured listing', 'Priority in recommendations', 'Higher visibility', 'Analytics dashboard'],
                'is_active': True
            }
        ]

        created_count = 0
        updated_count = 0

        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.get_or_create(
                plan_type=plan_data['plan_type'],
                defaults=plan_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created plan: {plan.name} - NGN{plan.price}')
                )
            else:
                # Update existing plan with new data
                for key, value in plan_data.items():
                    setattr(plan, key, value)
                plan.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated plan: {plan.name} - NGN{plan.price}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Subscription plans setup complete. Created: {created_count}, Updated: {updated_count}'
            )
        )