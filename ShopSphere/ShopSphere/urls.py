from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
<<<<<<< HEAD
    # User App (Handles root '/')
    path('', include('user.urls')),
    path('admin/', include('admin.urls')),
    
    # Vendor App
    path('vendor/', include('vendor.urls')),
    
    # Super Admin App (Required for 'admin_login' URL)
    # Super Admin App (Required for 'admin_login' URL)
    path('superadmin/', include('superAdmin.urls')),

=======
    path('', include('user.urls')),
    # Django Admin
    path('admin/', admin.site.urls),
    
    # API endpoints for each app
    path('vendor/', include('vendor.urls')),
    path('superAdmin/', include('superAdmin.urls')),
    path('deliveryAgent/', include('deliveryAgent.urls')),
>>>>>>> 039501b31bd951b814ae952af8abc44f806c2f41
]

# Serve media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
<<<<<<< HEAD
=======
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
>>>>>>> 039501b31bd951b814ae952af8abc44f806c2f41
