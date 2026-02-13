from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    
    path('', views.agent_portal, name='agentPortal'),
    path('login/', views.agent_portal, name='agentLogin'),
    path('register/', views.agent_portal, name='agentRegister'),

    
    path('logout/', LogoutView.as_view(next_page='agentPortal'), name='logout'),

    
    path('delivery/dashboard/', views.delivery_dashboard, name='delivery_dashboard'),

    
    path('delivery/accept-order/<int:order_id>/', views.accept_order, name='accept_order'),

    
    path('accept-order/<int:order_id>/', views.accept_order_sim, name='accept_order_sim'),
]