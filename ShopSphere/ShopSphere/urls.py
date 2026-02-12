"""
ShopSphere URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # User App (Handles root '/')
    path('', include('user.urls')),
    path('admin/', include('admin.urls')),
    
    # Vendor App
    path('vendor/', include('vendor.urls')),
    
    # Super Admin App (Required for 'admin_login' URL)
    # Super Admin App (Required for 'admin_login' URL)
    path('superadmin/', include('superAdmin.urls')),

]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
