from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    # We use 'delivery_login' as the primary name to avoid conflicts with 'vendor'
    path('', views.agent_portal, name='delivery_portal'),
    path('login/', views.agent_portal, name='delivery_login'),
    path('register/', views.agent_portal, name='delivery_register'),

    # The next_page now points explicitly to 'delivery_login'
    path('logout/', LogoutView.as_view(next_page='delivery_login'), name='delivery_logout'),

    path('dashboard/', views.delivery_dashboard, name='delivery_dashboard'),
    path('delivery/accept-order/<int:order_id>/', views.accept_order, name='accept_order'),
]