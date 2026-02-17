from django.urls import path, include
from . import views

urlpatterns = [
    # API endpoints for React Admin
    path('api/', include('superAdmin.api_urls')),

    # Admin Authentication
    path('login/', views.admin_login_view, name='admin_login'),
    path('logout/', views.admin_logout_view, name='admin_logout'),
    
    # Admin Dashboard
    path('', views.admin_dashboard, name='admin_dashboard'),
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
    path('products/<int:product_id>/unblock/', views.unblock_product, name='unblock_product'),

    # Delivery Agent Management
    path('delivery-agent-requests/', views.manage_agent_requests, name='manage_agent_requests'),
    path('delivery-agents/', views.manage_agent, name='manage_delivery_agents'),
    path('delivery-agents/<int:agent_id>/', views.agent_detail, name='delivery_agent_detail'),
    path('delivery-agents/<int:agent_id>/approve/', views.approve_agent, name='approve_delivery_agent'),
    path('delivery-agents/<int:agent_id>/reject/', views.reject_agent, name='reject_delivery_agent'),
    path('delivery-agents/<int:agent_id>/block/', views.block_agent, name='block_delivery_agent'),
    path('delivery-agents/<int:agent_id>/unblock/', views.unblock_agent, name='unblock_delivery_agent'),
]