from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    AdminAuthViewSet, AdminDashboardViewSet, AdminUserViewSet, 
    AdminVendorViewSet, AdminReportViewSet, AdminDeliveryViewSet,
    AdminProductViewSet, AdminSystemConfigViewSet, VendorRequestViewSet,
    AdminOrderViewSet
)

router = DefaultRouter()
router.register(r'auth', AdminAuthViewSet, basename='admin-auth')
router.register(r'dashboard', AdminDashboardViewSet, basename='admin-dashboard')
router.register(r'users', AdminUserViewSet, basename='admin-users')
router.register(r'vendors', AdminVendorViewSet, basename='admin-vendors')
router.register(r'vendor-requests', VendorRequestViewSet, basename='admin-vendor-requests')
router.register(r'products', AdminProductViewSet, basename='admin-products')
router.register(r'delivery-agents', AdminDeliveryViewSet, basename='admin-delivery')
router.register(r'reports', AdminReportViewSet, basename='admin-reports')
router.register(r'settings', AdminSystemConfigViewSet, basename='admin-settings')
router.register(r'orders', AdminOrderViewSet, basename='admin-orders')

urlpatterns = [
    path('', include(router.urls)),
]
