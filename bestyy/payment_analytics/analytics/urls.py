from django.urls import path
from .views import DashboardAnalyticsView, VendorTransactionHistoryView, RecentActivityView, ActivityWebhookView
from .vendor_sales_chart import VendorSalesChartView

urlpatterns = [
    path('dashboard/analytics/', DashboardAnalyticsView.as_view(), name='dashboard-analytics'),
    path('vendor/transactions/', VendorTransactionHistoryView.as_view(), name='vendor-transaction-history'),
    path('vendor/sales-chart/', VendorSalesChartView.as_view(), name='vendor-sales-chart'),
    path('admin/recent-activity/', RecentActivityView.as_view(), name='recent-activity'),
    path('webhook/activity/', ActivityWebhookView.as_view(), name='activity-webhook'),
] 