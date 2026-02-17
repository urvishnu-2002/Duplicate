from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('user_login', views.login_api, name='user_login'),
    path('register', views.register_api, name='register'),
    path('logout', views.logout_api, name='logout'),

    # Shop / Product
<<<<<<< HEAD
    path('', views.home_api, name='home'),
    path('userProducts', views.home_api, name='home'),
    
    # Cart 
=======
   
    path('', views.get_product, name='user_products'),

    # Cart
>>>>>>> bc5c9a9c70879a27dcda6caaba4b7b1606a4b5f9
    path('cart', views.cart_view, name='cart'),
    path('add_to_cart/<int:product_id>', views.add_to_cart, name='add_to_cart'),
    
    
    path('checkout', views.checkout_view, name='checkout'),
    path('process_payment', views.process_payment, name='process_payment'),

    # User Profile / Orders
    path('my_orders', views.my_orders, name='my_orders'),
    path('address', views.address_page, name="address_page"),
    path('delete-address/<int:id>', views.delete_address, name="delete_address"),

    # #Reviews
    # '''path('my_reviews', views.user_reviews, name='user_reviews'),
    # path('submit_review/<int:product_id>', views.submit_review, name='submit_review'),
    # path('delete_review/<int:review_id>', views.delete_review, name='delete_review'),
    # path('edit_review/<int:review_id>', views.edit_review, name='edit_review'),'''
    # path('review_product/<int:product_id>', views.review_product, name='review_product')
]