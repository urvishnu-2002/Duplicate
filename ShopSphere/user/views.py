from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import AuthUser, Product, Cart, CartItem, Order, OrderItem, Address
from .serializers import RegisterSerializer, ProductSerializer, CartSerializer, OrderSerializer, AddressSerializer
from .forms import AddressForm
from vendor.models import Product as VendorProduct

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
            return redirect('home')

    if request.accepted_renderer.format == 'json':
        return Response({"error": "Invalid credentials"}, status=401)
    return render(request, "user_login.html", {"error": "Invalid credentials"})

# 🔹 HOME (Product Page)
@api_view(['GET'])
def home_api(request):
    products = VendorProduct.objects.all()
    
    if request.accepted_renderer.format == 'json':
        serializer = ProductSerializer(products, many=True)
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

def get_product(request):
    products = VendorProduct.objects.all()
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
@permission_classes([IsAuthenticated])
def add_to_cart(request, product_id):
    # Depending on your Product model, you might need to import VendorProduct or use the local Product.
    # Looking at home_api, it displays VendorProduct.
    product = get_object_or_404(VendorProduct, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # We need to map VendorProduct to our local Product model if they are different, 
    # OR the CartItem should point to VendorProduct.
    # Checking user/models.py: CartItem points to 'Product' which has name and price.
    # If VendorProduct and Product are separate tables, this might fail.
    # Let's assume you want to add the VendorProduct.
    
    # Fallback to local Product if thats what CartItem expects
    local_product, lp_created = Product.objects.get_or_create(
        name=product.name,
        defaults={'price': product.price}
    )
    
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=local_product)
    
    if not item_created:
        cart_item.quantity += 1
        cart_item.save()
    
    if request.accepted_renderer.format == 'json':
        return Response({"message": "Item added to cart", "cart_count": cart.items.count()})
        
    return redirect('home')

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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_payment(request):
    payment_mode = request.data.get('payment_mode')
    transaction_id = request.data.get('transaction_id')
    items_from_request = request.data.get('items')

    if not payment_mode:
        if request.accepted_renderer.format == 'json':
            return Response({"error": "Payment mode required"}, status=400)
        return redirect('checkout')

    order = None

    # CASE 1: Items passed directly (e.g. from frontend state)
    if items_from_request:
        summary_items = [f"{i.get('quantity', 1)} x {i.get('name')}" for i in items_from_request]
        item_names_str = ", ".join(summary_items)
        
        try:
            order = Order.objects.create(
                user=request.user,
                payment_mode=payment_mode,
                transaction_id=transaction_id,
                item_names=item_names_str
            )
            for item_data in items_from_request:
                OrderItem.objects.create(
                    order=order,
                    product_name=item_data.get('name'),
                    quantity=item_data.get('quantity', 1),
                    price=item_data.get('price', 0)
                )
            # Clear database cart as well
            Cart.objects.filter(user=request.user).delete()
        except Exception as e:
             return Response({"error": f"Database Error: {str(e)}"}, status=500)
            
    # CASE 2: Use items from the database cart
    else:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all()
            if not cart_items:
                if request.accepted_renderer.format == 'json':
                    return Response({"error": "Cart is empty"}, status=400)
                return redirect('cart')

            summary_items = [f"{item.quantity} x {item.product.name}" for item in cart_items]
            item_names_str = ", ".join(summary_items)

            order = Order.objects.create(
                user=request.user,
                payment_mode=payment_mode,
                transaction_id=transaction_id,
                item_names=item_names_str
            )

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-order_date')
    
    if request.accepted_renderer.format == 'json':
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
        
    return render(request, "my_orders.html", {"orders": orders})

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def address_page(request):
    if request.method == 'POST':
        serializer = AddressSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({
                "message": "Address saved successfully",
                "address": serializer.data
            }, status=201)
        return Response(serializer.errors, status=400)
    
    addresses = Address.objects.filter(user=request.user)
    serializer = AddressSerializer(addresses, many=True)
    
    if request.accepted_renderer.format == 'json':
        return Response({"addresses": serializer.data})
        
    return render(request, "address.html", {"addresses": addresses})

@api_view(['POST', 'GET', 'DELETE'])
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