from django.core.management.base import BaseCommand
from bestyy.core_features.user.services.menu_reminder_service import MenuReminderService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send WhatsApp menu update reminders to vendors who have not updated their menu in >24h.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which vendors would be reminded without actually sending messages',
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write('DRY RUN: Checking vendors needing menu update reminders...')
            vendors = MenuReminderService.get_vendors_needing_reminder()
            self.stdout.write(f'Found {vendors.count()} vendors needing reminders:')
            for vendor in vendors:
                if vendor.last_menu_update is None:
                    self.stdout.write(f'  - {vendor.business_name} (NEVER set menu items)')
                else:
                    self.stdout.write(f'  - {vendor.business_name} (last update: {vendor.last_menu_update})')
        else:
            self.stdout.write('Sending WhatsApp menu update reminders...')
            MenuReminderService.send_reminders()
            self.stdout.write(self.style.SUCCESS('Completed WhatsApp menu update reminders job.'))
            logger.info('Menu update reminders job completed successfully')
