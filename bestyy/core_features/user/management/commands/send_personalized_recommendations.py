"""
Management command to send personalized AI-powered restaurant recommendations to users.
Run this command twice per week to send tailored recommendations via email, WhatsApp, and webhooks.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from user.services.personalized_recommendation_service import PersonalizedRecommendationService


class Command(BaseCommand):
    help = 'Send personalized restaurant recommendations to users (run 2x per week)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending notifications',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Send recommendation preview for specific user ID only',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of users to send recommendations to (default: 50)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        user_id = options['user_id']
        limit = options['limit']

        if dry_run:
            self.stdout.write('DRY RUN MODE - No notifications will be sent')
            self.stdout.write('=' * 50)

        if user_id:
            # Preview for specific user
            self.stdout.write(f'Generating recommendation preview for user ID: {user_id}')
            preview = PersonalizedRecommendationService.get_recommendation_preview(user_id)

            if preview:
                self.stdout.write(f'User: {preview["user"]}')
                self.stdout.write(f'Would send: {preview["would_send"]}')
                self.stdout.write(f'Message: {preview["message"]}')
                self.stdout.write(f'Insights: {preview["insights"]}')

                if not preview["would_send"]:
                    self.stdout.write(
                        self.style.WARNING('User would not receive notification (missing contact info)')
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(f'User with ID {user_id} not found')
                )
            return

        # Send to multiple users
        self.stdout.write(f'Sending personalized recommendations to up to {limit} users...')
        self.stdout.write('Prioritizing inactive users to conserve OpenRouter credits.')

        if dry_run:
            # In dry run, show breakdown of user prioritization
            eligible_users = PersonalizedRecommendationService._get_eligible_users()

            # Analyze user activity levels
            seven_days_ago = timezone.now() - timedelta(days=7)
            three_days_ago = timezone.now() - timedelta(days=3)

            inactive_count = sum(1 for user in eligible_users
                                if user.orders.filter(created_at__lt=seven_days_ago).exists())
            moderate_count = sum(1 for user in eligible_users
                                if user.orders.filter(created_at__gte=seven_days_ago, created_at__lt=three_days_ago).exists())
            active_count = len(eligible_users) - inactive_count - moderate_count

            self.stdout.write(f'Would send to {min(len(eligible_users), limit)} users:')
            self.stdout.write(f'  - Inactive users (7+ days): {inactive_count}')
            self.stdout.write(f'  - Moderately active (3-7 days): {moderate_count}')
            self.stdout.write(f'  - Very active (< 3 days): {active_count}')
            return

        # Send actual recommendations (max 15 per day)
        sent_count = PersonalizedRecommendationService.send_daily_recommendations(limit=limit)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully sent personalized recommendations to {sent_count} users (max {limit} per day)'
            )
        )
        self.stdout.write('Fair cycling: each user gets one recommendation before anyone gets a second.')
        self.stdout.write('Focused on users who haven\'t ordered in over a week for maximum re-engagement impact.')

        if sent_count == 0:
            self.stdout.write(
                self.style.WARNING('No recommendations were sent. Check user eligibility and contact info.')
            )