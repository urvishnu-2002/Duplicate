from django.contrib import admin
from django.urls import path, include
from vendor import views as vendor_views
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path('', include('user.urls')),
    # Django Admin
    path('admin/', admin.site.urls),
    
    # API endpoints for each app
    path('vendor/', include('vendor.urls')),
    path('superAdmin/', include('superAdmin.urls')),
    path('deliveryAgent/', include('deliveryAgent.urls')),
    path('vendor_register', vendor_views.register_view, name='vendor_register_api'),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
