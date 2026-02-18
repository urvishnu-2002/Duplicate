from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    # Delivery Agent Authentication
    path('', views.agent_portal, name='delivery_portal'),
    path('login/', views.agent_portal, name='delivery_login'),
    path('register/', views.register_view, name='delivery_register'),
    path('verify-otp/', views.verify_otp_view, name='delivery_verify_otp'),
    path('logout/', LogoutView.as_view(next_page='delivery_login'), name='delivery_logout'),
    
    # Delivery Agent Profile & Details
    path('details/', views.delivery_details_view, name='delivery_details'),
    
    # Delivery Agent Dashboard & Orders
    path('dashboard/', views.delivery_dashboard, name='delivery_dashboard'),
    path('accept-order/<int:order_id>/', views.accept_order, name='accept_order'),
]