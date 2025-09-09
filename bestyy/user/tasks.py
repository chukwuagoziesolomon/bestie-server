"""
Celery tasks for user-related operations.
"""
from celery import shared_task
from django.contrib.auth import get_user_model
from user.services.auto_favorite_service import AutoFavoriteService

User = get_user_model()


@shared_task
def auto_favorite_periodic_task():
    """
    Periodic task to automatically add favorites for all users based on their ordering history.
    This task can be scheduled to run daily/weekly to catch any missed favorites.
    """
    try:
        # Get all users with orders
        users_with_orders = User.objects.filter(orders__isnull=False).distinct()
        
        total_favorites_added = 0
        
        for user in users_with_orders:
            try:
                service = AutoFavoriteService(user)
                
                # Check food items
                frequent_items = service.get_frequently_ordered_items(days=30, min_orders=3)
                for item in frequent_items:
                    if not service._is_food_favorited(item):
                        service._add_food_favorite(item)
                        total_favorites_added += 1
                
                # Check restaurants
                frequent_restaurants = service.get_frequently_ordered_restaurants(days=60, min_orders=5)
                for restaurant in frequent_restaurants:
                    if not service._is_restaurant_favorited(restaurant):
                        service._add_restaurant_favorite(restaurant)
                        total_favorites_added += 1
                        
            except Exception as e:
                print(f"Error processing user {user.id}: {e}")
                continue
        
        return f"Auto-favorite task completed. Added {total_favorites_added} new favorites."
        
    except Exception as e:
        return f"Auto-favorite task failed: {str(e)}"


@shared_task
def auto_favorite_user_task(user_id):
    """
    Task to process auto-favorites for a specific user.
    """
    try:
        user = User.objects.get(id=user_id)
        service = AutoFavoriteService(user)
        
        favorites_added = 0
        
        # Check food items
        frequent_items = service.get_frequently_ordered_items(days=30, min_orders=3)
        for item in frequent_items:
            if not service._is_food_favorited(item):
                service._add_food_favorite(item)
                favorites_added += 1
        
        # Check restaurants
        frequent_restaurants = service.get_frequently_ordered_restaurants(days=60, min_orders=5)
        for restaurant in frequent_restaurants:
            if not service._is_restaurant_favorited(restaurant):
                service._add_restaurant_favorite(restaurant)
                favorites_added += 1
        
        return f"Added {favorites_added} favorites for user {user.username}"
        
    except User.DoesNotExist:
        return f"User with ID {user_id} not found"
    except Exception as e:
        return f"Error processing user {user_id}: {str(e)}"




