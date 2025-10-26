"""
URL configuration for bestyy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework.authtoken.views import obtain_auth_token
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView, TemplateView, View
from django.shortcuts import redirect
from django.urls import reverse_lazy
from urllib.parse import urlparse, parse_qs, urlencode

# Import the view for social login test
from bestyy.core_features.user.views import social_login_test
# Temporarily disabled allauth imports
# from user.api.social_views import GoogleLogin, GoogleSignup, GoogleConnect, CompleteProfile
from django.views.generic import RedirectView

"""
Centralize admin-related routes by delegating to bestyy.adminpanel.urls.
Keeps existing redirects and compatibility paths intact below.
"""


# Import allauth views after admin site is defined (temporarily disabled)
# from allauth.socialaccount.providers.oauth2.views import OAuth2LoginView, OAuth2CallbackView
# from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter

# Temporarily disabled allauth OAuth classes
# class GoogleOAuth2LoginView(OAuth2LoginView):
#     """Custom OAuth2 login view for Google"""
#     adapter_class = GoogleOAuth2Adapter

# class GoogleOAuth2CallbackView(OAuth2CallbackView, View):
#     """Custom OAuth2 callback view for Google"""
#     adapter_class = GoogleOAuth2Adapter
    
#     def get(self, request, *args, **kwargs):
#         # Delegate to the parent class's dispatch method
#         return super().get(request, *args, **kwargs)

# WebSocket URL patterns are imported in asgi.py

urlpatterns = [
    # Consolidated admin endpoints
    path('', include('bestyy.adminpanel.urls')),
    
    # Authentication endpoints (temporarily disabled allauth)
    # path('api/auth/', include('dj_rest_auth.urls')),  # Removed email/password login endpoints
    # path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    
    # Google OAuth URLs (temporarily disabled)
    # path('api/auth/social/google/', GoogleLogin.as_view(), name='google-login'),  # Handle both GET and POST
    # path('api/auth/social/google/callback/', GoogleLogin.as_view(http_method_names=['post']), name='google-callback'),
    # path('api/auth/social/google/signup/', GoogleSignup.as_view(), name='google-signup'),
    # path('api/auth/social/google/connect/', GoogleConnect.as_view(), name='google-connect'),
    # path('api/auth/social/complete-profile/', CompleteProfile.as_view(), name='complete-profile'),
    
    # Django Allauth URLs (temporarily disabled)
    # path('auth/google/login/', GoogleOAuth2LoginView.as_view(), name='google_login'),
    # path('auth/google/callback/', GoogleOAuth2CallbackView.as_view(), name='google_callback'),
    # path('api/auth/social/', include('allauth.socialaccount.urls')),
    path('api/token/', obtain_auth_token, name='api_token_auth'),
    
    # API endpoints
    path('api/user/', include(('bestyy.core_features.user.urls', 'user'), namespace='user')),  # User-related endpoints
    path('api/orders/', include('bestyy.restaurant_features.order.urls')),  # Order-related endpoints
    path('api/whatsapp/', include('bestyy.communication.whatsapp.urls')),  # WhatsApp endpoints (adjusted)
    
    # For backward compatibility with frontend making requests to /api/api/user/
    path('api/api/user/', include('bestyy.core_features.user.urls')),
    
    # For backward compatibility with frontend making requests to /api/api/admin/
    path('api/api/admin/', include('bestyy.core_features.user.admin.urls')),
    
    # Redirect for duplicate /api/ in social auth URL with query parameters
    path('api/api/auth/social/google/', lambda request: redirect(f"/api/auth/social/google/{'?' + request.META.get('QUERY_STRING', '') if request.META.get('QUERY_STRING') else ''}")),
    
    # Frontend compatibility - keep legacy includes/redirects
    path('api/user/admin/', include('bestyy.core_features.user.admin.urls')),
    path('admin/', include('bestyy.core_features.user.admin.urls')),

    # Redirect WebSocket-like URLs to HTTP endpoints for compatibility
    path('ws/admin/activity/', RedirectView.as_view(url='/admin/activity/', permanent=False)),
    # Analytics routes
    path('api/', include('bestyy.payment_analytics.analytics.urls')),
    # Vendor dashboard analytics routes
    path('api/user/dashboard/analytics/', RedirectView.as_view(url='/api/dashboard/analytics/', permanent=False)),
    path('api/user/vendors/sales-chart/', RedirectView.as_view(url='/api/vendor/sales-chart/', permanent=False)),
    
    # Social login test page
    path('social-login-test/', social_login_test, name='social-login-test'),
    
    # Redirects for old URLs to new API paths
    path('user/admin/metrics/pending-verification/', 
         RedirectView.as_view(url=reverse_lazy('pending-verification-metric'), permanent=True)),
    path('user/admin/metrics/revenue/', 
         RedirectView.as_view(url=reverse_lazy('total-revenue-metric'), permanent=True)),
    path('user/admin/metrics/orders/', 
         RedirectView.as_view(url=reverse_lazy('total-orders-metric'), permanent=True)),
    path('user/admin/verification/pending/', 
         RedirectView.as_view(url=reverse_lazy('pending-verifications'), permanent=True)),
    
    # Redirect for frontend compatibility (temporary)
    path('user/orders/', RedirectView.as_view(url='/api/user/orders/', permanent=False)),
    path('user/me/', RedirectView.as_view(url='/api/user/me/', permanent=False)),
    path('user/login/', RedirectView.as_view(url='/api/user/login/', permanent=False)),
    path('user/addresses/', RedirectView.as_view(url='/api/user/addresses/', permanent=False)),
    path('user/favorites/', RedirectView.as_view(url='/api/user/favorites/', permanent=False)),
    
    # Courier dashboard redirects for frontend compatibility
    path('user/couriers/dashboard/analytics/', RedirectView.as_view(url='/api/user/couriers/dashboard/analytics/', permanent=False)),
    path('user/couriers/dashboard/earnings-chart/', RedirectView.as_view(url='/api/user/couriers/dashboard/earnings-chart/', permanent=False)),
    path('user/couriers/dashboard/recent-deliveries/', RedirectView.as_view(url='/api/user/couriers/dashboard/recent-deliveries/', permanent=False)),
    path('user/couriers/deliveries/', RedirectView.as_view(url='/api/user/couriers/deliveries/', permanent=False)),
    
    # Additional courier endpoint redirects
    path('user/couriers/register/', RedirectView.as_view(url='/api/user/couriers/register/', permanent=False)),
    path('user/couriers/me/', RedirectView.as_view(url='/api/user/couriers/me/', permanent=False)),
    
    # Courier payout and earnings redirects for frontend compatibility
    path('user/couriers/payouts/', RedirectView.as_view(url='/api/user/couriers/payouts/', permanent=False)),
    path('user/couriers/earnings/', RedirectView.as_view(url='/api/user/couriers/earnings/', permanent=False)),
    
    # Courier company analytics redirects for frontend compatibility
    path('user/couriers/companies/analytics/', RedirectView.as_view(url='/api/user/couriers/companies/analytics/', permanent=False)),
    path('user/couriers/companies/<int:company_id>/performance/', RedirectView.as_view(url='/api/user/couriers/companies/<int:company_id>/performance/', permanent=False)),
    
    # Courier delivery activity redirects for frontend compatibility
    path('user/couriers/delivery-activity/', RedirectView.as_view(url='/api/user/couriers/delivery-activity/', permanent=False)),
    path('user/couriers/delivery-trends/', RedirectView.as_view(url='/api/user/couriers/delivery-trends/', permanent=False)),
    
    # Vendor sales chart redirects for frontend compatibility
    path('user/vendors/sales-chart/', RedirectView.as_view(url='/api/vendor/sales-chart/', permanent=False)),
    
    # Vendor dashboard analytics redirects for frontend compatibility
    path('user/dashboard/analytics/', RedirectView.as_view(url='/api/dashboard/analytics/', permanent=False)),
    
    # Vendor orders redirects for frontend compatibility
    path('user/vendors/orders/', RedirectView.as_view(url='/api/user/vendors/orders/', permanent=False)),
    path('user/vendors/orders/<int:order_id>/', RedirectView.as_view(url='/api/user/vendors/orders/<int:order_id>/', permanent=False)),
    
    # Vendor menu redirects for frontend compatibility
    path('user/vendors/menu/', RedirectView.as_view(url='/api/user/vendors/menu/', permanent=False)),
    path('user/vendors/menu/<int:pk>/', RedirectView.as_view(url='/api/user/vendors/menu/<int:pk>/', permanent=False)),
    path('user/vendors/menu/categories/', RedirectView.as_view(url='/api/user/vendors/menu/categories/', permanent=False)),
    path('user/vendors/menu/stats/', RedirectView.as_view(url='/api/user/vendors/menu/stats/', permanent=False)),
    path('user/vendors/menu/bulk/', RedirectView.as_view(url='/api/user/vendors/menu/bulk/', permanent=False)),
    
    # Vendor stock management redirects for frontend compatibility
    path('user/vendors/stock/', RedirectView.as_view(url='/api/user/vendors/stock/', permanent=False)),
    path('user/vendors/stock/<int:pk>/', RedirectView.as_view(url='/api/user/vendors/stock/<int:pk>/', permanent=False)),
    path('user/vendors/stock/<int:item_id>/toggle/', RedirectView.as_view(url='/api/user/vendors/stock/<int:item_id>/toggle/', permanent=False)),
    path('user/vendors/stock/bulk-toggle/', RedirectView.as_view(url='/api/user/vendors/stock/bulk-toggle/', permanent=False)),
    path('user/vendors/stock/summary/', RedirectView.as_view(url='/api/user/vendors/stock/summary/', permanent=False)),
    
    # Vendor transaction history redirects for frontend compatibility
    path('user/vendors/transactions/', RedirectView.as_view(url='/api/user/vendors/transactions/', permanent=False)),
    path('user/vendors/transactions/summary/', RedirectView.as_view(url='/api/user/vendors/transactions/summary/', permanent=False)),
    path('user/vendors/transactions/earnings/', RedirectView.as_view(url='/api/user/vendors/transactions/earnings/', permanent=False)),
    path('user/vendors/transactions/payments/', RedirectView.as_view(url='/api/user/vendors/transactions/payments/', permanent=False)),
    path('user/vendors/transactions/analytics/', RedirectView.as_view(url='/api/user/vendors/transactions/analytics/', permanent=False)),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# WebSocket URL patterns are now defined in user/routing.py and imported in asgi.py
