from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/whatsapp/', include('whatsapp_ai.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)