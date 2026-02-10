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
    # Uncomment these as you enable the apps in settings.py
    # path('api/vendor/', include('vendor.urls')),
    # path('api/delivery/', include('deliveryAgent.urls')),
    # path('api/superadmin/', include('superAdmin.urls')),
    # path('api/shopadmin/', include('admin.urls')),
]

# Serve media files in development
'''if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    path('', include('user.urls')),
    # Admin Dashboard
    #path('', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard_alt'),

    # Vendor Request Management
    path('vendor-requests/', views.manage_vendor_requests, name='manage_vendor_requests'),
    path('vendor-requests/<int:vendor_id>/', views.vendor_request_detail, name='vendor_request_detail'),
    path('vendor-requests/<int:vendor_id>/approve/', views.approve_vendor, name='approve_vendor'),
    path('vendor-requests/<int:vendor_id>/reject/', views.reject_vendor, name='reject_vendor'),

    # Vendor Management
    path('vendors/', views.manage_vendors, name='manage_vendors'),
    path('vendors/<int:vendor_id>/', views.vendor_detail, name='vendor_detail'),
    path('vendors/<int:vendor_id>/block/', views.block_vendor, name='block_vendor'),
    path('vendors/<int:vendor_id>/unblock/', views.unblock_vendor, name='unblock_vendor'),

    # Product Management
    path('products/', views.manage_products, name='manage_products'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('products/<int:product_id>/block/', views.block_product, name='block_product'),
    path('products/<int:product_id>/unblock/', views.unblock_product, name='unblock_product'),'''



urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

