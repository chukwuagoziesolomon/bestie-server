"""
Alternative suggestions service for handling unavailable items and budget constraints
"""
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.db.models import Q, F, Avg
from ..models import VendorProfile
from bestyy.restaurant_features.order.models import Order
# MenuItem model is not available in the current codebase

logger = logging.getLogger(__name__)


class AlternativeSuggestionsService:
    """
    Service for generating alternative suggestions when items are unavailable
    or don't meet budget constraints
    """

    def __init__(self):
        self.category_mappings = {
            'pizza': ['pasta', 'sandwich', 'burger', 'shawarma'],
            'burger': ['sandwich', 'pizza', 'shawarma', 'chicken'],
            'chicken': ['fish', 'beef', 'turkey', 'goat meat'],
            'rice': ['pasta', 'yam', 'bread', 'plantain'],
            'soup': ['stew', 'sauce', 'porridge', 'egusi'],
            'pasta': ['rice', 'yam', 'potato', 'pizza'],
            'fish': ['chicken', 'beef', 'turkey', 'shrimps'],
            'beef': ['chicken', 'fish', 'turkey', 'goat meat'],
            'shawarma': ['burger', 'sandwich', 'pizza', 'chicken'],
            'sandwich': ['burger', 'pizza', 'shawarma', 'pasta']
        }

        self.cuisine_mappings = {
            'nigerian': ['african', 'local', 'traditional'],
            'italian': ['mediterranean', 'european', 'pizza'],
            'chinese': ['asian', 'fast_food', 'noodles'],
            'american': ['fast_food', 'burgers', 'pizza'],
            'mexican': ['latin', 'spicy', 'burritos']
        }

    def generate_item_alternatives(self, unavailable_item: str, user_budget: Optional[Decimal] = None,
                                 location_coords: Optional[Dict] = None, max_suggestions: int = 3) -> Dict:
        """
        Generate alternative suggestions when an item is unavailable
        """
        alternatives = {
            'substitutes': [],
            'similar_category': [],
            'budget_alternatives': [],
            'nearby_vendors': []
        }

        # Find exact substitutes (same name, different vendors)
        substitutes = self._find_exact_substitutes(unavailable_item, user_budget, location_coords)
        alternatives['substitutes'] = substitutes[:max_suggestions]

        # Find similar category items
        similar_items = self._find_similar_category_items(unavailable_item, user_budget, location_coords)
        alternatives['similar_category'] = similar_items[:max_suggestions]

        # Find budget-friendly alternatives if budget specified
        if user_budget:
            budget_alts = self._find_budget_alternatives(unavailable_item, user_budget, location_coords)
            alternatives['budget_alternatives'] = budget_alts[:max_suggestions]

        # Find nearby vendors with similar items
        nearby = self._find_nearby_vendors_with_similar_items(unavailable_item, location_coords)
        alternatives['nearby_vendors'] = nearby[:max_suggestions]

        return alternatives

    def _find_exact_substitutes(self, item_name: str, budget: Optional[Decimal] = None,
                               location_coords: Optional[Dict] = None) -> List[Dict]:
        """
        Find exact item name matches from different vendors.
        """
        try:
            from bestyy.restaurant_features.product.models import Product as MenuItem

            # Find items with similar names from different vendors
            similar_items = MenuItem.objects.filter(
                Q(dish_name__icontains=item_name) |
                Q(item_description__icontains=item_name),
                available_now=True
            ).select_related('vendor').exclude(
                vendor__verification_status='rejected'
            )[:10]  # Get more to filter

            results = []
            for item in similar_items:
                # Skip if budget specified and item is too expensive
                if budget and float(item.price) > float(budget):
                    continue

                results.append({
                    'id': item.id,
                    'name': item.dish_name,
                    'description': item.item_description or '',
                    'price': float(item.price),
                    'image': item.image.url if item.image else None,
                    'category': item.category or 'Other',
                    'vendor_name': item.vendor.business_name,
                    'vendor_id': item.vendor.id,
                    'vendor_logo': item.vendor.logo.url if item.vendor.logo else None,
                    'vendor_rating': getattr(item.vendor, 'avg_rating', 4.0) or 4.0,
                    'delivery_time': f"{getattr(item.vendor, 'delivery_time_min', 20) or 20}-{getattr(item.vendor, 'delivery_time_max', 45) or 45} min",
                    'vendor_address': item.vendor.business_address,
                    'is_available': item.available_now,
                    'preparation_time': getattr(item, 'preparation_time_minutes', 15) or 15,
                    'score': self._calculate_item_score(item, item_name)
                })

            # Sort by relevance score and return top results
            results.sort(key=lambda x: x.get('score', 0), reverse=True)
            return results[:5]

        except Exception as e:
            logger.error(f"Error finding exact substitutes: {str(e)}")
            return []

    def _find_similar_category_items(self, item_name: str, budget: Optional[Decimal] = None,
                                    location_coords: Optional[Dict] = None) -> List[Dict]:
        """
        Find items in similar categories.
        """
        try:
            from bestyy.restaurant_features.product.models import Product as MenuItem

            # Determine category of the requested item
            category = self._categorize_item(item_name)

            # Find items in the same category
            category_items = MenuItem.objects.filter(
                category__icontains=category,
                available_now=True
            ).select_related('vendor').exclude(
                vendor__verification_status='rejected'
            )[:15]  # Get more to filter

            results = []
            for item in category_items:
                # Skip if budget specified and item is too expensive
                if budget and float(item.price) > float(budget):
                    continue

                results.append({
                    'id': item.id,
                    'name': item.dish_name,
                    'description': item.item_description or '',
                    'price': float(item.price),
                    'image': item.image.url if item.image else None,
                    'category': item.category or 'Other',
                    'vendor_name': item.vendor.business_name,
                    'vendor_id': item.vendor.id,
                    'vendor_logo': item.vendor.logo.url if item.vendor.logo else None,
                    'vendor_rating': getattr(item.vendor, 'avg_rating', 4.0) or 4.0,
                    'delivery_time': f"{getattr(item.vendor, 'delivery_time_min', 20) or 20}-{getattr(item.vendor, 'delivery_time_max', 45) or 45} min",
                    'vendor_address': item.vendor.business_address,
                    'is_available': item.available_now,
                    'preparation_time': getattr(item, 'preparation_time_minutes', 15) or 15,
                    'similarity_reason': f'Same category: {category}',
                    'score': self._calculate_category_score(item, category)
                })

            # Sort by score and return top results
            results.sort(key=lambda x: x.get('score', 0), reverse=True)
            return results[:5]

        except Exception as e:
            logger.error(f"Error finding similar category items: {str(e)}")
            return []

    def _find_budget_alternatives(self, item_name: str, budget: Decimal,
                                 location_coords: Optional[Dict] = None) -> List[Dict]:
        """
        Find cheaper alternatives within budget.
        """
        try:
            from bestyy.restaurant_features.product.models import Product as MenuItem

            # Find items cheaper than the budget
            budget_items = MenuItem.objects.filter(
                price__lte=budget,
                available_now=True
            ).select_related('vendor').exclude(
                vendor__verification_status='rejected'
            ).order_by('-price')[:10]  # Get most expensive within budget first

            results = []
            for item in budget_items:
                results.append({
                    'id': item.id,
                    'name': item.dish_name,
                    'description': item.item_description or '',
                    'price': float(item.price),
                    'image': item.image.url if item.image else None,
                    'category': item.category or 'Other',
                    'vendor_name': item.vendor.business_name,
                    'vendor_id': item.vendor.id,
                    'vendor_logo': item.vendor.logo.url if item.vendor.logo else None,
                    'vendor_rating': getattr(item.vendor, 'avg_rating', 4.0) or 4.0,
                    'delivery_time': f"{getattr(item.vendor, 'delivery_time_min', 20) or 20}-{getattr(item.vendor, 'delivery_time_max', 45) or 45} min",
                    'vendor_address': item.vendor.business_address,
                    'is_available': item.available_now,
                    'preparation_time': getattr(item, 'preparation_time_minutes', 15) or 15,
                    'savings': float(budget) - float(item.price),
                    'score': self._calculate_budget_score(item, budget)
                })

            # Sort by score (best value first)
            results.sort(key=lambda x: x.get('score', 0), reverse=True)
            return results[:5]

        except Exception as e:
            logger.error(f"Error finding budget alternatives: {str(e)}")
            return []

    def _find_nearby_vendors_with_similar_items(self, item_name: str,
                                               location_coords: Optional[Dict] = None) -> List[Dict]:
        """
        Find nearby vendors that might have similar items.
        """
        try:
            from ..models import VendorProfile

            # Get category of the requested item
            category = self._categorize_item(item_name)

            # Find vendors with items in similar categories
            # For now, return top-rated vendors (since location filtering would need coordinates)
            nearby_vendors = VendorProfile.objects.filter(
                verification_status='approved',
                is_suspended=False
            ).order_by('-avg_rating')[:5]

            results = []
            for vendor in nearby_vendors:
                results.append({
                    'vendor_id': vendor.id,
                    'vendor_name': vendor.business_name,
                    'vendor_logo': vendor.logo.url if vendor.logo else None,
                    'vendor_rating': getattr(vendor, 'avg_rating', 4.0) or 4.0,
                    'delivery_time': f"{getattr(vendor, 'delivery_time_min', 20) or 20}-{getattr(vendor, 'delivery_time_max', 45) or 45} min",
                    'vendor_address': vendor.business_address,
                    'business_category': vendor.business_category,
                    'distance_km': None,  # Would need location coords to calculate
                    'estimated_delivery_fee': getattr(vendor, 'base_delivery_fee', 1500) or 1500,
                    'is_open': True,  # Simplified - would check operating hours
                    'score': (getattr(vendor, 'avg_rating', 4.0) or 4.0) * 10
                })

            return results

        except Exception as e:
            logger.error(f"Error finding nearby vendors: {str(e)}")
            return []

    def _categorize_item(self, item_name: str) -> str:
        """
        Categorize an item based on its name
        """
        item_lower = item_name.lower()

        # Direct category mappings
        category_keywords = {
            'pizza': ['pizza', 'margherita', 'pepperoni', 'hawaiian'],
            'burger': ['burger', 'cheeseburger', 'bacon burger'],
            'chicken': ['chicken', 'fried chicken', 'grilled chicken'],
            'rice': ['rice', 'jollof', 'fried rice', 'white rice'],
            'pasta': ['pasta', 'spaghetti', 'macaroni', 'noodles'],
            'soup': ['soup', 'egusi', 'ogbono', 'efo riro'],
            'fish': ['fish', 'grilled fish', 'fried fish'],
            'beef': ['beef', 'cow meat', 'steak'],
            'shawarma': ['shawarma', 'kebab', 'gyro'],
            'sandwich': ['sandwich', 'panini', 'wrap']
        }

        for category, keywords in category_keywords.items():
            if any(keyword in item_lower for keyword in keywords):
                return category

        # Default category
        return 'other'

    def generate_unavailable_item_response(self, item_name: str, alternatives: Dict) -> str:
        """
        Generate a user-friendly response for unavailable items
        """
        response = f"Sorry, {item_name} is currently unavailable. Here are some alternatives:\n\n"

        if alternatives['substitutes']:
            response += "📍 *Same item from other vendors:*\n"
            for i, alt in enumerate(alternatives['substitutes'][:2], 1):
                response += f"{i}. {alt['name']} - ₦{alt['price']:,.0f} at {alt['vendor_name']}\n"
            response += "\n"

        if alternatives['similar_category']:
            response += "🔄 *Similar options:*\n"
            for i, alt in enumerate(alternatives['similar_category'][:2], 1):
                response += f"{i}. {alt['name']} ({alt['category']}) - ₦{alt['price']:,.0f} at {alt['vendor_name']}\n"
            response += "\n"

        if alternatives['budget_alternatives']:
            response += "💰 *More budget-friendly options:*\n"
            for i, alt in enumerate(alternatives['budget_alternatives'][:2], 1):
                response += f"{i}. {alt['name']} - ₦{alt['price']:,.0f} at {alt['vendor_name']} (save ₦{alt['savings']:.0f})\n"
            response += "\n"

        response += "👉 *Reply with the number to order an alternative, or 'cancel' to cancel this order.*"

        return response

    def generate_budget_exceeded_response(self, item_name: str, requested_budget: Decimal,
                                        alternatives: Dict) -> str:
        """
        Generate response when budget is exceeded
        """
        response = f"The {item_name} you requested exceeds your ₦{requested_budget:,.0f} budget. Here are options within your budget:\n\n"

        if alternatives['budget_alternatives']:
            response += "💰 *Budget-friendly alternatives:*\n"
            for i, alt in enumerate(alternatives['budget_alternatives'], 1):
                response += f"{i}. {alt['name']} - ₦{alt['price']:,.0f} at {alt['vendor_name']}\n"
            response += "\n"

        if alternatives['similar_category']:
            response += "🔄 *Similar items:*\n"
            for i, alt in enumerate(alternatives['similar_category'][:2], 1):
                response += f"{i}. {alt['name']} - ₦{alt['price']:,.0f} at {alt['vendor_name']}\n"
            response += "\n"

        response += f"👉 *Reply with the number to order, or 'flexible' if you can go slightly over ₦{requested_budget:,.0f}.*"

        return response

    def suggest_order_modifications(self, order: Order, issue_type: str) -> List[Dict]:
        """
        Suggest modifications to fix order issues.
        MenuItem model is not available, so returns empty list.
        """
        return []

    def _calculate_item_score(self, item, search_term: str) -> float:
        """
        Calculate relevance score for item based on name match.
        """
        score = 0.0

        # Exact name match gets highest score
        if item.dish_name.lower() == search_term.lower():
            score += 100
        elif search_term.lower() in item.dish_name.lower():
            score += 50

        # Description match
        if item.item_description and search_term.lower() in item.item_description.lower():
            score += 20

        # Vendor rating bonus
        vendor_rating = getattr(item.vendor, 'avg_rating', 4.0) or 4.0
        score += vendor_rating * 5

        # Availability bonus
        if item.available_now:
            score += 10

        return score

    def _calculate_category_score(self, item, category: str) -> float:
        """
        Calculate score for category-based recommendations.
        """
        score = 0.0

        # Category match
        if item.category and category.lower() in item.category.lower():
            score += 50

        # Vendor rating bonus
        vendor_rating = getattr(item.vendor, 'avg_rating', 4.0) or 4.0
        score += vendor_rating * 5

        # Availability bonus
        if item.available_now:
            score += 10

        # Price factor (prefer reasonably priced items)
        price = float(item.price)
        if 500 <= price <= 5000:  # Sweet spot for pricing
            score += 20
        elif price < 500:  # Too cheap might be suspicious
            score += 5

        return score

    def _calculate_budget_score(self, item, budget: Decimal) -> float:
        """
        Calculate score for budget-based recommendations.
        """
        score = 0.0

        price = float(item.price)
        budget_float = float(budget)

        # Savings percentage (higher savings = higher score)
        savings_percentage = ((budget_float - price) / budget_float) * 100
        score += min(savings_percentage, 50)  # Cap at 50 points

        # Vendor rating bonus
        vendor_rating = getattr(item.vendor, 'avg_rating', 4.0) or 4.0
        score += vendor_rating * 5

        # Availability bonus
        if item.available_now:
            score += 10

        # Prefer items that are reasonably close to budget (not too cheap)
        budget_utilization = (price / budget_float) * 100
        if 30 <= budget_utilization <= 90:  # Good utilization range
            score += 15

        return score