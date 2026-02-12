from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [
    # Redirect root URL to home page
    path('', lambda request: redirect('home'), name='index'),
    
    path('login', views.login_api, name='login'),
    path('register', views.register_api, name='register'),
    path('home', views.home_api, name='home'),
    path('logout', views.logout_api, name='logout'),
    path('add_to_cart/<int:product_id>', views.add_to_cart, name='add_to_cart'),
    path('cart', views.cart_view, name='cart'),
    path('checkout', views.checkout_view, name='checkout'),
    path('process_payment/', views.process_payment, name='process_payment'),
    path('my_orders/', views.my_orders, name='my_orders'),
    path('address/', views.address_page, name="address_page"),
    path('delete-address/<int:id>/', views.delete_address, name="delete_address"),
]