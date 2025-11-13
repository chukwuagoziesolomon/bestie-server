"""
Smart recommendations API for finding similar items across vendors
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, F, Avg, Count
from django.db.models.functions import Lower
from bestyy.restaurant_features.product.models import Product as MenuItem
from ..models import VendorProfile
from ..services.alternative_suggestions_service import AlternativeSuggestionsService
from ..services.budget_analysis_service import BudgetAnalysisService
import logging

logger = logging.getLogger(__name__)


class SmartItemRecommendationsView(APIView):
    """
    API endpoint for smart item recommendations across all vendors
    """
    permission_classes = []  # Allow public access

    def get(self, request):
        """
        Get smart recommendations for an item across all vendors
        """
        item_name = request.query_params.get('item', '').strip()
        vendor_name = request.query_params.get('vendor', '').strip()
        budget = request.query_params.get('budget')
        limit = int(request.query_params.get('limit', 5))

        if not item_name:
            return Response(
                {'error': 'Item name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse budget if provided
        budget_amount = None
        if budget:
            try:
                budget_amount = float(budget.replace('₦', '').replace(',', '').strip())
            except (ValueError, TypeError):
                pass

        # Check if exact item/vendor combination exists
        exact_matches = self._find_exact_matches(item_name, vendor_name, budget_amount)

        if exact_matches:
            # Return exact matches with direct ordering option
            response_data = self._format_exact_matches(exact_matches, item_name, vendor_name)
        else:
            # Find smart alternatives
            alternatives = self._find_smart_alternatives(item_name, vendor_name, budget_amount, limit)
            response_data = self._format_alternatives(alternatives, item_name, vendor_name)

        return Response(response_data)

    def _find_exact_matches(self, item_name: str, vendor_name: str = None, budget: float = None):
        """
        Find exact matches for item/vendor combination.
        MenuItem model is unavailable in the current build, so return empty.
        """
        return []

    def _find_smart_alternatives(self, item_name: str, vendor_name: str = None,
                               budget: float = None, limit: int = 5):
        """
        Find smart alternatives when exact match not found
        """
        alt_service = AlternativeSuggestionsService()
        budget_service = BudgetAnalysisService()

        # Get comprehensive alternatives
        alternatives = alt_service.generate_item_alternatives(
            item_name,
            user_budget=budget
        )

        # Combine and prioritize results
        smart_recommendations = []

        # 1. Add exact substitutes first
        for alt in alternatives.get('substitutes', [])[:2]:
            smart_recommendations.append({
                'type': 'exact_substitute',
                'priority': 1,
                **alt
            })

        # 2. Add same category items
        for alt in alternatives.get('similar_category', [])[:2]:
            smart_recommendations.append({
                'type': 'same_category',
                'priority': 2,
                **alt
            })

        # 3. Add budget alternatives if budget specified
        if budget:
            for alt in alternatives.get('budget_alternatives', [])[:2]:
                smart_recommendations.append({
                    'type': 'budget_option',
                    'priority': 3,
                    **alt
                })

        # 4. Add nearby vendor options
        for alt in alternatives.get('nearby_vendors', [])[:1]:
            smart_recommendations.append({
                'type': 'nearby_vendor',
                'priority': 4,
                **alt
            })

        # Sort by priority then any score field if present
        smart_recommendations.sort(key=lambda x: (x.get('priority', 99), -x.get('score', 0)))
        return smart_recommendations[:limit]

    def _format_exact_matches(self, items, item_name: str, vendor_name: str = None):
        return {
            'query': {
                'item': item_name,
                'vendor': vendor_name
            },
            'exact_matches': [],
            'alternatives': []
        }

    def _format_alternatives(self, alternatives, item_name: str, vendor_name: str = None):
        return {
            'query': {
                'item': item_name,
                'vendor': vendor_name
            },
            'exact_matches': [],
            'alternatives': alternatives
        }


class VendorItemSearchView(APIView):
    """
    Search for items across all vendors with smart filtering
    """
    permission_classes = []  # Allow public access

    def get(self, request):
        """
        Search for items with smart filtering and recommendations
        """
        query = request.query_params.get('q', '').strip()
        category = request.query_params.get('category')
        max_price = request.query_params.get('max_price')
        vendor_id = request.query_params.get('vendor_id')
        limit = int(request.query_params.get('limit', 10))

        if not query:
            return Response(
                {'error': 'Search query is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build search query
        search_query = Q()
        search_query &= (
            Q(dish_name__icontains=query) |
            Q(item_description__icontains=query) |
            Q(category__icontains=query)
        )

        # Add filters
        if category:
            search_query &= Q(category__icontains=category)
        if max_price:
            try:
                search_query &= Q(price__lte=float(max_price))
            except ValueError:
                pass
        if vendor_id:
            search_query &= Q(vendor_id=vendor_id)

        # Execute search
        items = MenuItem.objects.filter(
            search_query,
            available_now=True
        ).select_related('vendor').order_by('price')[:limit]

        # Format results
        results = []
        for item in items:
            results.append({
                'id': item.id,
                'name': item.dish_name,
                'description': item.item_description,
                'price': float(item.price),
                'category': item.category,
                'vendor_name': item.vendor.business_name,
                'vendor_id': item.vendor.id,
                'image': item.image.url if item.image else None,
                'rating': item.vendor.avg_rating or 4.0,
                'delivery_time': f"{item.vendor.delivery_time_min or 20}-{item.vendor.delivery_time_max or 45} min"
            })

        return Response({
            'query': query,
            'total_results': len(results),
            'results': results,
            'filters_applied': {
                'category': category,
                'max_price': max_price,
                'vendor_id': vendor_id
            }
        })


class SimilarItemsView(APIView):
    """
    Find items similar to a given item
    """
    permission_classes = []  # Allow public access

    def get(self, request):
        """
        Find items similar to the specified item
        """
        item_id = request.query_params.get('item_id')
        item_name = request.query_params.get('item_name')
        limit = int(request.query_params.get('limit', 5))

        if not item_id and not item_name:
            return Response(
                {'error': 'Either item_id or item_name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the reference item
        if item_id:
            try:
                reference_item = MenuItem.objects.select_related('vendor').get(id=item_id)
            except MenuItem.DoesNotExist:
                return Response(
                    {'error': 'Item not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Find first matching item by name
            reference_item = MenuItem.objects.filter(
                Q(dish_name__icontains=item_name) |
                Q(item_description__icontains=item_name),
                available_now=True
            ).select_related('vendor').first()

            if not reference_item:
                return Response(
                    {'error': 'Item not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Find similar items
        similar_items = self._find_similar_items(reference_item, limit)

        return Response({
            'reference_item': {
                'id': reference_item.id,
                'name': reference_item.dish_name,
                'category': reference_item.category,
                'price': float(reference_item.price),
                'vendor_name': reference_item.vendor.business_name
            },
            'similar_items': similar_items,
            'total_similar': len(similar_items)
        })

    def _find_similar_items(self, reference_item: MenuItem, limit: int):
        """
        Find items similar to the reference item
        """
        # Find items in same category from different vendors
        similar_items = MenuItem.objects.filter(
            category=reference_item.category,
            available_now=True
        ).exclude(
            id=reference_item.id
        ).exclude(
            vendor=reference_item.vendor
        ).select_related('vendor').order_by('price')[:limit]

        results = []
        for item in similar_items:
            results.append({
                'id': item.id,
                'name': item.dish_name,
                'description': item.item_description,
                'price': float(item.price),
                'vendor_name': item.vendor.business_name,
                'vendor_id': item.vendor.id,
                'image': item.image.url if item.image else None,
                'similarity_reason': f'Same category: {item.category}',
                'price_comparison': 'cheaper' if item.price < reference_item.price else 'more_expensive'
            })

        return results