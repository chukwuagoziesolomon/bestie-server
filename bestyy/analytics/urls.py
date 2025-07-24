from django.urls import path
from .views import DashboardAnalyticsView, VendorTransactionHistoryView

urlpatterns = [
    path('dashboard/analytics/', DashboardAnalyticsView.as_view(), name='dashboard-analytics'),
    path('vendor/transactions/', VendorTransactionHistoryView.as_view(), name='vendor-transaction-history'),
] 