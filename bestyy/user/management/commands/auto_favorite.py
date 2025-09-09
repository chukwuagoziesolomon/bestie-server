"""
Django management command to automatically add favorites based on user ordering behavior.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from user.services.auto_favorite_service import AutoFavoriteService

User = get_user_model()


class Command(BaseCommand):
    help = 'Automatically add food items and restaurants to favorites based on user ordering patterns'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Run for specific user ID only',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be favorited without actually adding favorites',
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        dry_run = options.get('dry_run')

        if user_id:
            try:
                user = User.objects.get(id=user_id)
                self.stdout.write(f"Processing user: {user.username} (ID: {user.id})")
                self._process_user(user, dry_run)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User with ID {user_id} not found"))
        else:
            # Process all users with orders
            users_with_orders = User.objects.filter(orders__isnull=False).distinct()
            self.stdout.write(f"Processing {users_with_orders.count()} users with orders...")
            
            for user in users_with_orders:
                self.stdout.write(f"Processing user: {user.username} (ID: {user.id})")
                self._process_user(user, dry_run)

        self.stdout.write(self.style.SUCCESS("Auto-favorite processing completed!"))

    def _process_user(self, user, dry_run):
        """Process auto-favoriting for a specific user."""
        service = AutoFavoriteService(user)
        
        # Check food items
        frequent_items = service.get_frequently_ordered_items(days=30, min_orders=3)
        if frequent_items.exists():
            self.stdout.write(f"  Found {frequent_items.count()} frequently ordered food items:")
            for item in frequent_items:
                if not dry_run:
                    service._add_food_favorite(item)
                    self.stdout.write(f"    ✓ Auto-favorited: {item.dish_name}")
                else:
                    self.stdout.write(f"    Would auto-favorite: {item.dish_name}")
        else:
            self.stdout.write("  No frequently ordered food items found")

        # Check restaurants
        frequent_restaurants = service.get_frequently_ordered_restaurants(days=60, min_orders=5)
        if frequent_restaurants.exists():
            self.stdout.write(f"  Found {frequent_restaurants.count()} frequently ordered restaurants:")
            for restaurant in frequent_restaurants:
                if not dry_run:
                    service._add_restaurant_favorite(restaurant)
                    self.stdout.write(f"    ✓ Auto-favorited: {restaurant.business_name}")
                else:
                    self.stdout.write(f"    Would auto-favorite: {restaurant.business_name}")
        else:
            self.stdout.write("  No frequently ordered restaurants found")




