"""
Admin API URL configuration for the user app.
"""
from django.urls import path, include
from bestyy.core_features.user.api.admin_views import (
    PendingVendorsList,
    VendorVerificationView,
    VendorStatsView,
    PendingCouriersList,
    PendingVerificationsView,
    PendingVerificationSummaryView,
    AdminUsersList,
    RegularUsersCountView,
    CourierVerificationView,
    UnifiedVerificationView,
    AllPendingVerificationsView,
)
from bestyy.core_features.user.api.user_views import UserDetailView
from bestyy.payment_analytics.analytics.views import RecentActivityView
from bestyy.core_features.user.api.admin_order_views import AdminOrderListView, OrderStatsView
from bestyy.core_features.user.api.admin_setup_views import create_admin_user, check_admin_exists
from bestyy.core_features.user.api.cloudinary_test_views import test_cloudinary_config, test_cloudinary_upload
from bestyy.core_features.user.api.admin_revenue_views import AdminRevenueAnalyticsView, AdminRevenueChartView
from bestyy.core_features.user.admin.views.dashboard_stats import (
    AdminDashboardStatsView,
    AdminRevenueBreakdownView,
)
from bestyy.core_features.user.api.admin_user_management import UserSuspensionView, SuspendedUsersListView
from bestyy.core_features.user.api.admin_auth_views import AdminLoginView, AdminLogoutView

urlpatterns = [
    # Admin authentication
    path('login/', AdminLoginView.as_view(), name='admin-login'),
    path('logout/', AdminLogoutView.as_view(), name='admin-logout'),
    
    # Vendor management endpoints
    path('vendors/', PendingVendorsList.as_view(), name='admin-vendors-list'),
    path('vendors/pending/', PendingVendorsList.as_view(), name='admin-pending-vendors'),
    path('vendors/<int:vendor_id>/', VendorVerificationView.as_view(), name='admin-vendor-detail'),
    path('vendors/<int:vendor_id>/approve/', VendorVerificationView.as_view(), name='admin-vendor-approve'),
    path('vendors/<int:vendor_id>/reject/', VendorVerificationView.as_view(), name='admin-vendor-reject'),

    # Courier management endpoints
    path('couriers/pending/', PendingCouriersList.as_view(), name='admin-pending-couriers'),
    path('couriers/<int:courier_id>/', CourierVerificationView.as_view(), name='admin-courier-detail'),
    path('couriers/<int:courier_id>/approve/', CourierVerificationView.as_view(), name='admin-courier-approve'),
    path('couriers/<int:courier_id>/reject/', CourierVerificationView.as_view(), name='admin-courier-reject'),

    # NEW: Single endpoint for all pending verifications (recommended) - MUST come first
    path('verification/all-pending/', AllPendingVerificationsView.as_view(), name='admin-all-pending-verifications'),
    
    # Unified verification endpoint for backward/explicit usage
    path('verification/pending/', PendingVerificationsView.as_view(), name='admin-pending-verifications'),
    path('verification/summary/', PendingVerificationSummaryView.as_view(), name='admin-verification-summary'),
    path('verification/courier/<int:courier_id>/', CourierVerificationView.as_view(), name='admin-verification-courier'),
    
    # Unified verification endpoints (recommended)
    path('verification/<str:verification_type>/<int:verification_id>/', UnifiedVerificationView.as_view(), name='admin-unified-verification'),
    path('verification/<str:verification_type>/<int:verification_id>/approve/', UnifiedVerificationView.as_view(), name='admin-unified-approve'),
    path('verification/<str:verification_type>/<int:verification_id>/reject/', UnifiedVerificationView.as_view(), name='admin-unified-reject'),

    # Regular users tracking
    path('users/', AdminUsersList.as_view(), name='admin-users-list'),
    path('users/<int:user_id>/', UserDetailView.as_view(), name='admin-user-detail'),
    path('users/count/', RegularUsersCountView.as_view(), name='admin-regular-users-count'),
    
    # Activity feed endpoints
    path('activities/recent/', RecentActivityView.as_view(), name='admin-recent-activities'),
    path('activity/', RecentActivityView.as_view(), name='admin-activity'),
    
    # Revenue analytics endpoints
    path('revenue/analytics/', AdminRevenueAnalyticsView.as_view(), name='admin-revenue-analytics'),
    path('revenue/chart/', AdminRevenueChartView.as_view(), name='admin-revenue-chart'),
    path('revenue/breakdown/', AdminRevenueBreakdownView.as_view(), name='admin-revenue-breakdown'),
    
    # Dashboard KPI endpoints
    path('dashboard/stats/', AdminDashboardStatsView.as_view(), name='admin-dashboard-stats'),
    # Top vendors and order activity endpoints not yet implemented in new module
    
    # User management endpoints
    path('users/<str:user_type>/<int:user_id>/suspend/', UserSuspensionView.as_view(), name='admin-user-suspend'),
    path('users/<str:user_type>/<int:user_id>/activate/', UserSuspensionView.as_view(), name='admin-user-activate'),
    path('users/<str:user_type>/<int:user_id>/status/', UserSuspensionView.as_view(), name='admin-user-status'),
    path('users/suspended/', SuspendedUsersListView.as_view(), name='admin-suspended-users'),
    
    # Regular user suspension endpoints (for users without vendor/courier profiles)
    path('users/<int:user_id>/suspend/', UserSuspensionView.as_view(), name='admin-regular-user-suspend'),
    path('users/<int:user_id>/activate/', UserSuspensionView.as_view(), name='admin-regular-user-activate'),
    path('users/<int:user_id>/status/', UserSuspensionView.as_view(), name='admin-regular-user-status'),
    
    # Dashboard endpoints
    path('dashboard-metrics/', VendorStatsView.as_view(), name='admin-dashboard-metrics'),
    path('vendors/stats/', VendorStatsView.as_view(), name='admin-vendors-stats'),
    
    # Order management endpoints
    path('orders/', AdminOrderListView.as_view(), name='admin-orders-list'),
    path('orders/stats/', OrderStatsView.as_view(), name='admin-orders-stats'),

    # Activity and analytics
    path('', include('bestyy.payment_analytics.analytics.urls')),
    
    # Admin setup endpoints (one-time use)
    path('setup/create-admin/', create_admin_user, name='admin-create-admin'),
]