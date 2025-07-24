from django.urls import path
from .views import (
    VendorSignupView, CourierSignupView, UserSignupView, 
    UserOrderListView, UserOrderCreateView, EmailLoginView, LogoutView, 
    UserProfileView, UserBookingListView, UserBookingCreateView, 
    UserAddressListView, UserAddressCreateView, UserAddressUpdateView, 
    UserAddressDeleteView, UserFavoriteListView, UserFavoriteCreateView, 
    UserFavoriteDeleteView, PaymentCreateView, PaymentListView, 
    SavedCardListView, SavedCardCreateView, SavedCardDeleteView, 
    PaystackWebhookView, UserProfileUpdateView, 
    OrderReceiptConfirmationView, VendorOrderManagementView,
    MenuItemListCreateView, MenuItemRetrieveUpdateDestroyView,
    VendorOrderTrackingView, MenuItemCreateView
)

urlpatterns = [
    # Account Creation for different roles
    path('signup/vendor/', VendorSignupView.as_view(), name='vendor-signup'),
    path('signup/courier/', CourierSignupView.as_view(), name='courier-signup'),
    path('signup/user/', UserSignupView.as_view(), name='user-signup'),
    
    # Authentication
    path('login/', EmailLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='user-profile-update'),
    
    # Menu Item Management (for Vendors)
    path('vendor/menu-items/', MenuItemListCreateView.as_view(), name='vendor-menu-item-list-create'),
    path('vendor/menu-items/create/', MenuItemCreateView.as_view(), name='vendor-menu-item-create'),
    path('vendor/menu-items/<int:pk>/', MenuItemRetrieveUpdateDestroyView.as_view(), name='vendor-menu-item-detail'),
    
    # User data endpoints
    path('orders/user/', UserOrderListView.as_view(), name='user-order-list'),
    path('orders/user/create/', UserOrderCreateView.as_view(), name='user-order-create'),
    path('orders/user/<int:order_id>/confirm-receipt/', OrderReceiptConfirmationView.as_view(), name='order-receipt-confirmation'),
    path('orders/vendor/<int:order_id>/<str:action>/', VendorOrderManagementView.as_view(), name='vendor-order-management'),
    path('orders/vendor/tracking/', VendorOrderTrackingView.as_view(), name='vendor-order-tracking'),
    path('bookings/user/', UserBookingListView.as_view(), name='user-booking-list'),
    path('bookings/user/create/', UserBookingCreateView.as_view(), name='user-booking-create'),
    path('addresses/user/', UserAddressListView.as_view(), name='user-address-list'),
    path('addresses/user/create/', UserAddressCreateView.as_view(), name='user-address-create'),
    path('addresses/user/<int:pk>/update/', UserAddressUpdateView.as_view(), name='user-address-update'),
    path('addresses/user/<int:pk>/delete/', UserAddressDeleteView.as_view(), name='user-address-delete'),
    path('favorites/user/', UserFavoriteListView.as_view(), name='user-favorite-list'),
    path('favorites/user/create/', UserFavoriteCreateView.as_view(), name='user-favorite-create'),
    path('favorites/user/<int:pk>/delete/', UserFavoriteDeleteView.as_view(), name='user-favorite-delete'),
    path('payments/user/', PaymentListView.as_view(), name='user-payment-list'),
    path('payments/user/create/', PaymentCreateView.as_view(), name='user-payment-create'),
    path('cards/user/', SavedCardListView.as_view(), name='user-card-list'),
    path('cards/user/create/', SavedCardCreateView.as_view(), name='user-card-create'),
    path('cards/user/<int:pk>/delete/', SavedCardDeleteView.as_view(), name='user-card-delete'),
    path('paystack/webhook/', PaystackWebhookView.as_view(), name='paystack-webhook'),
] 