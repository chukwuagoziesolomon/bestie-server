"""
Budget-aware ordering service for handling price constraints and suggestions
"""
import re
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.db.models import Q, Min, Max
from ..models import VendorProfile, UserProfile
# MenuItem model is not available in the current codebase

logger = logging.getLogger(__name__)


class BudgetAnalysisService:
    """
    Service for analyzing user budgets and finding optimal ordering options
    """

    BUDGET_PATTERNS = [
        r'\bunder\s*₦?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'\bbelow\s*₦?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'\bno\s+more\s+than\s*₦?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'\bmaximum\s*₦?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'\baround\s*₦?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'\babout\s*₦?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'\bup\s+to\s*₦?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'\bat\s+most\s*₦?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'\b≤\s*₦?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'\b<=\s*₦?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
    ]

    def __init__(self):
        self.flexibility_percentage = 10  # Allow 10% over budget by default

    def extract_budget_from_text(self, text: str) -> Optional[Decimal]:
        """
        Extract budget amount from natural language text
        """
        text_lower = text.lower().strip()

        for pattern in self.BUDGET_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    return Decimal(amount_str)
                except (ValueError, TypeError):
                    continue

        return None

    def find_items_within_budget(self, food_type: str, max_budget: Decimal,
                               location_coords: Optional[Dict] = None,
                               limit: int = 5) -> List[Dict]:
        """
        Find menu items within budget constraints.
        MenuItem model is not available, so returns empty list.
        """
        return []

    def generate_budget_alternatives(self, food_type: str, requested_budget: Decimal,
                                   location_coords: Optional[Dict] = None) -> Dict:
        """
        Generate alternative suggestions when exact budget match not found
        """
        # Find items slightly over budget (within flexibility)
        flexible_budget = requested_budget * (1 + Decimal(str(self.flexibility_percentage)) / 100)

        # Find cheaper alternatives
        cheaper_items = self.find_items_within_budget(food_type, requested_budget, location_coords, 3)

        # Find slightly more expensive items (within flexibility)
        # MenuItem model is not available, so return empty list
        over_budget_results = []

        # Find similar items in different categories
        similar_items = self._find_similar_category_items(food_type, requested_budget, location_coords)

        return {
            'requested_budget': float(requested_budget),
            'flexible_budget': float(flexible_budget),
            'cheaper_alternatives': cheaper_items,
            'slightly_over_budget': over_budget_results,
            'similar_category_items': similar_items,
            'has_exact_matches': len(cheaper_items) > 0,
            'has_flexible_matches': len(over_budget_results) > 0
        }

    def _find_similar_category_items(self, food_type: str, budget: Decimal,
                                   location_coords: Optional[Dict] = None) -> List[Dict]:
        """
        Find similar items in different categories within budget
        """
        # Simple category mapping - could be enhanced with ML
        category_mappings = {
            'pizza': ['pasta', 'sandwich', 'burger'],
            'burger': ['sandwich', 'pizza', 'shawarma'],
            'chicken': ['fish', 'beef', 'turkey'],
            'rice': ['pasta', 'yam', 'bread'],
            'soup': ['stew', 'sauce', 'porridge']
        }

        similar_categories = category_mappings.get(food_type.lower(), [])

        if not similar_categories:
            return []

        # Find items in similar categories within budget
        # MenuItem model is not available, so return empty list
        return []

    def analyze_budget_feasibility(self, cart_items: List[Dict], user_budget: Optional[Decimal] = None) -> Dict:
        """
        Analyze if a cart is within budget and suggest optimizations
        """
        total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart_items)

        analysis = {
            'total_cost': float(total_cost),
            'item_count': len(cart_items),
            'within_budget': True,
            'budget_difference': 0.0,
            'suggestions': []
        }

        if user_budget:
            analysis['user_budget'] = float(user_budget)
            analysis['within_budget'] = total_cost <= user_budget
            analysis['budget_difference'] = float(user_budget - total_cost)

            if not analysis['within_budget']:
                # Generate suggestions to reduce cost
                analysis['suggestions'] = self._generate_budget_reduction_suggestions(
                    cart_items, total_cost, user_budget
                )

        return analysis

    def _generate_budget_reduction_suggestions(self, cart_items: List[Dict],
                                             total_cost: Decimal, budget: Decimal) -> List[Dict]:
        """
        Generate suggestions to reduce cart cost to fit budget
        """
        suggestions = []
        excess_amount = total_cost - budget

        # Sort items by price for removal suggestions
        sorted_items = sorted(cart_items, key=lambda x: x.get('price', 0), reverse=True)

        # Suggestion 1: Remove most expensive item
        if sorted_items:
            expensive_item = sorted_items[0]
            new_total = total_cost - (expensive_item.get('price', 0) * expensive_item.get('quantity', 1))
            savings = total_cost - new_total

            suggestions.append({
                'type': 'remove_item',
                'description': f'Remove {expensive_item.get("name", "item")}',
                'savings': float(savings),
                'new_total': float(new_total),
                'item_id': expensive_item.get('id')
            })

        # Suggestion 2: Reduce quantities
        for item in sorted_items[:2]:  # Check first 2 expensive items
            if item.get('quantity', 1) > 1:
                reduction = 1
                new_quantity = item['quantity'] - reduction
                savings = item['price'] * reduction
                new_total = total_cost - savings

                suggestions.append({
                    'type': 'reduce_quantity',
                    'description': f'Reduce {item["name"]} quantity to {new_quantity}',
                    'savings': float(savings),
                    'new_total': float(new_total),
                    'item_id': item['id'],
                    'new_quantity': new_quantity
                })

        # Suggestion 3: Find cheaper alternatives
        for item in sorted_items[:1]:  # Check most expensive item
            alternatives = self._find_cheaper_alternatives(item, excess_amount)
            for alt in alternatives[:2]:  # Limit to 2 alternatives
                price_diff = item['price'] - alt['price']
                new_total = total_cost - price_diff

                suggestions.append({
                    'type': 'substitute_item',
                    'description': f'Replace {item["name"]} with cheaper {alt["name"]}',
                    'savings': float(price_diff),
                    'new_total': float(new_total),
                    'original_item_id': item['id'],
                    'alternative_item': alt
                })

        return suggestions

    def _find_cheaper_alternatives(self, original_item: Dict, min_savings: Decimal) -> List[Dict]:
        """
        Find cheaper alternatives to an expensive item.
        MenuItem model is not available, so returns empty list.
        """
        return []