"""
Service for generating and sending personalized AI-powered restaurant recommendations to users.
This service analyzes user behavior, preferences, and order history to create
personalized recommendation messages sent via email, WhatsApp, and webhooks.
"""
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Count, Avg, Q, F
from bestyy.core_features.user.models import (
    User, VendorProfile, Favorite, UserRecommendationHistory
)
from bestyy.restaurant_features.order.models import Order
from bestyy.restaurant_features.product.models import Product as MenuItem
# Removed direct import - now using HTTP API calls for production-grade decoupling
import random
import logging

logger = logging.getLogger(__name__)


class PersonalizedRecommendationService:
    """
    Service to generate and send personalized restaurant recommendations to users.
    Analyzes user behavior patterns and sends tailored messages 2x per week.
    """

    RECOMMENDATION_TEMPLATES = {
        'morning': [
            "Good morning {name}! 🌅 Ready for breakfast? Based on what you've enjoyed before, I think you'd love {restaurant} - they have amazing {cuisine} options!",
            "Hey {name}! ☕ Starting your day right? I've found {restaurant} with fresh {cuisine} dishes that match your taste perfectly.",
            "Morning {name}! 🌞 Based on your preferences, {restaurant} has some {cuisine} specials that would be perfect for your breakfast.",
        ],
        'lunch': [
            "Hi {name}! 🍽️ Lunch time! I noticed you enjoy {cuisine} - {restaurant} has incredible lunch specials right now.",
            "Hey {name}! 🕐 It's lunchtime! Based on your order history, {restaurant} would be perfect for your midday meal.",
            "{name}, lunch calling! 🍕 I think you'd really enjoy {restaurant}'s {cuisine} selection - they have great reviews!",
        ],
        'dinner': [
            "Good evening {name}! 🌙 Dinner time! {restaurant} has amazing {cuisine} dishes that I think you'd love.",
            "Hi {name}! 🌆 Ready for dinner? Based on what you've ordered before, {restaurant} would be perfect tonight.",
            "Evening {name}! 🍽️ {restaurant} has some incredible {cuisine} options that match your preferences exactly.",
        ],
        'general': [
            "Hey {name}! 👋 I have a feeling you'd love {restaurant} - they specialize in {cuisine} and have great reviews!",
            "Hi {name}! 🌟 Based on your taste preferences, {restaurant} would be a great choice for your next meal.",
            "{name}, I think you'd really enjoy {restaurant}'s {cuisine} dishes - they have excellent ratings!",
            "Hello {name}! 🍴 I've found {restaurant} with amazing {cuisine} options that match what you usually order.",
        ],
        'craving': [
            "Hey {name}! 🍕 What are you craving today? I think {restaurant} has exactly what you're looking for!",
            "{name}, feeling hungry? 🍽️ {restaurant} has some {cuisine} dishes that I know you'd love.",
            "Hi {name}! 🥘 Based on your preferences, {restaurant} would satisfy any craving you might have!",
        ]
    }

    @staticmethod
    def send_daily_recommendations(limit=15):
        """
        Send personalized recommendations to up to 15 users per day.
        Cycles through all eligible users before repeating anyone.
        Focuses on users who haven't ordered in over a week.
        """

        # Get users who haven't received recommendations recently (fair cycling)
        eligible_users = UserRecommendationHistory.get_next_eligible_users(limit=limit)

        # Further filter to users who haven't ordered in over a week
        week_ago = timezone.now() - timedelta(days=7)
        inactive_users = []

        for user in eligible_users:
            # Check if user's last order was over a week ago
            last_order = user.orders.order_by('-created_at').first()
            if last_order and last_order.created_at < week_ago:
                inactive_users.append(user)

        # If we don't have enough inactive users, include some who haven't ordered in 3-7 days
        if len(inactive_users) < limit:
            three_days_ago = timezone.now() - timedelta(days=3)
            for user in eligible_users:
                if user not in inactive_users:
                    last_order = user.orders.order_by('-created_at').first()
                    if last_order and three_days_ago <= last_order.created_at < week_ago:
                        inactive_users.append(user)
                        if len(inactive_users) >= limit:
                            break

        sent_count = 0
        for user in inactive_users[:limit]:
            try:
                PersonalizedRecommendationService._send_personalized_recommendation(user)
                # Mark as sent in history
                history = UserRecommendationHistory.create_or_get(user)
                history.mark_sent()
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send recommendation to user {user.id}: {str(e)}")
                continue

        return sent_count

    @staticmethod
    def _get_eligible_users():
        """
        Get users who are eligible for personalized recommendations.
        Prioritizes users who haven't ordered recently to conserve API credits.
        """
        # Users who:
        # - Are active
        # - Have placed at least one order
        # - Haven't received a recommendation in the last 3 days
        # - Have email or phone for notifications
        # - Prioritize users who haven't ordered in 7+ days (to re-engage inactive users)

        three_days_ago = timezone.now() - timedelta(days=3)
        seven_days_ago = timezone.now() - timedelta(days=7)

        # Get base eligible users
        base_eligible = User.objects.filter(
            is_active=True,
            orders__isnull=False,  # Have placed orders
        ).exclude(
            Q(email='') | Q(phone__isnull=True)  # Must have contact info
        ).distinct()

        # Prioritize users who haven't ordered recently (inactive users)
        # This conserves credits by focusing on re-engagement
        inactive_users = base_eligible.filter(
            orders__created_at__lt=seven_days_ago  # Last order more than 7 days ago
        ).order_by('orders__created_at')[:60]  # Take oldest orders first, limit to 60

        # Fill remaining slots with moderately active users (3-7 days since last order)
        moderately_active = base_eligible.filter(
            orders__created_at__gte=seven_days_ago,
            orders__created_at__lt=three_days_ago
        ).exclude(
            id__in=inactive_users.values_list('id', flat=True)
        ).order_by('orders__created_at')[:30]  # Take oldest first, limit to 30

        # Combine prioritized users
        eligible_users = list(inactive_users) + list(moderately_active)

        # If we still have room, add some very active users (but limit to prevent spam)
        if len(eligible_users) < 90:
            very_active = base_eligible.filter(
                orders__created_at__gte=three_days_ago
            ).exclude(
                id__in=[u.id for u in eligible_users]
            ).order_by('orders__created_at')[:10]  # Very limited for active users

            eligible_users.extend(list(very_active))

        return eligible_users[:90]  # Final limit to prevent excessive API usage

    @staticmethod
    def _send_personalized_recommendation(user: User):
        """
        Generate and send a personalized recommendation to a user.
        """
        # Analyze user preferences and behavior
        user_insights = PersonalizedRecommendationService._analyze_user_behavior(user)

        # Generate recommendation message
        message = PersonalizedRecommendationService._generate_recommendation_message(user, user_insights)

        # Send via multiple channels
        PersonalizedRecommendationService._send_via_whatsapp(user, message)
        PersonalizedRecommendationService._send_via_email(user, message)
        PersonalizedRecommendationService._send_via_webhook(user, message, user_insights)

    @staticmethod
    def _analyze_user_behavior(user: User):
        """
        Analyze user's order history, preferences, and favorites to understand their tastes.
        """
        insights = {
            'preferred_cuisines': [],
            'favorite_restaurants': [],
            'order_frequency': 0,
            'avg_order_value': 0,
            'last_order_date': None,
            'time_of_day_preference': None,
            'location_preference': None,
        }

        # Get user's preferences
        try:
            preferences = user.preferences
            insights['preferred_cuisines'] = preferences.preferred_cuisines or []
            insights['location_preference'] = preferences.current_city
        except UserPreference.DoesNotExist:
            pass

        # Analyze order history
        orders = Order.objects.filter(customer=user).order_by('-created_at')

        if orders.exists():
            insights['order_frequency'] = PersonalizedRecommendationService._calculate_order_frequency(orders)
            insights['avg_order_value'] = orders.aggregate(avg=Avg('total_amount'))['avg'] or 0
            insights['last_order_date'] = orders.first().created_at

            # Extract preferred cuisines from order history
            ordered_items = MenuItem.objects.filter(order_items__order__customer=user).distinct()
            cuisines_from_orders = ordered_items.values_list('category', flat=True).distinct()
            insights['preferred_cuisines'].extend(list(cuisines_from_orders))

            # Find favorite restaurants
            vendor_counts = orders.values('vendor').annotate(
                order_count=Count('id')
            ).order_by('-order_count')[:3]

            for vendor_data in vendor_counts:
                try:
                    vendor = VendorProfile.objects.get(id=vendor_data['vendor'])
                    insights['favorite_restaurants'].append({
                        'vendor': vendor,
                        'order_count': vendor_data['order_count']
                    })
                except VendorProfile.DoesNotExist:
                    continue

        # Analyze favorites
        favorites = Favorite.objects.filter(user=user, favorite_type='venue')
        for favorite in favorites:
            if favorite.vendor:
                insights['favorite_restaurants'].append({
                    'vendor': favorite.vendor,
                    'is_favorite': True
                })

        # Determine time preference
        if orders.exists():
            hour_counts = {}
            for order in orders[:10]:  # Last 10 orders
                hour = order.created_at.hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1

            if hour_counts:
                preferred_hour = max(hour_counts, key=hour_counts.get)
                if 6 <= preferred_hour <= 10:
                    insights['time_of_day_preference'] = 'morning'
                elif 11 <= preferred_hour <= 15:
                    insights['time_of_day_preference'] = 'lunch'
                elif 18 <= preferred_hour <= 22:
                    insights['time_of_day_preference'] = 'dinner'

        return insights

    @staticmethod
    def _calculate_order_frequency(orders):
        """
        Calculate how often the user orders (orders per week).
        """
        if not orders:
            return 0

        # Get orders from last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_orders = orders.filter(created_at__gte=thirty_days_ago)

        if recent_orders.count() < 2:
            return recent_orders.count()  # Return actual count if less than 2

        # Calculate average days between orders
        first_order = recent_orders.last().created_at
        last_order = recent_orders.first().created_at
        days_span = (last_order - first_order).days or 1

        orders_per_week = (recent_orders.count() / days_span) * 7
        return round(orders_per_week, 1)

    @staticmethod
    def _generate_recommendation_message(user: User, insights: dict):
        """
        Generate a personalized recommendation message based on user insights.
        """
        # Get top recommendation
        recommendation = PersonalizedRecommendationService._get_top_recommendation(user, insights)

        if not recommendation:
            return None

        # Choose message template based on time and context
        current_hour = datetime.now().hour
        if 6 <= current_hour <= 10:
            template_category = 'morning'
        elif 11 <= current_hour <= 15:
            template_category = 'lunch'
        elif 18 <= current_hour <= 22:
            template_category = 'dinner'
        else:
            # Random choice between general and craving
            template_category = random.choice(['general', 'craving'])

        # Override with user's preferred time if available
        if insights.get('time_of_day_preference'):
            template_category = insights['time_of_day_preference']

        templates = PersonalizedRecommendationService.RECOMMENDATION_TEMPLATES[template_category]
        template = random.choice(templates)

        # Fill in template variables
        message = template.format(
            name=user.first_name or user.email.split('@')[0],
            restaurant=recommendation['vendor'].business_name,
            cuisine=recommendation.get('cuisine', 'delicious')
        )

        return message

    @staticmethod
    def _get_top_recommendation(user: User, insights: dict):
        """
        Get the top recommendation for a user based on their insights.
        """
        # Use the existing recommendation system but personalize it
        import requests
        from django.conf import settings

        # Get recommendations with user's preferences
        user_location = {}
        if insights.get('location_preference'):
            user_location['city'] = insights['location_preference']

        # Make HTTP API call to the recommendations endpoint
        base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
        api_url = f"{base_url}/api/user/recommendations/"

        params = {
            'limit': 5,
        }
        if user_location.get('city'):
            params['city'] = user_location['city']

        try:
            response = requests.get(api_url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('recommendations'):
                    recommendations = data['recommendations']
                else:
                    return None
            else:
                return None
        except Exception as e:
            logger.error(f"Error calling recommendations API: {str(e)}")
            return None

        if not recommendations:
            return None

        # Score recommendations based on user insights
        scored_recommendations = []
        for rec in recommendations:
            score = PersonalizedRecommendationService._score_recommendation(rec, insights)
            scored_recommendations.append((rec, score))

        # Sort by score and return top recommendation
        scored_recommendations.sort(key=lambda x: x[1], reverse=True)

        top_rec, top_score = scored_recommendations[0]

        # Add cuisine info and menu details with images/videos
        cuisine = PersonalizedRecommendationService._extract_cuisine_from_vendor(top_rec['id'])
        vendor = VendorProfile.objects.get(id=top_rec['id'])

        # Get top menu items with images/videos
        top_menu_items = []
        menu_items = vendor.menu_items.filter(available_now=True)[:3]  # Get top 3 available items

        for item in menu_items:
            item_data = {
                'name': item.dish_name,
                'description': item.item_description,
                'price': str(item.price),
                'category': item.category,
                'has_image': bool(item.image),
                'has_video': bool(item.video),
                'image_url': item.image.url if item.image else None,
                'video_url': item.video.url if item.video else None,
            }
            top_menu_items.append(item_data)

        return {
            'vendor': vendor,
            'cuisine': cuisine,
            'score': top_score,
            'top_menu_items': top_menu_items,
            'has_video_content': any(item.get('has_video') for item in top_menu_items)
        }

    @staticmethod
    def _score_recommendation(recommendation: dict, insights: dict):
        """
        Score a recommendation based on user insights.
        Prioritizes Pro subscription vendors.
        """
        score = recommendation.get('recommendation_score', 0)

        vendor_id = recommendation['id']

        # Check if vendor has Pro subscription - major boost for paid subscribers
        try:
            vendor = VendorProfile.objects.get(id=vendor_id)
            if hasattr(vendor, 'subscription') and vendor.subscription and vendor.subscription.is_featured_active:
                score += 50  # Major boost for Pro subscribers
        except VendorProfile.DoesNotExist:
            pass

        # Boost score if user has ordered from this vendor before
        if any(fav.get('vendor') and fav['vendor'].id == vendor_id for fav in insights['favorite_restaurants']):
            score += 20

        # Boost score if cuisine matches preferences
        vendor_cuisine = PersonalizedRecommendationService._extract_cuisine_from_vendor(vendor_id)
        if vendor_cuisine and vendor_cuisine.lower() in [c.lower() for c in insights['preferred_cuisines']]:
            score += 15

        # Boost score for featured vendors (they paid for visibility)
        if recommendation.get('is_featured'):
            score += 10

        return score

    @staticmethod
    def _extract_cuisine_from_vendor(vendor_id):
        """
        Extract cuisine type from vendor's menu items.
        """
        try:
            vendor = VendorProfile.objects.get(id=vendor_id)
            menu_items = vendor.menu_items.all()
            if menu_items.exists():
                # Get most common category
                categories = menu_items.values_list('category', flat=True)
                return max(set(categories), key=categories.count)
        except:
            pass
        return 'local cuisine'

    @staticmethod
    def _send_via_whatsapp(user: User, message: str):
        """
        Send recommendation via WhatsApp.
        """
        if not user.phone or not message:
            return

        try:
            from whatsapp_ai.services.whatsapp_service import WhatsAppService
            whatsapp_service = WhatsAppService()
            whatsapp_service.send_message(
                to=user.phone,
                message=message,
                message_type='recommendation'
            )
        except Exception as e:
            logger.error(f"WhatsApp recommendation failed for user {user.id}: {str(e)}")

    @staticmethod
    def _send_via_email(user: User, message: str):
        """
        Send recommendation via email.
        """
        if not user.email or not message:
            return

        try:
            from django.core.mail import send_mail
            from django.conf import settings

            subject = f"🍽️ Personalized Restaurant Recommendation for You!"

            # Add some HTML formatting
            html_message = f"""
            <html>
            <body>
                <h2>🍴 Bestyy Restaurant Recommendation</h2>
                <p>{message}</p>
                <p><a href="{settings.BASE_URL}/restaurants">Browse Restaurants</a></p>
                <p>Best regards,<br>Bestyy Team</p>
            </body>
            </html>
            """

            send_mail(
                subject=subject,
                message=message,  # Plain text version
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )
        except Exception as e:
            logger.error(f"Email recommendation failed for user {user.id}: {str(e)}")

    @staticmethod
    def _send_via_webhook(user: User, message: str, insights: dict):
        """
        Send recommendation via webhook if user has webhook configured.
        """
        # This would require adding webhook_url field to User model
        # For now, we'll skip this or implement a basic version
        pass

    @staticmethod
    def get_recommendation_preview(user_id: int):
        """
        Get a preview of what recommendation would be sent to a user.
        Useful for testing and admin review.
        """
        try:
            user = User.objects.get(id=user_id)
            insights = PersonalizedRecommendationService._analyze_user_behavior(user)
            message = PersonalizedRecommendationService._generate_recommendation_message(user, insights)

            return {
                'user': user.email,
                'insights': insights,
                'message': message,
                'would_send': bool(message and (user.email or user.phone))
            }
        except User.DoesNotExist:
            return None