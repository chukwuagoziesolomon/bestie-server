from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Import views
from .api.courier_views import (
    CourierListView,
    CourierDetailView,
    CourierVerificationView,
    CourierRegistrationView,
)
from .admin_dashboard_views import AdminDashboardMetricsView
# Temporarily disabled allauth social views
# from .api.social_views import GoogleLogin, GoogleConnect, GoogleSignup, CompleteProfile
from .api.courier_views import CourierListView, CourierDetailView, CourierVerificationView, CourierRegistrationView
from .api.vendor_views import VendorRegistrationView, VendorProfileView, VendorVerificationStatusView
from .api.admin_views import AdminDashboardMetricsView, PendingVendorsList, VendorVerificationView, VendorStatsView, PendingCouriersList
from .api.user_views import (
    UserRegistrationView, UserLoginView, UserProfileView, 
    ChangePasswordView, LogoutView, UserListView, UserDetailView,
    AdminUserCreateView, AdminUserUpdateView, AdminUserDeleteView,
    CurrentUserView, UserOrdersView, UserOrderDetailView, UserAddressListView, UserAddressDetailView, UserAddressSetDefaultView, UserFavoritesListView, UserFavoritesDetailView, UserFoodFavoritesView, UserVenueFavoritesView, UserAutoFavoriteView, MultiRoleRegistrationView
)
from .cors_test import cors_test
from .api.courier_dashboard_views import (
    dashboard_analytics,
    earnings_chart_data,
    recent_deliveries,
    update_delivery_status
)
from .api.courier_deliveries import CourierDeliveriesView
from .api.courier_payouts import CourierPayoutHistoryView, CourierEarningsBreakdownView
from .api.courier_company_analytics import CourierCompanyAnalyticsView, CourierCompanyPerformanceView
from .api.courier_delivery_activity import CourierDeliveryActivityView, CourierDeliveryTrendsView
from .api.vendor_orders import VendorOrdersView, VendorOrderDetailView
from .api.vendor_menu_views import (
    VendorMenuListView, VendorMenuDetailView, VendorMenuCategoriesView, 
    VendorMenuStatsView, VendorMenuBulkUpdateView
)
from .api.vendor_stock_views import (
    VendorStockListView, VendorStockDetailView, toggle_item_availability,
    bulk_toggle_availability, stock_summary
)
from .api.vendor_transactions import (
    VendorTransactionHistoryView, vendor_transaction_summary,
    vendor_earnings_breakdown, vendor_payment_history, vendor_transaction_analytics,
    vendor_order_activity, vendor_top_dishes
)
from .role_views import AssignRoleView, AvailableRolesView

# Create a router for API endpoints
router = DefaultRouter()

# API endpoints for courier management
courier_urls = [
    path('couriers/register/', CourierRegistrationView.as_view(), name='courier-register'),
    path('couriers/', CourierListView.as_view(), name='courier-list'),
    path('couriers/<int:id>/', CourierDetailView.as_view(), name='courier-detail'),
    path('couriers/<int:id>/verify/', CourierVerificationView.as_view(), name='courier-verify'),
    
    # Courier Dashboard Endpoints
    path('couriers/dashboard/analytics/', dashboard_analytics, name='courier-dashboard-analytics'),
    path('couriers/dashboard/earnings-chart/', earnings_chart_data, name='courier-earnings-chart'),
    path('couriers/dashboard/recent-deliveries/', recent_deliveries, name='courier-recent-deliveries'),
    path('couriers/deliveries/', CourierDeliveriesView.as_view(), name='courier-deliveries-list'),
    path('couriers/deliveries/<int:order_id>/status/', update_delivery_status, name='courier-update-delivery-status'),
    
    # Courier Payout and Earnings Endpoints
    path('couriers/payouts/', CourierPayoutHistoryView.as_view(), name='courier-payout-history'),
    path('couriers/earnings/', CourierEarningsBreakdownView.as_view(), name='courier-earnings-breakdown'),
    
    # Courier Company Analytics Endpoints
    path('couriers/companies/analytics/', CourierCompanyAnalyticsView.as_view(), name='courier-company-analytics'),
    path('couriers/companies/<int:company_id>/performance/', CourierCompanyPerformanceView.as_view(), name='courier-company-performance'),
    
    # Courier Delivery Activity Endpoints
    path('couriers/delivery-activity/', CourierDeliveryActivityView.as_view(), name='courier-delivery-activity'),
    path('couriers/delivery-trends/', CourierDeliveryTrendsView.as_view(), name='courier-delivery-trends'),
]

# Role management endpoints
role_urls = [
    path('roles/assign/', AssignRoleView.as_view(), name='assign-role'),
    path('roles/available/', AvailableRolesView.as_view(), name='available-roles'),
]

# Vendor endpoints
vendor_urls = [
    # Public registration endpoint (no auth required)
    path('vendors/register/', VendorRegistrationView.as_view(), name='vendor-register'),
    # Vendor profile management (requires authentication)
    path('vendors/me/', VendorProfileView.as_view(), name='vendor-profile'),
    # Check verification status
    path('vendors/verification-status/', VendorVerificationStatusView.as_view(), name='vendor-verification-status'),
    # Vendor orders management
    path('vendors/orders/', VendorOrdersView.as_view(), name='vendor-orders'),
    path('vendors/orders/<int:order_id>/', VendorOrderDetailView.as_view(), name='vendor-order-detail'),
    # Vendor menu management
    path('vendors/menu/', VendorMenuListView.as_view(), name='vendor-menu-list'),
    path('vendors/menu/<int:pk>/', VendorMenuDetailView.as_view(), name='vendor-menu-detail'),
    path('vendors/menu/categories/', VendorMenuCategoriesView.as_view(), name='vendor-menu-categories'),
    path('vendors/menu/stats/', VendorMenuStatsView.as_view(), name='vendor-menu-stats'),
    path('vendors/menu/bulk/', VendorMenuBulkUpdateView.as_view(), name='vendor-menu-bulk'),
    
    # Vendor stock management
    path('vendors/stock/', VendorStockListView.as_view(), name='vendor-stock-list'),
    path('vendors/stock/<int:pk>/', VendorStockDetailView.as_view(), name='vendor-stock-detail'),
    path('vendors/stock/<int:item_id>/toggle/', toggle_item_availability, name='vendor-stock-toggle'),
    path('vendors/stock/bulk-toggle/', bulk_toggle_availability, name='vendor-stock-bulk-toggle'),
    path('vendors/stock/summary/', stock_summary, name='vendor-stock-summary'),
    
    # Vendor transaction history
    path('vendors/transactions/', VendorTransactionHistoryView.as_view(), name='vendor-transactions'),
    path('vendors/transactions/summary/', vendor_transaction_summary, name='vendor-transaction-summary'),
    path('vendors/transactions/earnings/', vendor_earnings_breakdown, name='vendor-earnings-breakdown'),
    path('vendors/transactions/payments/', vendor_payment_history, name='vendor-payment-history'),
    path('vendors/transactions/analytics/', vendor_transaction_analytics, name='vendor-transaction-analytics'),
    
    # Vendor dashboard endpoints
    path('vendors/dashboard/order-activity/', vendor_order_activity, name='vendor-order-activity'),
    path('vendors/dashboard/top-dishes/', vendor_top_dishes, name='vendor-top-dishes'),
]

# Admin API endpoints - these will be mounted at /api/admin/
auth_urls = [
    # Standard authentication
    path('login/', UserLoginView.as_view(), name='login'),
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('register/multi-role/', MultiRoleRegistrationView.as_view(), name='multi-role-register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
    
    # OAuth2 Endpoints
    # Temporarily disabled allauth OAuth URLs
    # path('oauth/', include([
    #     # Google OAuth
    #     path('google/', include([
    #         # Initiate OAuth flow (returns auth URL)
    #         path('', GoogleLogin.as_view(), name='google-initiate'),
    #         # OAuth callback (handled by GoogleLogin view with code parameter)
    #         path('callback/', GoogleLogin.as_view(), name='google-callback'),
    #         # Connect existing account with Google
    #         path('connect/', GoogleConnect.as_view(), name='google-connect'),
    #         # Sign up with Google
    #         path('signup/', GoogleSignup.as_view(), name='google-signup'),
    #     ])),
    #     # Complete profile after social signup
    #     path('complete-profile/', CompleteProfile.as_view(), name='complete-profile'),
    # ])),
]

admin_api_urls = [
    # User authentication endpoints
    path('', include(auth_urls)),
    # Vendor management endpoints
    path('vendors/', PendingVendorsList.as_view(), name='admin-vendors-list'),
    path('vendors/pending/', PendingVendorsList.as_view(), name='admin-pending-vendors'),
    path('vendors/<int:vendor_id>/', VendorVerificationView.as_view(), name='admin-vendor-detail'),
    path('vendors/<int:vendor_id>/approve/', VendorVerificationView.as_view(), name='admin-vendor-approve'),
    path('vendors/<int:vendor_id>/reject/', VendorVerificationView.as_view(), name='admin-vendor-reject'),
    
    # Dashboard endpoints
    path('dashboard-metrics/', AdminDashboardMetricsView.as_view(), name='admin-dashboard-metrics'),
    path('vendors/stats/', VendorStatsView.as_view(), name='admin-vendors-stats'),
]

# This makes admin_api_urls importable from user.urls
urlpatterns = [
    # Test endpoints for Cloudinary configuration
    path('test/cloudinary/', views.test_cloudinary, name='test-cloudinary'),
    path('test/menu-image-upload/', views.test_menu_image_upload, name='test-menu-image-upload'),
    path('test/auth/', views.test_auth, name='test-auth'),
    path('test/vendor-auth/', views.test_vendor_auth, name='test-vendor-auth'),
    # CORS test endpoint
    path('cors-test/', cors_test, name='cors-test'),
    # Include role management endpoints
    path('', include(role_urls)),
    # Include courier API endpoints under /api/user/
    path('', include(courier_urls)),
    # Include vendor API endpoints
    path('', include(vendor_urls)),
    # Expose auth endpoints at /api/user/
    path('', include(auth_urls)),
    # User orders endpoints
    path('orders/', UserOrdersView.as_view(), name='user-orders'),
    path('orders/<int:order_id>/', UserOrderDetailView.as_view(), name='user-order-detail'),
    # User address endpoints
    path('addresses/', UserAddressListView.as_view(), name='user-addresses'),
    path('addresses/<int:pk>/', UserAddressDetailView.as_view(), name='user-address-detail'),
    path('addresses/<int:address_id>/set-default/', UserAddressSetDefaultView.as_view(), name='user-address-set-default'),
    # User favorites endpoints
    path('favorites/', UserFavoritesListView.as_view(), name='user-favorites'),
    path('favorites/<int:pk>/', UserFavoritesDetailView.as_view(), name='user-favorite-detail'),
    path('favorites/food/', UserFoodFavoritesView.as_view(), name='user-food-favorites'),
    path('favorites/venues/', UserVenueFavoritesView.as_view(), name='user-venue-favorites'),
    path('favorites/auto/', UserAutoFavoriteView.as_view(), name='user-auto-favorite'),
    # Include admin API endpoints under /api/user/admin/
    path('admin/', include(admin_api_urls)),
    # Courier dashboard endpoints (already included in courier_urls)
]