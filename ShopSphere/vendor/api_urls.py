from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    VendorDashboardView, ProductViewSet, VendorProfileViewSet,
    VendorOrdersViewSet, VendorSalesAnalyticsViewSet,
    VendorCommissionViewSet, VendorPaymentViewSet,
    VendorOrderSummaryViewSet
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='vendor-product')
router.register(r'orders', VendorOrdersViewSet, basename='vendor-order')
router.register(r'sales-analytics', VendorSalesAnalyticsViewSet, basename='vendor-analytics')
router.register(r'commissions', VendorCommissionViewSet, basename='vendor-commission')
router.register(r'payments', VendorPaymentViewSet, basename='vendor-payment')
router.register(r'order-summary', VendorOrderSummaryViewSet, basename='vendor-order-summary')
router.register(r'profile', VendorProfileViewSet, basename='vendor-profile')

urlpatterns = [
    # Dashboard
    path('dashboard/', VendorDashboardView.as_view(), name='vendor_dashboard'),
    
    # Routed endpoints
    path('', include(router.urls)),
]