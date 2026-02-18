from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico', permanent=True)),
    path('', include('user.urls')),
    # Django Admin
    path('admin/', admin.site.urls),
    
    # User/Customer URLs (Home, Product browsing, Cart, Orders)
    path('', include('user.urls')),
    
    # Vendor URLs (Vendor registration, products, dashboard)
    path('vendor/', include('vendor.urls')),
    
    # Delivery Agent URLs (Agent registration, portal, orders)
    path('delivery/', include('deliveryAgent.urls')),
    
    # SuperAdmin URLs (Admin panel, approvals, management)
    path('superAdmin/', include('superAdmin.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
