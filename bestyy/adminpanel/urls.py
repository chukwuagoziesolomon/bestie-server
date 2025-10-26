from django.urls import path, include
from django.contrib import admin

# Expose Django admin and existing admin API routes under one umbrella
urlpatterns = [
    # Django's admin site (kept at /django-admin/ per existing config)
    path('django-admin/', admin.site.urls),

    # Consolidate existing admin API routes
    path('api/admin/', include('bestyy.core_features.user.admin.urls')),
    path('api/admin/orders/', include('bestyy.restaurant_features.order.urls')),

    # Backward-compat/aliases already present in project-level urls will keep working
]




