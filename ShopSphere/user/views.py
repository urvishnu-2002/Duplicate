from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from .models import AuthUser, Product, Cart, CartItem, Order, OrderItem, Address
from .serializers import RegisterSerializer, ProductSerializer, CartSerializer, OrderSerializer
from .forms import AddressForm
from django.contrib.auth.decorators import login_required
from .models import AuthUser, Product, Cart, CartItem, Order, OrderItem, Address
from .serializers import RegisterSerializer, ProductSerializer, CartSerializer, OrderSerializer
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
        if request.accepted_renderer.format == 'json':
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
        # Use session login for HTML form submissions
        login(request, user)
        
        # For API/JSON clients, also return JWT tokens
        refresh = RefreshToken.for_user(user)
        
        if request.accepted_renderer.format == 'json':
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
# @permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not item_created:
        cart_item.quantity += 1
        cart_item.save()
    
    if request.accepted_renderer.format == 'json':
        return Response({"message": "Item added to cart", "cart_count": cart.items.count()})
        
    return redirect('home')


# 🔹 VIEW CART
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    if request.accepted_renderer.format == 'json':
        serializer = CartSerializer(cart)
        return Response(serializer.data)
        
    total_price = sum(item.total_price() for item in cart_items)
    
    return render(request, "cart.html", {
        "cart_items": cart_items, 
        "total_cart_price": total_price
    })


# 🔹 CHECKOUT
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def checkout_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    if not cart_items:
        if request.accepted_renderer.format == 'json':
             return Response({"message": "Cart is empty"}, status=400)
        return redirect('cart')
        
    total_price = sum(item.total_price() for item in cart_items)
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


# 🔹 PROCESS PAYMENT
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_payment(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=401)
        
    payment_mode = request.data.get('payment_mode')
    transaction_id = request.data.get('transaction_id')
    items_from_request = request.data.get('items')

    # Add timestamp to transaction_id to ensure uniqueness for retries if needed, 
    # BUT better to rely on frontend sending unique IDs or handling it.
    # However, to fix the specific error 500 which is due to trying to create MULTIPLE Orders 
    # with the SAME transaction_id (Unique Constraint Violation), we must refactor to create
    # a Single Order with multiple items.

    if not payment_mode:
        print(f"DEBUG: Payment Error - Missing payment_mode. Data: {request.data}")
        return Response({"error": "Payment mode required"}, status=400)

    items_to_process = []
    
    # CASE 1: Items are passed directly in the request (Frontend Redux state)
    if request.accepted_renderer.format == 'json':
        return Response({"error": "Payment mode required"}, status=400)
    return redirect('checkout')

    order = None

    # CASE 1: Items passed directly (e.g. from a separate frontend state / Buy Now)
    if items_from_request:
        summary_items = []
        for item_data in items_from_request:

            items_to_process.append({
                "name": item_data.get('name'),
                "quantity": item_data.get('quantity', 1),
                "price": item_data.get('price', 0)
            })
    # CASE 2: Fallback to Backend Database Cart

            name = item_data.get('name')
            quantity = item_data.get('quantity', 1)
            summary_items.append(f"{quantity} x {name}")
            
        item_names_str = ", ".join(summary_items)
        
        # Create Single Order
        try:
            order = Order.objects.create(
                user=request.user,
                payment_mode=payment_mode,
                transaction_id=transaction_id,
                item_names=item_names_str
            )
        except Exception as e:
            # Handle potential race condition or duplicate transaction ID
             return Response({"error": f"Database Error: {str(e)}"}, status=500)
        
        # Create OrderItems
        for item_data in items_from_request:
            OrderItem.objects.create(
                order=order,
                product_name=item_data.get('name'),
                quantity=item_data.get('quantity', 1),
                price=item_data.get('price', 0)
            )

        # Optional: Clear cart if bought directly? Assuming yes for consistency
        try:
             Cart.objects.filter(user=request.user).delete()
        except:
             pass
            
    # CASE 2: Use items from the database cart

    else:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all()
            if not cart_items:
                if request.accepted_renderer.format == 'json':
                    return Response({"error": "Cart is empty"}, status=400)
                return redirect('cart')

            # Build summary string
            summary_items = []
            for item in cart_items:
                 summary_items.append(f"{item.quantity} x {item.product.name}")
            item_names_str = ", ".join(summary_items)

            # Create Single Order
            try:
                order = Order.objects.create(
                    user=request.user,
                    payment_mode=payment_mode,
                    transaction_id=transaction_id,
                    item_names=item_names_str
                )
            except Exception as e:
                return Response({"error": f"Database Error: {str(e)}"}, status=500)

            # Create OrderItems
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product_name=item.product.name,
                    quantity=item.quantity,
                    price=item.product.price
                )
            
            cart.items.all().delete()
            
        except Cart.DoesNotExist:
            if request.accepted_renderer.format == 'json':
                return Response({"error": "Cart not found"}, status=404)
            return redirect('home')

    if request.accepted_renderer.format == 'json':
        return Response({
            "success": True,
            "message": "Payment successful",
            "order_id": order.id
        })

    return redirect('my_orders')


# 🔹 MY ORDERS
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-order_date')
    
    if request.accepted_renderer.format == 'json':
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
@permission_classes([IsAuthenticated])
def logout_api(request):
    logout(request)
    return redirect('login')


# 🔹 ADDRESS MANAGEMENT
@login_required
def address_page(request):
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


@login_required
def delete_address(request, id):
    addr = get_object_or_404(Address, id=id, user=request.user)
    addr.delete()
    return redirect("address_page")
