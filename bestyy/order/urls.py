"""
URLs for the order app.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'order'

router = DefaultRouter()
# No viewset-based routes for now

urlpatterns = [
    # Admin order management
    path('admin/orders/', views.AdminOrderListView.as_view(), name='admin-order-list'),
    path('admin/orders/<uuid:id>/', views.AdminOrderDetailView.as_view(), name='admin-order-detail'),
    path('admin/orders/<uuid:id>/status/', views.AdminOrderStatusUpdateView.as_view(), name='admin-order-status-update'),
    path('admin/orders/stats/', views.OrderStatsView.as_view(), name='order-stats'),
]
