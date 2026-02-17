from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    # We use 'delivery_login' as the primary name to avoid conflicts with 'vendor'
    path('', views.agent_portal, name='delivery_portal'),
    path('login/', views.agent_portal, name='delivery_login'),
    path('register/', views.register_view, name='delivery_register'),
    path('verify-otp/', views.verify_otp_view, name='delivery_verify_otp'),
    path('delivery-details/', views.delivery_details_view, name='delivery_details'),

    # The next_page now points explicitly to 'delivery_login'
    path('logout/', LogoutView.as_view(next_page='delivery_login'), name='delivery_logout'),

    path('dashboard/', views.delivery_dashboard, name='delivery_dashboard'),
    path('delivery/accept-order/<int:order_id>/', views.accept_order, name='accept_order'),
]