"""
Smart Vendor Recommendation Service
Handles vendor recommendations with:
- Featured vendor priority
- Fallback recommendations when preferred vendor unavailable
- "MORE" pagination for browsing
- Rich vendor display (picture, price, bio, ratings)
"""
import logging
from typing import Dict, List, Optional, Tuple
from django.db.models import Q, Avg, Count, Prefetch
from django.core.cache import cache
from decimal import Decimal

logger = logging.getLogger(__name__)


class VendorRecommendationService:
    """
    Smart vendor recommendation engine with featured priority
    """
    
    VENDORS_PER_PAGE = 3  # Show 3 vendors at a time
    
    def __init__(self, user=None, user_location: Dict = None):
        self.user = user
        self.user_location = user_location or {}
        
    def search_vendors_for_dish(
        self, 
        dish_name: str, 
        preferred_vendor_name: Optional[str] = None,
        page: int = 1
    ) -> Dict:
        """
        Search for vendors that serve a specific dish
        
        Args:
            dish_name: Name of the dish/product
            preferred_vendor_name: Optional preferred vendor name
            page: Page number for pagination (1-indexed)
            
        Returns:
            {
                'found_preferred': bool,
                'preferred_vendor': dict or None,
                'recommended_vendors': list,
                'total_vendors': int,
                'current_page': int,
                'has_more': bool,
                'message': str  # WhatsApp formatted message
            }
        """
        from bestyy.core_features.user.models import VendorProfile
        from bestyy.restaurant_features.product.models import Product
        
        # Step 1: Search for products matching the dish name
        products = Product.objects.filter(
            Q(name__icontains=dish_name) | Q(description__icontains=dish_name),
            is_available=True,
            stock_quantity__gt=0
        ).select_related('vendor', 'vendor__user')
        
        if not products.exists():
            return {
                'found_preferred': False,
                'preferred_vendor': None,
                'recommended_vendors': [],
                'total_vendors': 0,
                'current_page': page,
                'has_more': False,
                'message': f"😕 Sorry, I couldn't find any vendors serving *{dish_name}*.\n\nTry searching for something else or browse our featured vendors!"
            }
        
        # Step 2: Check if preferred vendor exists and has the dish
        preferred_vendor = None
        found_preferred = False
        
        if preferred_vendor_name:
            preferred_products = products.filter(
                vendor__business_name__icontains=preferred_vendor_name,
                vendor__is_suspended=False,
                vendor__verification_status='approved'
            )
            
            if preferred_products.exists():
                found_preferred = True
                product = preferred_products.first()
                preferred_vendor = self._format_vendor_display(
                    product.vendor,
                    product,
                    is_preferred=True
                )
        
        # Step 3: Get other vendors (featured first)
        other_vendors_query = products.exclude(
            vendor__business_name__icontains=preferred_vendor_name
        ) if preferred_vendor_name else products
        
        # Filter active, approved vendors
        other_vendors_query = other_vendors_query.filter(
            vendor__is_suspended=False,
            vendor__verification_status='approved'
        )
        
        # Get unique vendor IDs (SQLite-compatible way)
        vendor_ids = list(set(other_vendors_query.values_list('vendor_id', flat=True)))
        
        # Get vendors sorted by featured status
        vendors = VendorProfile.objects.filter(
            id__in=vendor_ids
        ).select_related('user').order_by(
            '-user__is_featured',  # Featured first
            '-created_at'  # Then by newest
        )
        
        # Pagination
        total_vendors = vendors.count()
        start_idx = (page - 1) * self.VENDORS_PER_PAGE
        end_idx = start_idx + self.VENDORS_PER_PAGE
        paginated_vendors = vendors[start_idx:end_idx]
        
        has_more = end_idx < total_vendors
        
        # Format vendor displays
        recommended_vendors = []
        for vendor in paginated_vendors:
            # Get the product from this vendor
            vendor_product = products.filter(vendor=vendor).first()
            if vendor_product:
                vendor_display = self._format_vendor_display(
                    vendor,
                    vendor_product,
                    is_featured=vendor.user.is_featured
                )
                recommended_vendors.append(vendor_display)
        
        # Generate WhatsApp message
        message = self._generate_recommendation_message(
            dish_name=dish_name,
            preferred_vendor=preferred_vendor,
            found_preferred=found_preferred,
            preferred_vendor_name=preferred_vendor_name,
            recommended_vendors=recommended_vendors,
            current_page=page,
            has_more=has_more,
            total_vendors=total_vendors
        )
        
        return {
            'found_preferred': found_preferred,
            'preferred_vendor': preferred_vendor,
            'recommended_vendors': recommended_vendors,
            'total_vendors': total_vendors,
            'current_page': page,
            'has_more': has_more,
            'message': message
        }
    
    def _format_vendor_display(
        self, 
        vendor: 'VendorProfile', 
        product: 'Product',
        is_preferred: bool = False,
        is_featured: bool = False
    ) -> Dict:
        """
        Format vendor information for display
        
        Returns:
            {
                'vendor_id': int,
                'vendor_name': str,
                'product_id': int,
                'product_name': str,
                'price': Decimal,
                'bio': str,
                'logo_url': str,
                'rating': float,
                'total_reviews': int,
                'is_featured': bool,
                'is_preferred': bool
            }
        """
        # Mock rating for now (replace with actual rating system when available)
        avg_rating = 4.5  # Default rating
        total_reviews = 0  # No review system yet
        
        # Get logo URL
        logo_url = None
        if vendor.logo:
            try:
                logo_url = vendor.logo.url
            except:
                logo_url = None
        
        return {
            'vendor_id': vendor.id,
            'vendor_name': vendor.business_name,
            'product_id': product.id,
            'product_name': product.name,
            'price': product.price,
            'bio': vendor.business_description or "Great food, served fresh!",
            'logo_url': logo_url,
            'rating': round(avg_rating, 1),
            'total_reviews': total_reviews,
            'is_featured': is_featured,
            'is_preferred': is_preferred,
            'business_address': vendor.business_address or "Available for delivery"
        }
    
    def _generate_recommendation_message(
        self,
        dish_name: str,
        preferred_vendor: Optional[Dict],
        found_preferred: bool,
        preferred_vendor_name: Optional[str],
        recommended_vendors: List[Dict],
        current_page: int,
        has_more: bool,
        total_vendors: int
    ) -> str:
        """Generate WhatsApp-formatted recommendation message"""
        
        message = ""
        
        # If preferred vendor found
        if found_preferred and preferred_vendor:
            message += f"✅ *Found at {preferred_vendor_name}!*\n\n"
            message += self._format_single_vendor_display(preferred_vendor)
            message += f"\n\n{'─' * 30}\n\n"
            
            if recommended_vendors:
                message += f"🍽️ *Also available at these trusted vendors:*\n\n"
        
        # If preferred vendor NOT found but specified
        elif preferred_vendor_name and not found_preferred:
            message += f"😕 *{preferred_vendor_name}* doesn't have *{dish_name}* right now.\n\n"
            message += f"✨ *But don't worry! Here are trusted alternatives:*\n\n"
        
        # No preferred vendor specified - show recommendations
        else:
            message += f"🍽️ *{dish_name}* - Available at these vendors:\n\n"
        
        # Display recommended vendors
        for idx, vendor in enumerate(recommended_vendors, start=1):
            # Add featured badge
            featured_badge = "⭐ *FEATURED* " if vendor['is_featured'] else ""
            
            message += f"{featured_badge}*{idx}. {vendor['vendor_name']}*\n"
            message += f"   📍 {vendor['business_address'][:50]}...\n"
            message += f"   💰 ₦{float(vendor['price']):,.0f}\n"
            
            # Rating stars
            rating = vendor['rating']
            stars = self._get_star_rating(rating)
            message += f"   {stars} {rating}/5.0 ({vendor['total_reviews']} reviews)\n"
            
            # Bio (truncated)
            bio = vendor['bio'][:60] + "..." if len(vendor['bio']) > 60 else vendor['bio']
            message += f"   ℹ️ {bio}\n\n"
        
        # Pagination info
        if has_more:
            remaining = total_vendors - (current_page * self.VENDORS_PER_PAGE)
            message += f"━━━━━━━━━━━━━━━━━━\n\n"
            message += f"📊 Showing {current_page * self.VENDORS_PER_PAGE} of {total_vendors} vendors\n\n"
            message += f"💬 Reply:\n"
            message += f"• *NUMBER* (1, 2, 3...) - Select vendor\n"
            message += f"• *MORE* - See {min(remaining, self.VENDORS_PER_PAGE)} more options\n"
        else:
            message += f"━━━━━━━━━━━━━━━━━━\n\n"
            message += f"💬 Reply with a *NUMBER* (1, 2, 3...) to select a vendor"
        
        return message
    
    def _format_single_vendor_display(self, vendor: Dict) -> str:
        """Format single vendor for display"""
        message = f"🏪 *{vendor['vendor_name']}*\n"
        message += f"📍 {vendor['business_address']}\n"
        message += f"💰 {vendor['product_name']} - ₦{float(vendor['price']):,.0f}\n"
        
        # Rating
        stars = self._get_star_rating(vendor['rating'])
        message += f"{stars} {vendor['rating']}/5.0 ({vendor['total_reviews']} reviews)\n"
        
        # Bio
        message += f"\nℹ️ {vendor['bio']}"
        
        return message
    
    def _get_star_rating(self, rating: float) -> str:
        """Convert numeric rating to star emojis"""
        full_stars = int(rating)
        half_star = 1 if (rating - full_stars) >= 0.5 else 0
        empty_stars = 5 - full_stars - half_star
        
        return "⭐" * full_stars + "✨" * half_star + "☆" * empty_stars
    
    def get_featured_vendors_for_dish(self, dish_name: str, limit: int = 5) -> List[Dict]:
        """
        Get only featured vendors for a specific dish
        Used when user doesn't specify vendor name
        """
        from bestyy.core_features.user.models import VendorProfile
        from bestyy.restaurant_features.product.models import Product
        
        products = Product.objects.filter(
            Q(name__icontains=dish_name) | Q(description__icontains=dish_name),
            is_available=True,
            stock_quantity__gt=0,
            vendor__is_suspended=False,
            vendor__verification_status='approved',
            vendor__user__is_featured=True  # Only featured
        ).select_related('vendor', 'vendor__user')
        
        # Get unique vendors (SQLite-compatible)
        seen_vendors = set()
        unique_products = []
        for product in products:
            if product.vendor_id not in seen_vendors:
                seen_vendors.add(product.vendor_id)
                unique_products.append(product)
                if len(unique_products) >= limit:
                    break
        
        products = unique_products
        
        featured_vendors = []
        for product in products:
            vendor_display = self._format_vendor_display(
                product.vendor,
                product,
                is_featured=True
            )
            featured_vendors.append(vendor_display)
        
        return featured_vendors
    
    def cache_search_results(self, conversation_id: str, search_results: Dict):
        """Cache search results for pagination"""
        cache_key = f"vendor_search_{conversation_id}"
        cache.set(cache_key, search_results, timeout=600)  # 10 minutes
    
    def get_cached_search_results(self, conversation_id: str) -> Optional[Dict]:
        """Get cached search results"""
        cache_key = f"vendor_search_{conversation_id}"
        return cache.get(cache_key)
    
    def clear_search_cache(self, conversation_id: str):
        """Clear cached search results"""
        cache_key = f"vendor_search_{conversation_id}"
        cache.delete(cache_key)
