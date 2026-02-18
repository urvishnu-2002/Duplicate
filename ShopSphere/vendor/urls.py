from django.urls import path
from . import views

urlpatterns = [
    # Vendor Authentication
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='vendor_login'),
    path('register/', views.register_view, name='register'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('logout/', views.logout_view, name='logout'),
    
    # Vendor Profile & Status
    path('details/', views.vendor_details_view, name='vendor_details'),
    path('approval-status/', views.approval_status_view, name='approval_status'),
    
    # Binary Data Serving
    path('serve-image/<int:image_id>/', views.serve_product_image, name='serve_product_image'),
    path('serve-doc/<int:profile_id>/<str:doc_type>/', views.serve_vendor_document, name='serve_vendor_document'),
    # Vendor Dashboard
    path('dashboard/', views.vendor_home_view, name='vendor_home'),
    
    # Product Management
    path('products/add/', views.add_product_view, name='add_product'),
    path('products/<int:product_id>/', views.view_product_view, name='view_product'),
    path('products/<int:product_id>/edit/', views.edit_product_view, name='edit_product'),
    path('products/<int:product_id>/delete/', views.delete_product_view, name='delete_product'),
]