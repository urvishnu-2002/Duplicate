"""
ShopSphere URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django Admin
    # path('admin/', admin.site.urls),
    
    # API endpoints for each app
    path('', include('user.urls')),
    path('vendor/', include('vendor.urls')),
    path('superAdmin/', include('superAdmin.urls')),
    path('deliveryAgent/', include('deliveryAgent.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
