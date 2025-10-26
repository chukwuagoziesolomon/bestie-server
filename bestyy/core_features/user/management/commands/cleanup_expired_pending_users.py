"""
Management command to clean up expired pending users
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from bestyy.core_features.user.models import PendingUser


class Command(BaseCommand):
    help = 'Clean up expired pending users from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Find expired pending users
        expired_users = PendingUser.objects.filter(expires_at__lt=timezone.now())

        count = expired_users.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would delete {count} expired pending users')
            )
        else:
            deleted_count, _ = expired_users.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {deleted_count} expired pending users')
            )