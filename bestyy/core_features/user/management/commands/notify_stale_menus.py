"""
Management command to notify vendors with stale menus.
Run this command periodically (e.g., daily) to check and notify vendors
whose menus haven't been updated in 2 days.
"""
from django.core.management.base import BaseCommand
from user.services.menu_update_notification_service import MenuUpdateNotificationService


class Command(BaseCommand):
    help = 'Notify vendors whose menus haven\'t been updated in 2 days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually sending notifications',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write('DRY RUN MODE - No notifications will be sent')
            self.stdout.write('=' * 50)

        # Get stale menu vendors
        stale_vendors = MenuUpdateNotificationService.get_stale_menu_vendors()

        if not stale_vendors:
            self.stdout.write(
                self.style.SUCCESS('No vendors with stale menus found.')
            )
            return

        self.stdout.write(f'Found {len(stale_vendors)} vendors with stale menus:')

        for vendor in stale_vendors:
            days_stale = MenuUpdateNotificationService._days_since_menu_update(vendor)
            self.stdout.write(
                f'  - {vendor.business_name} (ID: {vendor.id}): '
                f'{days_stale} days since last menu update'
            )

        if dry_run:
            self.stdout.write(f'\nWould notify {len(stale_vendors)} vendors.')
            return

        # Send notifications
        self.stdout.write('\nSending notifications...')
        notified_count = MenuUpdateNotificationService.check_and_notify_stale_menus()

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully notified {notified_count} vendors about menu updates.'
            )
        )