"""
Service to automatically update vendor popularity metrics when orders are completed.
Works with existing models only - no separate popularity/rating models.
"""
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta

from bestyy.core_features.user.models import VendorProfile
from bestyy.restaurant_features.order.models import Order


class VendorPopularityUpdateService:
    """
    Service to automatically update vendor popularity metrics.
    Since VendorPopularity and VendorRating models don't exist, we calculate metrics on-demand.
    This should be called when orders are completed.
    """
    
    @staticmethod
    def get_vendor_metrics(vendor):
        """
        Get vendor popularity metrics calculated on-demand.
        Returns a dictionary with all relevant metrics.
        """
        if not vendor:
            return {}
        
        # Calculate total orders
        total_orders = Order.objects.filter(vendor=vendor).count()
        
        # Calculate total revenue
        total_revenue = Order.objects.filter(
            vendor=vendor,
            status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Calculate recent activity (orders in last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_orders = Order.objects.filter(
            vendor=vendor,
            created_at__gte=thirty_days_ago,
            status='completed'
        ).count()
        
        # Calculate orders in last 7 days
        seven_days_ago = timezone.now() - timedelta(days=7)
        orders_last_7_days = Order.objects.filter(
            vendor=vendor,
            created_at__gte=seven_days_ago,
            status='completed'
        ).count()
        
        # Calculate popularity score
        popularity_score = VendorPopularityUpdateService._calculate_popularity_score(
            total_orders,
            total_revenue,
            recent_orders
        )
        
        return {
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'recent_orders': recent_orders,
            'orders_last_7_days': orders_last_7_days,
            'popularity_score': popularity_score,
            'is_featured': getattr(vendor, 'is_featured', False),
            'featured_priority': getattr(vendor, 'featured_priority', 0),
            'verification_status': vendor.verification_status,
            'is_suspended': vendor.is_suspended,
        }
    
    @staticmethod
    def update_vendor_popularity_on_order_completion(order):
        """
        Update vendor popularity metrics when an order is completed.
        Since we don't have a separate popularity model, we just return the current metrics.
        """
        if not order.vendor:
            return None
        
        return VendorPopularityUpdateService.get_vendor_metrics(order.vendor)
    
    @staticmethod
    def _calculate_popularity_score(total_orders, total_revenue, recent_orders):
        """
        Calculate a popularity score based on various metrics.
        Higher score = more popular vendor.
        """
        # Base score from total orders
        order_score = min(total_orders * 0.1, 50)  # Max 50 points from orders
        
        # Revenue score (normalized)
        revenue_score = min(float(total_revenue) / 1000 * 0.1, 30)  # Max 30 points from revenue
        
        # Recent activity bonus
        recent_score = min(recent_orders * 0.5, 20)  # Max 20 points from recent orders
        
        total_score = order_score + revenue_score + recent_score
        return round(total_score, 2)
    
    @staticmethod
    def get_top_vendors_by_metric(metric='popularity_score', limit=10):
        """
        Get top vendors by a specific metric.
        Since we don't have a popularity model, we calculate on-demand.
        """
        vendors = VendorProfile.objects.filter(
            verification_status='approved',
            is_suspended=False
        )
        
        vendor_metrics = []
        for vendor in vendors:
            metrics = VendorPopularityUpdateService.get_vendor_metrics(vendor)
            metrics['vendor'] = vendor
            vendor_metrics.append(metrics)
        
        # Sort by the specified metric
        if metric in ['popularity_score', 'total_orders', 'total_revenue', 'recent_orders']:
            vendor_metrics.sort(key=lambda x: x.get(metric, 0), reverse=True)
        
        return vendor_metrics[:limit]
    
    @staticmethod
    def get_vendors_by_city(city, limit=10):
        """
        Get vendors in a specific city with their metrics.
        """
        vendors = VendorProfile.objects.filter(
            verification_status='approved',
            is_suspended=False,
            business_address__icontains=city
        )
        
        vendor_metrics = []
        for vendor in vendors:
            metrics = VendorPopularityUpdateService.get_vendor_metrics(vendor)
            metrics['vendor'] = vendor
            vendor_metrics.append(metrics)
        
        # Sort by popularity score
        vendor_metrics.sort(key=lambda x: x.get('popularity_score', 0), reverse=True)
        
        return vendor_metrics[:limit]
    
    @staticmethod
    def _extract_city_from_address(address):
        """
        Extract city name from address string.
        This is a simple implementation - in production, you'd use geocoding services.
        """
        if not address:
            return None
        
        # Common Nigerian cities to look for
        nigerian_cities = [
            'Lagos', 'Abuja', 'Kano', 'Ibadan', 'Port Harcourt', 'Benin City',
            'Kaduna', 'Maiduguri', 'Zaria', 'Aba', 'Jos', 'Ilorin', 'Oyo',
            'Enugu', 'Abeokuta', 'Sokoto', 'Onitsha', 'Warri', 'Calabar',
            'Ikot Ekpene', 'Owerri', 'Katsina', 'Akure', 'Bauchi', 'Minna',
            'Makurdi', 'Ado Ekiti', 'Yenagoa', 'Ogbomosho', 'Umuahia',
            'Victoria Island', 'Ikoyi', 'Lekki', 'Surulere', 'Yaba'
        ]
        
        address_lower = address.lower()
        for city in nigerian_cities:
            if city.lower() in address_lower:
                return city
        
        return None