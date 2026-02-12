from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login ,logout
from django.shortcuts import render, redirect, get_object_or_404
from .models import AuthUser, Product, Cart, CartItem, Order, OrderItem, Address
from .serializers import RegisterSerializer, ProductSerializer, CartSerializer, OrderSerializer
from .forms import AddressForm


# 🔹 REGISTER
@api_view(['GET', 'POST'])
def register_api(request):
    if request.method == 'GET':
        return render(request, "user_register.html")
    
    serializer = RegisterSerializer(data=request.data)

    
    print(f"DEBUG: Register Data: {request.data}")

    if serializer.is_valid():
        serializer.save()
        if 'application/json' in request.headers.get('Accept', ''):
            return Response({"message": "User registered successfully"}, status=201)
        return redirect('login')

    
    print(f"DEBUG: Register Errors: {serializer.errors}")


    return Response(serializer.errors, status=400)


# 🔹 LOGIN (JWT token generate)
@api_view(['GET', 'POST'])
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
        
        # Check if it's HTML form submission vs JSON API
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


from vendor.models import Product as VendorProduct

# 🔹 HOME (Product Page)
@api_view(['GET'])
def home_api(request):
    products = VendorProduct.objects.all()
    
    # API / JSON Response
    if 'application/json' in request.headers.get('Accept', '') or request.accepted_renderer.format == 'json':
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
    items_from_request = request.data.get('items') # For frontend direct sync
    
    if not payment_mode:
        print(f"DEBUG: Payment Error - Missing payment_mode. Data: {request.data}")
        return Response({"error": "Payment mode required"}, status=400)

    items_to_process = []
    
    # CASE 1: Items are passed directly in the request (Frontend Redux state)
    if items_from_request:
        for item_data in items_from_request:
            items_to_process.append({
                "name": item_data.get('name'),
                "quantity": item_data.get('quantity', 1),
                "price": item_data.get('price', 0)
            })
    # CASE 2: Fallback to Backend Database Cart
    else:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all()
            if not cart_items:
                if 'application/json' in request.headers.get('Accept', ''):
                    return Response({"error": "Cart is empty"}, status=400)
                return redirect('home')
                
            for item in cart_items:
                items_to_process.append({
                    "name": item.product.name,
                    "quantity": item.quantity,
                    "price": float(item.product.price)
                })
        except Cart.DoesNotExist:
            if 'application/json' in request.headers.get('Accept', ''):
                return Response({"error": "Cart not found and no items provided"}, status=404)
            return redirect('home')

    if not items_to_process:
        print(f"DEBUG: Payment Error - No items to process.")
        return Response({"error": "No items to process"}, status=400)

    # Create ONE Order for the entire transaction
    summary_str = ", ".join([f"{i.get('quantity')} x {i.get('name')}" for i in items_to_process])
    
    order = Order.objects.create(
        user=request.user,
        payment_mode=payment_mode,
        transaction_id=transaction_id,
        item_names=summary_str
    )
    
    for item in items_to_process:
        OrderItem.objects.create(
            order=order,
            product_name=item['name'],
            quantity=item['quantity'],
            price=item['price']
        )
    
    # Clear the DB cart after successful order creation
    try:
        cart = Cart.objects.get(user=request.user)
        cart.items.all().delete()
    except Cart.DoesNotExist:
        pass

    if 'application/json' in request.headers.get('Accept', ''):
        return Response({
            "success": True, 
            "message": "Payment successful", 
            "order_id": order.id
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


# 🔹 ADDRESS PAGE
@api_view(['GET', 'POST'])
def address_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    if request.method == 'POST':
        form = AddressForm(request.data)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            return redirect('address_page')
    
    addresses = Address.objects.filter(user=request.user)
    form = AddressForm()
    return render(request, "address.html", {"addresses": addresses, "form": form})


# 🔹 DELETE ADDRESS
@api_view(['POST', 'GET'])
def delete_address(request, id):
    address = get_object_or_404(Address, id=id, user=request.user)
    address.delete()
    return redirect('address_page')


# 🔹 LOGOUT
@api_view(['POST', 'GET'])
def logout_api(request):
    logout(request)
    return redirect('login')