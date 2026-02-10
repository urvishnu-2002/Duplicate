from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login ,logout
from django.shortcuts import render, redirect, get_object_or_404
from .models import AuthUser, Product, Cart, CartItem, Order, OrderItem, Address
from .serializers import RegisterSerializer, ProductSerializer, CartSerializer, OrderSerializer, CartItemSerializer
from .forms import AddressForm


# 🔹 REGISTER
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def register_api(request):
    if request.method == 'GET':
        return render(request, "user_register.html")
    
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        if 'application/json' in request.headers.get('Accept', ''):
            return Response({"message": "User registered successfully"}, status=201)
        return redirect('login')

    if request.accepted_renderer.format == 'json':
        return Response(serializer.errors, status=400)
    return render(request, "user_register.html", {"error": serializer.errors})


# 🔹 LOGIN (JWT token generate)
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def login_api(request):
    if request.method == 'GET':
        return render(request, "user_login.html")
    
    # We use email as the primary login field now
    email = request.data.get('email') or request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=email, password=password)

    if user:
        # Use session login for HTML form submissions
        login(request, user)
        
        # For API/JSON clients, also return JWT tokens
        refresh = RefreshToken.for_user(user)
        
        if 'application/json' in request.headers.get('Accept', ''):
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "username": user.username,
                "role": user.role
            })
        else:
            return redirect('home')

    return Response({"error": "Invalid credentials"}, status=401)


# 🔹 HOME (Product Page)
@api_view(['GET'])
def home_api(request):
    products = Product.objects.all()
    
    # API / JSON Response
    if 'application/json' in request.headers.get('Accept', ''):
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)
        
    # HTML Response
    cart_count = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            # Sum of quantities
            cart_count = sum(item.quantity for item in cart.items.all())
        except Cart.DoesNotExist:
            pass
            
    return render(request, "product_list.html", {
        "products": products, 
        "cart_count": cart_count,
        "user": request.user
    })

# 🔹 ADD TO CART
@api_view(['GET', 'POST'])
def add_to_cart(request, product_id):
    if not request.user.is_authenticated:
        if request.accepted_renderer.format == 'json':
            return Response({"error": "Authentication required"}, status=401)
        return redirect('login')
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not item_created:
        cart_item.quantity += 1
        cart_item.save()
    
    if 'application/json' in request.headers.get('Accept', ''):
        return Response({"message": "Item added to cart", "cart_count": cart.items.count()})
        
    return redirect('home')


# 🔹 VIEW CART
@api_view(['GET'])
def cart_view(request):
    if not request.user.is_authenticated:
        if request.accepted_renderer.format == 'json':
            return Response({"error": "Authentication required"}, status=401)
        return redirect('login')
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    if 'application/json' in request.headers.get('Accept', ''):
        serializer = CartSerializer(cart)
        return Response(serializer.data)
        
    total_price = sum(item.total_price() for item in cart_items)
    
    return render(request, "cart.html", {
        "cart_items": cart_items, 
        "total_cart_price": total_price
    })


# 🔹 CHECKOUT
@api_view(['GET'])
def checkout_view(request):
    if not request.user.is_authenticated:
        if request.accepted_renderer.format == 'json':
            return Response({"error": "Authentication required"}, status=401)
        return redirect('login')
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    if not cart_items:
        if 'application/json' in request.headers.get('Accept', ''):
             return Response({"message": "Cart is empty"}, status=400)
        return redirect('cart')
        
    total_price = sum(item.total_price() for item in cart_items)
    items_count = sum(item.quantity for item in cart_items)
    
    if 'application/json' in request.headers.get('Accept', ''):
        return Response({
            "total_price": total_price,
            "items_count": items_count,
            "cart_items": CartSerializer(cart).data
        })
    
    return render(request, "checkout.html", {
        "total_price": total_price,
        "items_count": items_count
    })


# 🔹 PROCESS PAYMENT
@api_view(['POST'])
def process_payment(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=401)
    
    payment_mode = request.data.get('payment_mode')
    transaction_id = request.data.get('transaction_id')
    items_from_request = request.data.get('items')

    if not payment_mode:
        return Response({"error": "Payment mode required"}, status=400)

    created_orders = []
    
    # CASE 1: Items passed directly (e.g. from a separate frontend state)
    if items_from_request:
        for item_data in items_from_request:
            name = item_data.get('name')
            quantity = item_data.get('quantity', 1)
            price = item_data.get('price', 0)
            
            order = Order.objects.create(
                user=request.user,
                payment_mode=payment_mode,
                transaction_id=transaction_id,
                item_names=f"{quantity} x {name}"
            )
            OrderItem.objects.create(
                order=order,
                product_name=name,
                quantity=quantity,
                price=price
            )
            created_orders.append(order)
            
        try:
            cart = Cart.objects.get(user=request.user)
            cart.items.all().delete()
        except Cart.DoesNotExist:
            pass
            
    # CASE 2: Use items from the database cart
    else:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all()
            if not cart_items:
                if 'application/json' in request.headers.get('Accept', ''):
                    return Response({"error": "Cart is empty"}, status=400)
                return redirect('cart')

            # Create ONE order for all items in the cart
            summary_str = ", ".join([f"{item.quantity} x {item.product.name}" for item in cart_items])
            order = Order.objects.create(
                user=request.user,
                payment_mode=payment_mode,
                transaction_id=transaction_id,
                item_names=summary_str
            )
            
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product_name=item.product.name,
                    quantity=item.quantity,
                    price=item.product.price
                )
            
            created_orders.append(order)
            cart.items.all().delete()
        except Cart.DoesNotExist:
            if 'application/json' in request.headers.get('Accept', ''):
                return Response({"error": "Cart not found"}, status=404)
            return redirect('home')

    if 'application/json' in request.headers.get('Accept', ''):
        return Response({
            "success": True,
            "message": "Payment successful",
            "orders_created": len(created_orders)
        })
        
    return redirect('my_orders')


# 🔹 MY ORDERS
@api_view(['GET'])
def my_orders(request):
    if not request.user.is_authenticated:
        if request.accepted_renderer.format == 'json':
            return Response({"error": "Authentication required"}, status=401)
        return redirect('login')
    orders = Order.objects.filter(user=request.user).order_by('-order_date')
    
    if 'application/json' in request.headers.get('Accept', ''):
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
        
    return render(request, "my_orders.html", {"orders": orders})


# 🔹 LOGOUT
@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def logout_api(request):
    logout(request)
    return redirect('login')

def address_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    addresses = Address.objects.filter(user=request.user)
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            return redirect("address_page")
    else:
        form = AddressForm()
    return render(request, "address.html", {
        "form": form,
        "addresses": addresses
    })

def delete_address(request, id):
    if not request.user.is_authenticated:
        return redirect('login')
    addr = get_object_or_404(Address, id=id, user=request.user)
    addr.delete()
    return redirect('address_page')