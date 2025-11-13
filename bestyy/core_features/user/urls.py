"""
URL configuration for user app
"""
from django.urls import path, include
from .api import (
    user_views, order_views, vendor_search_views, personalized_recommendations,
    vendor_orders, vendor_stock_views, vendor_reply_views, paystack_views,
    food_customization_views, featured_vendor_admin, crypto_payment_views,
    courier_deliveries, courier_dashboard_views, admin_views, admin_order_views,
    admin_user_management, banner_views, unified_recommendation_view,
    unified_search_view, smart_recommendations, vendor_menu_views, vendor_transactions,
    vendor_profile_views, location_services, order_summary, google_places_proxy
)
from .api.user_subscription_views import (
    paystack_webhook, verify_subscription_payment, user_subscription_status,
    initialize_subscription_payment, subscription_success_page
)
from .api import verification_views

app_name = 'user'

urlpatterns = [
    # Authentication
    path('login/', user_views.UserLoginView.as_view(), name='user_login'),
    
    # User management
    path('me/', user_views.UserProfileView.as_view(), name='user_me'),
    path('profile/', user_views.UserProfileView.as_view(), name='user_profile'),
    path('profile/info/', user_views.UserProfileInfoView.as_view(), name='user_profile_info'),

    # Health check for monitoring
    path('health/', user_views.HealthCheckView.as_view(), name='health_check'),
    path('register/multi-role/', user_views.MultiRoleRegistrationView.as_view(), name='multi_role_register'),
    path('addresses/', user_views.UserAddressListView.as_view(), name='user_addresses'),
    path('addresses/<int:pk>/', user_views.UserAddressDetailView.as_view(), name='user_address_detail'),
    path('favorites/', user_views.UserFavoritesListView.as_view(), name='user_favorites'),
    path('favorites/food/', user_views.UserFoodFavoritesView.as_view(), name='user_food_favorites'),
    path('favorites/venue/', user_views.UserVenueFavoritesView.as_view(), name='user_venue_favorites'),

    # Orders
    path('orders/', order_views.UnifiedCheckoutView.as_view(), name='order_list_create'),
    path('orders/<uuid:pk>/confirmation/', order_views.OrderConfirmationView.as_view(), name='order_confirmation'),
    path('orders/<uuid:pk>/status/', order_views.OrderStatusView.as_view(), name='order_status_update'),
    path('orders/<uuid:pk>/receipt/', order_views.OrderReceiptView.as_view(), name='order_receipt'),
    path('orders/<uuid:pk>/payment-status/', order_views.OrderPaymentStatusView.as_view(), name='order_payment_status'),
    path('orders/<uuid:pk>/modify/', order_views.OrderSummaryView.as_view(), name='order_modify'),

    # Cart management
    path('cart/', food_customization_views.CartView.as_view(), name='cart'),
    path('cart/add/', food_customization_views.AddToCartView.as_view(), name='cart_add'),

    # Vendor search and recommendations
    path('vendors/search/', vendor_search_views.VendorSearchView.as_view(), name='vendor_search'),
    path('vendors/<int:vendor_id>/profile/', vendor_profile_views.VendorProfileDetailView.as_view(), name='vendor_profile'),
    path('vendors/<int:vendor_id>/menu/', vendor_menu_views.VendorMenuItemsView.as_view(), name='vendor_menu'),
    # path('vendors/featured/', vendor_search_views.FeaturedVendorsView.as_view(), name='featured_vendors'),
    path('recommendations/', unified_recommendation_view.UnifiedVendorRecommendationView.as_view(), name='vendor_recommendations'),

    # Smart recommendations (NEW)
    path('smart-recommendations/', smart_recommendations.SmartItemRecommendationsView.as_view(), name='smart_recommendations'),
    path('items/search/', smart_recommendations.VendorItemSearchView.as_view(), name='item_search'),
    path('items/similar/', smart_recommendations.SimilarItemsView.as_view(), name='similar_items'),

    # Unified search and recommendations - disabled
    # path('unified/search/', unified_search_view.UnifiedSearchView.as_view(), name='unified_search'),
    # path('unified/recommendations/', unified_recommendation_view.UnifiedRecommendationView.as_view(), name='unified_recommendations'),

    # Vendor management (for vendors)
    path('vendors/orders/', vendor_orders.VendorOrdersView.as_view(), name='vendor_orders'),
    path('vendors/menu/', vendor_menu_views.VendorMenuListView.as_view(), name='vendor_menu'),
    path('vendors/me/', user_views.UserProfileView.as_view(), name='vendor_me'),
    path('vendors/stock/', vendor_stock_views.VendorStockListView.as_view(), name='vendor_stock'),
    path('vendors/stock/<int:pk>/', vendor_stock_views.VendorStockDetailView.as_view(), name='vendor_stock_detail'),
    path('vendors/stock/<int:item_id>/toggle/', vendor_stock_views.toggle_item_availability, name='vendor_stock_toggle'),
    path('vendors/stock/bulk-toggle/', vendor_stock_views.bulk_toggle_availability, name='vendor_stock_bulk_toggle'),
    path('vendors/stock/summary/', vendor_stock_views.stock_summary, name='vendor_stock_summary'),
    path('vendors/orders/<int:pk>/', vendor_orders.VendorOrderDetailView.as_view(), name='vendor_order_detail'),
    path('vendors/replies/', vendor_reply_views.VendorReplyManagementView.as_view(), name='vendor_replies'),
    path('vendors/transactions/', vendor_transactions.VendorTransactionHistoryView.as_view(), name='vendor_transactions'),
    path('vendors/transactions/summary/', vendor_transactions.vendor_transaction_summary, name='vendor_transaction_summary'),
    path('vendors/transactions/earnings/', vendor_transactions.vendor_earnings_breakdown, name='vendor_earnings'),
    path('vendors/transactions/payments/', vendor_transactions.vendor_payment_history, name='vendor_payments'),
    path('vendors/transactions/analytics/', vendor_transactions.vendor_transaction_analytics, name='vendor_transaction_analytics'),
    path('vendors/dashboard/top-dishes/', vendor_transactions.vendor_top_dishes, name='vendor_top_dishes'),
    path('vendors/dashboard/order-activity/', vendor_transactions.vendor_order_activity, name='vendor_order_activity'),

    # Payment - using function-based views that exist
    path('payments/paystack/webhook/', paystack_views.create_dedicated_account, name='paystack_webhook'),
    path('payments/paystack/initialize/', paystack_views.get_dedicated_account, name='paystack_initialize'),
    path('payments/paystack/verify/<str:reference>/', paystack_views.requery_account, name='paystack_verify'),
    path('payments/crypto/', crypto_payment_views.CryptoPaymentListView.as_view(), name='crypto_payment'),

    # Food customization
    path('food-customization/', food_customization_views.MenuItemCustomizationView.as_view(), name='food_customization'),

    # Order summary with delivery calculation
    path('order-summary/', order_summary.OrderSummaryView.as_view(), name='order_summary'),

    # Courier management
    path('courier/deliveries/', courier_deliveries.CourierDeliveriesView.as_view(), name='courier_deliveries'),
    path('courier/deliveries/<int:pk>/', courier_deliveries.CourierDeliveriesView.as_view(), name='courier_delivery_detail'),
    path('courier/dashboard/', courier_dashboard_views.dashboard_analytics, name='courier_dashboard'),

    # Admin management
    path('admin/vendors/', admin_views.PendingVendorsList.as_view(), name='admin_vendors'),
    path('admin/vendors/<int:pk>/', admin_views.VendorVerificationView.as_view(), name='admin_vendor_detail'),
    path('admin/couriers/', admin_views.PendingCouriersList.as_view(), name='admin_couriers'),
    path('admin/couriers/<int:pk>/', admin_views.CourierVerificationView.as_view(), name='admin_courier_detail'),
    path('admin/orders/', admin_order_views.AdminOrderListView.as_view(), name='admin_orders'),
    path('admin/orders/<int:pk>/', admin_order_views.AdminOrderListView.as_view(), name='admin_order_detail'),
    path('admin/users/', admin_user_management.SuspendedUsersListView.as_view(), name='admin_users'),
    path('admin/featured-vendors/', featured_vendor_admin.FeaturedVendorListView.as_view(), name='admin_featured_vendors'),

    # Banners
    path('banners/', banner_views.BannerListView.as_view(), name='banners'),
    path('banners/<int:pk>/', banner_views.BannerDetailView.as_view(), name='banner_detail'),

    # Verification endpoints
    path('verification/supported-banks/', verification_views.get_supported_banks, name='supported_banks'),

    # Location services
    path('location/geocode/', location_services.AddressGeocodeView.as_view(), name='location_geocode'),
    path('location/suggestions/', location_services.AddressSuggestionsView.as_view(), name='location_suggestions'),
    path('location/validate-delivery/', location_services.DeliveryValidationView.as_view(), name='validate_delivery'),
    path('location/distance/', location_services.DistanceCalculationView.as_view(), name='location_distance'),
    path('location/status/', location_services.LocationServiceStatusView.as_view(), name='location_status'),

    # Google Places proxy (for frontend autocomplete to avoid CORS)
    path('google-places/autocomplete/', google_places_proxy.GooglePlacesProxyView.as_view(), name='google_places_autocomplete'),
    path('google-places/details/', google_places_proxy.GooglePlacesDetailsProxyView.as_view(), name='google_places_details'),

    # User subscription endpoints
    path('subscription/status/', user_subscription_status, name='user_subscription_status'),
    path('subscription/initialize/', initialize_subscription_payment, name='initialize_subscription'),
    path('subscription/verify/', verify_subscription_payment, name='verify_subscription'),
    path('subscription/success/', subscription_success_page, name='subscription_success'),

    # Webhook endpoints
    path('webhooks/paystack/', paystack_webhook, name='paystack_webhook'),
    # path('webhooks/', include('bestyy.core_features.user.api.webhook_views')),
]