"""
Service for automatically managing user favorites based on ordering behavior.
"""
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from user.models import Order, Favorite, MenuItem, VendorProfile


class AutoFavoriteService:
    """
    Service to automatically add food items and restaurants to favorites
    based on user ordering patterns.
    """
    
    def __init__(self, user):
        self.user = user
    
    def check_and_add_favorites(self, order):
        """
        Check if items/restaurants should be auto-favorited after an order.
        Called after order completion.
        """
        # Check for food item favorites
        self._check_food_item_favorites(order)
        
        # Check for restaurant favorites
        self._check_restaurant_favorites(order)
    
    def _check_food_item_favorites(self, order):
        """
        Check if food items should be auto-favorited based on order frequency.
        """
        # Get all items in this order
        for item in order.items.all():
            # Check if user has ordered this item multiple times in the last 30 days
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            # Count how many times this user has ordered this specific item
            order_count = Order.objects.filter(
                user=self.user,
                items=item,
                created_at__gte=thirty_days_ago,
                status__in=['completed', 'delivered']
            ).count()
            
            # Auto-favorite if ordered 3 or more times in 30 days
            if order_count >= 3:
                self._add_food_favorite(item)
    
    def _check_restaurant_favorites(self, order):
        """
        Check if restaurant should be auto-favorited based on order frequency.
        """
        # Check if user has ordered from this restaurant multiple times in the last 60 days
        sixty_days_ago = timezone.now() - timedelta(days=60)
        
        # Count how many times this user has ordered from this restaurant
        order_count = Order.objects.filter(
            user=self.user,
            vendor=order.vendor,
            created_at__gte=sixty_days_ago,
            status__in=['completed', 'delivered']
        ).count()
        
        # Auto-favorite if ordered 5 or more times in 60 days
        if order_count >= 5:
            self._add_restaurant_favorite(order.vendor)
    
    def _add_food_favorite(self, menu_item):
        """
        Add a food item to favorites if not already favorited.
        """
        # Check if already favorited
        if not Favorite.objects.filter(
            user=self.user,
            favorite_type='food',
            food_item=menu_item
        ).exists():
            Favorite.objects.create(
                user=self.user,
                favorite_type='food',
                food_item=menu_item
            )
            print(f"Auto-favorited food item: {menu_item.dish_name} for user {self.user.username}")
    
    def _add_restaurant_favorite(self, vendor):
        """
        Add a restaurant to favorites if not already favorited.
        """
        # Check if already favorited
        if not Favorite.objects.filter(
            user=self.user,
            favorite_type='venue',
            vendor=vendor
        ).exists():
            Favorite.objects.create(
                user=self.user,
                favorite_type='venue',
                vendor=vendor
            )
            print(f"Auto-favorited restaurant: {vendor.business_name} for user {self.user.username}")
    
    def _is_food_favorited(self, menu_item):
        """
        Check if a food item is already favorited by the user.
        """
        return Favorite.objects.filter(
            user=self.user,
            favorite_type='food',
            food_item=menu_item
        ).exists()
    
    def _is_restaurant_favorited(self, vendor):
        """
        Check if a restaurant is already favorited by the user.
        """
        return Favorite.objects.filter(
            user=self.user,
            favorite_type='venue',
            vendor=vendor
        ).exists()
    
    def get_frequently_ordered_items(self, days=30, min_orders=2):
        """
        Get items that user orders frequently (for potential auto-favoriting).
        """
        start_date = timezone.now() - timedelta(days=days)
        
        # Get items ordered multiple times in the specified period
        frequent_items = MenuItem.objects.filter(
            orders__user=self.user,
            orders__created_at__gte=start_date,
            orders__status__in=['completed', 'delivered']
        ).annotate(
            order_count=Count('orders')
        ).filter(
            order_count__gte=min_orders
        ).order_by('-order_count')
        
        return frequent_items
    
    def get_frequently_ordered_restaurants(self, days=60, min_orders=3):
        """
        Get restaurants that user orders from frequently (for potential auto-favoriting).
        """
        start_date = timezone.now() - timedelta(days=days)
        
        # Get restaurants ordered from multiple times in the specified period
        frequent_restaurants = VendorProfile.objects.filter(
            orders__user=self.user,
            orders__created_at__gte=start_date,
            orders__status__in=['completed', 'delivered']
        ).annotate(
            order_count=Count('orders')
        ).filter(
            order_count__gte=min_orders
        ).order_by('-order_count')
        
        return frequent_restaurants
    
    def bulk_check_and_add_favorites(self):
        """
        Bulk check and add favorites for all users based on their ordering history.
        This can be run as a periodic task.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        users_with_orders = User.objects.filter(orders__isnull=False).distinct()
        
        for user in users_with_orders:
            service = AutoFavoriteService(user)
            
            # Check food items
            frequent_items = service.get_frequently_ordered_items(days=30, min_orders=3)
            for item in frequent_items:
                service._add_food_favorite(item)
            
            # Check restaurants
            frequent_restaurants = service.get_frequently_ordered_restaurants(days=60, min_orders=5)
            for restaurant in frequent_restaurants:
                service._add_restaurant_favorite(restaurant)
