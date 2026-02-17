from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    DeliveryAgentDashboardView, DeliveryAssignmentViewSet,
    DeliveryTrackingViewSet, DeliveryEarningsViewSet,
    DeliveryPaymentViewSet, DeliveryDailyStatsViewSet,
    DeliveryFeedbackViewSet
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'assignments', DeliveryAssignmentViewSet, basename='delivery-assignment')
router.register(r'tracking', DeliveryTrackingViewSet, basename='delivery-tracking')
router.register(r'earnings', DeliveryEarningsViewSet, basename='delivery-earnings')
router.register(r'payments', DeliveryPaymentViewSet, basename='delivery-payment')
router.register(r'daily-stats', DeliveryDailyStatsViewSet, basename='delivery-stats')
router.register(r'feedback', DeliveryFeedbackViewSet, basename='delivery-feedback')

urlpatterns = [
    # Dashboard
    path('dashboard/', DeliveryAgentDashboardView.as_view(), name='delivery_dashboard'),
    
    # Routed endpoints
    path('', include(router.urls)),
]
