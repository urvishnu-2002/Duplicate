VISHNUVARDHAN REDDY
urvishnu
Online

Mahalakshmi — 11-02-2026 12:06
Hello vishnu
From first day  to till now task list endulo pettali
VISHNUVARDHAN REDDY — 12-02-2026 08:55
Hello
Please send here
Mahalakshmi — 12-02-2026 09:04
Ok
What is the work for me today
VISHNUVARDHAN REDDY — 12-02-2026 09:07
forward the tasks till now you have completed
Mahalakshmi — 12-02-2026 09:15
Image
VISHNUVARDHAN REDDY — 12-02-2026 09:36
copy,  noted
VISHNUVARDHAN REDDY — 12-02-2026 15:38
Hello Mahalakshmi
Are you there
Mahalakshmi — 12-02-2026 16:17
Ha vishnu
What happen
VISHNUVARDHAN REDDY — 12-02-2026 16:40
Ntg
Integration lo errors ochai kadha
vati status entii ani chesa
Mahalakshmi — 12-02-2026 16:46
Integration ayyindi kani adi login error backend lo ochindi adi ela cheyyanu nenu frontend lo chesa kada integration
Ippudu latest code ekkadundi vishnu
VISHNUVARDHAN REDDY — 12-02-2026 16:53
evo konni errors osthunnai 
check chesthunnam
Me and Nandini
Mahalakshmi — 12-02-2026 17:09
Ok vishnu
VISHNUVARDHAN REDDY — 12-02-2026 17:09
ha
Mahalakshmi — Yesterday at 22:00
Hello
Vishnu nenu main lo chesa kada
VISHNUVARDHAN REDDY — Yesterday at 22:00
hello
Mahalakshmi — Yesterday at 22:00
Vere folder lo ela cheyyali
VISHNUVARDHAN REDDY — Yesterday at 22:01
haan
VISHNUVARDHAN REDDY — Yesterday at 22:01
adhi ela cheppali ippudu
Mahalakshmi — Yesterday at 22:01
Ela
VISHNUVARDHAN REDDY — Yesterday at 22:02
tmrw chudkundham kadha , nak idea ledhu
balaji vallani adagali
Mahalakshmi — Yesterday at 22:03
Oka pani cheddama nuvvu elago nenu branch loki push chesaka nuvvu copy chesi main lo pedthav ka alage nenu copy chesi niku send chestha avi past chesthava
Avthada
VISHNUVARDHAN REDDY — Yesterday at 22:04
ha done
ikkade send chey
Mahalakshmi — Yesterday at 22:04
Okk
Mahalakshmi — Yesterday at 22:13
settings file
"""
Django settings for ShopSphere project.
"""

from pathlib import Path
from datetime import timedelta

message.txt
5 KB
urls file
from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('user_login', views.login_api, name='user_login'),
    path('register', views.register_api, name='register'),
    path('logout', views.logout_api, name='logout'),

    # Shop / Product

    path('', views.get_product, name='user_products'),

    # Cart
    path('cart', views.cart_view, name='cart'),
    path('add_to_cart/<int:product_id>', views.add_to_cart, name='add_to_cart'),
    path('remove_from_cart/<int:product_id>', views.remove_from_cart, name='remove_from_cart'),
    path('update_cart_quantity/<int:product_id>', views.update_cart_quantity, name='update_cart_quantity'),


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
views file
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from decimal import Decimal

from .models import AuthUser, Cart, CartItem, Order, OrderItem, Address, Review
from .serializers import RegisterSerializer, ProductSerializer, CartSerializer, OrderSerializer, AddressSerializer
from .forms import AddressForm
import uuid
from django.db import transaction
from vendor.models import Product
from rest_framework.decorators import authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def register_api(request):
    if request.method == 'GET':
        return render(request, "user_register.html")
    
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        if request.accepted_renderer.format == 'json':
            return Response({"message": "User registered successfully"}, status=201)
        return redirect('user_login')

    if request.accepted_renderer.format == 'json':
        return Response(serializer.errors, status=400)
    return render(request, "user_register.html", {"error": serializer.errors})

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def login_api(request):
    if request.method == 'GET':
        return render(request, "user_login.html")
    
    # support both JSON API clients (username/email) and HTML form
    username_or_email = request.data.get('email') or request.data.get('username')
    password = request.data.get('password')

    auth_identifier = username_or_email
    # If user provided a username instead of an email, resolve to the underlying email
    # because USERNAME_FIELD is 'email' in our AuthUser model.
    if username_or_email and '@' not in username_or_email:
        try:
            u = AuthUser.objects.get(username=username_or_email)
            auth_identifier = u.email
        except AuthUser.DoesNotExist:
            auth_identifier = None

    user = authenticate(username=auth_identifier, password=password)

    if user:
        login(request, user)
        refresh = RefreshToken.for_user(user)
        
        if request.accepted_renderer.format == 'json':
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "username": user.username,
                "role": user.role
            })
        else:
            return redirect('user_products')

    return Response({"error": "Invalid credentials"}, status=401)


# 🔹 HOME (Product Page)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_product(request):
    products = Product.objects.all()
    
    if request.accepted_renderer.format == 'json':
        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    cart_count = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_count = sum(item.quantity for item in cart.items.all())
        except Cart.DoesNotExist:
            pass
            
    return render(request, "product_list.html", {
        "products": products, 
        "cart_count": cart_count,
        "user": request.user
    })

@api_view(['GET', 'POST'])
@authentication_classes([JWTAuthentication])
... (273 lines left)

message.txt
15 KB
VISHNUVARDHAN REDDY — Yesterday at 22:16
a folder lo a file update cheyyalo kuda cheppava
Mahalakshmi — Yesterday at 22:17
user backend
VISHNUVARDHAN REDDY — Yesterday at 22:18
dhantlo sub folders kuda cheppara 
prathi sub folder lo untai e files
Mahalakshmi — Yesterday at 22:19
3 files e  view,urls for user
settings okate kada
VISHNUVARDHAN REDDY — Yesterday at 22:19
ok
Mahalakshmi — Yesterday at 22:20
frontend push chesa vendordashboard ani untadi
add to cart integration
VISHNUVARDHAN REDDY — Yesterday at 22:21
ok ma
Mahalakshmi — Yesterday at 22:21
haa
﻿
Mahalakshmi
mahalakshmi08928
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from decimal import Decimal

from .models import AuthUser, Cart, CartItem, Order, OrderItem, Address, Review
from .serializers import RegisterSerializer, ProductSerializer, CartSerializer, OrderSerializer, AddressSerializer
from .forms import AddressForm
import uuid
from django.db import transaction
from vendor.models import Product
from rest_framework.decorators import authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def register_api(request):
    if request.method == 'GET':
        return render(request, "user_register.html")
    
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        if request.accepted_renderer.format == 'json':
            return Response({"message": "User registered successfully"}, status=201)
        return redirect('user_login')

    if request.accepted_renderer.format == 'json':
        return Response(serializer.errors, status=400)
    return render(request, "user_register.html", {"error": serializer.errors})

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def login_api(request):
    if request.method == 'GET':
        return render(request, "user_login.html")
    
    # support both JSON API clients (username/email) and HTML form
    username_or_email = request.data.get('email') or request.data.get('username')
    password = request.data.get('password')

    auth_identifier = username_or_email
    # If user provided a username instead of an email, resolve to the underlying email
    # because USERNAME_FIELD is 'email' in our AuthUser model.
    if username_or_email and '@' not in username_or_email:
        try:
            u = AuthUser.objects.get(username=username_or_email)
            auth_identifier = u.email
        except AuthUser.DoesNotExist:
            auth_identifier = None

    user = authenticate(username=auth_identifier, password=password)

    if user:
        login(request, user)
        refresh = RefreshToken.for_user(user)
        
        if request.accepted_renderer.format == 'json':
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "username": user.username,
                "role": user.role
            })
        else:
            return redirect('user_products')

    return Response({"error": "Invalid credentials"}, status=401)


# 🔹 HOME (Product Page)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_product(request):
    products = Product.objects.all()
    
    if request.accepted_renderer.format == 'json':
        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    cart_count = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_count = sum(item.quantity for item in cart.items.all())
        except Cart.DoesNotExist:
            pass
            
    return render(request, "product_list.html", {
        "products": products, 
        "cart_count": cart_count,
        "user": request.user
    })

@api_view(['GET', 'POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not item_created:
        cart_item.quantity += 1
        cart_item.save()
    
    if request.accepted_renderer.format == 'json':
        return Response({
            "message": "Product added to cart",
            "cart_count": sum(item.quantity for item in cart.items.all())
        })
        
    return redirect('cart')

@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    if request.accepted_renderer.format == 'json':
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)
        
    total_price = sum(item.get_total() for item in cart_items)
    
    return render(request, "cart.html", {
        "cart_items": cart_items, 
        "total_cart_price": total_price
    })

@api_view(['POST', 'DELETE'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def remove_from_cart(request, product_id):
    cart = get_object_or_404(Cart, user=request.user)
    cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    cart_item.delete()
    
    if request.accepted_renderer.format == 'json':
        return Response({
            "message": "Product removed from cart",
            "cart_count": sum(item.quantity for item in cart.items.all())
        })
    return redirect('cart')

@api_view(['POST', 'PATCH'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def update_cart_quantity(request, product_id):
    action = request.data.get('action') # 'increase' or 'decrease'
    cart = get_object_or_404(Cart, user=request.user)
    cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    
    if action == 'increase':
        cart_item.quantity += 1
    elif action == 'decrease':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
        else:
            cart_item.delete()
            return Response({"message": "Item removed from cart", "cart_count": sum(item.quantity for item in cart.items.all())})
    
    cart_item.save()
    
    return Response({
        "message": "Quantity updated",
        "quantity": cart_item.quantity,
        "cart_count": sum(item.quantity for item in cart.items.all())
    })

def checkout_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    if not cart_items:
        if request.accepted_renderer.format == 'json':
             return Response({"message": "Cart is empty"}, status=400)
        return redirect('cart')
        
    total_price = sum(item.get_total() for item in cart_items)
    items_count = sum(item.quantity for item in cart_items)
    
    if request.accepted_renderer.format == 'json':
        return Response({
            "total_price": total_price,
            "items_count": items_count,
            "cart_items": CartSerializer(cart).data
        })
    
    return render(request, "checkout.html", {
        "total_price": total_price,
        "items_count": items_count
    })

@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def process_payment(request):
    payment_mode = request.data.get('payment_mode')
    transaction_id = request.data.get('transaction_id') or str(uuid.uuid4())[:12]
    items_from_request = request.data.get('items')
    order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"

    if not payment_mode:
        return Response({"error": "Payment mode required"}, status=400)

    try:
        with transaction.atomic():
            # CASE 1: Items passed directly (frontend state)
            if items_from_request:
                total_amount = Decimal('0.00')
                for item_data in items_from_request:
                    price = Decimal(str(item_data.get('price', 0)))
                    quantity = int(item_data.get('quantity', 1))
                    total_amount += price * quantity
                
                order = Order.objects.create(
                    user=request.user,
                    order_number=order_number,
                    payment_method=payment_mode,
                    transaction_id=transaction_id,
                    total_amount=total_amount,
                    subtotal=total_amount
                )
                
                for item_data in items_from_request:
                    price = Decimal(str(item_data.get('price', 0)))
                    quantity = int(item_data.get('quantity', 1))
                    OrderItem.objects.create(
                        order=order,
                        product_name=item_data.get('name'),
                        quantity=quantity,
                        product_price=price,
                        subtotal=price * quantity
                    )
                Cart.objects.filter(user=request.user).delete()

            # CASE 2: Use items from the database cart
            else:
                cart = Cart.objects.get(user=request.user)
                cart_items = cart.items.all()
                if not cart_items:
                    return Response({"error": "Cart is empty"}, status=400)

                total_amount = sum(item.get_total() for item in cart_items)
                
                order = Order.objects.create(
                    user=request.user,
                    order_number=order_number,
                    payment_method=payment_mode,
                    transaction_id=transaction_id,
                    total_amount=total_amount,
                    subtotal=total_amount
                )

                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        product_name=item.product.name,
                        quantity=item.quantity,
                        product_price=item.product.price,
                        subtotal=item.get_total()
                    )
                cart.items.all().delete()

    except Cart.DoesNotExist:
        return Response({"error": "Cart not found"}, status=404)
    except Exception as e:
        return Response({"error": f"Database Error: {str(e)}"}, status=500)

    if request.accepted_renderer.format == 'json':
        return Response({
            "success": True,
            "message": "Order placed successfully",
            "order_number": order_number,
            "order_id": order.id
        })
    
    return redirect('my_orders')

@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    if request.accepted_renderer.format == 'json':
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
        
    return render(request, "my_orders.html", {"orders": orders})

@api_view(['GET', 'POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def address_page(request):
    if request.method == 'POST':
        # Use Serializer for API/JSON requests
        if request.accepted_renderer.format == 'json':
            serializer = AddressSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=request.user)
                return Response({
                    "message": "Address saved successfully",
                    "address": serializer.data
                }, status=201)
            return Response(serializer.errors, status=400)
        
        # Fallback for traditional HTML forms
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            return redirect('address_page')

    addresses = Address.objects.filter(user=request.user).order_by('-created_at')[:1]
    
    if request.accepted_renderer.format == 'json':
        serializer = AddressSerializer(addresses, many=True)
        return Response({"addresses": serializer.data})
        
    form = AddressForm()
    return render(request, "address.html", {"addresses": addresses, "form": form})

@api_view(['POST', 'GET', 'DELETE'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def delete_address(request, id):
    address = get_object_or_404(Address, id=id, user=request.user)
    address.delete()
    
    if request.accepted_renderer.format == 'json':
        return Response({"message": "Address deleted successfully"})
        
    return redirect('address_page')

@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
def logout_api(request):
    logout(request)
    return redirect('user_login')

@login_required
def review_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    user = request.user
    if request.method == "POST":
        rating = request.POST.get('rating')
        if rating and rating.isdigit() and 1 <= int(rating) <= 5:
            Review.objects.create(
                user=request.user,
                Product=product,
                rating=int(rating),
                comment=request.POST.get('comment', ''),
                pictures=request.FILES.get('pictures')
            )
            return redirect('home')
        return render(request, 'review.html', {'product': product, 'error': 'Please provide a valid rating between 1 and 5.'})
    return render(request, 'review.html', {'product': product})

# @login_required
# def user_reviews(request):
#     reviews = Review.objects.filter(user=request.user)
#     return render(request, 'user_reviews.html', {'reviews': reviews})