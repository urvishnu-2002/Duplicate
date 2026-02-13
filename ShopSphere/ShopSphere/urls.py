"""
ShopSphere URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    # Django Admin
    # path('admin/', admin.site.urls),
    
    # API Schema and Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    path('api/docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # API endpoints for each app
    path('', include('user.urls')),
    # Uncomment these as you enable the apps in settings.py
    path('vendor/', include('vendor.urls')),
    # path('api/delivery/', include('deliveryAgent.urls')),
    # path('api/superadmin/', include('superAdmin.urls')),
    # path('api/shopadmin/', include('admin.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
