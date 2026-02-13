from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login ,logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import AuthUser, Product, Cart, CartItem, Order, OrderItem, Address
from .serializers import RegisterSerializer, ProductSerializer, CartItemSerializer, OrderSerializer
from .forms import AddressForm


@api_view(['GET', 'POST'])
def register_api(request):
    if request.method == 'GET':
        return render(request, "user_register.html")
    
    serializer = RegisterSerializer(data=request.data)
    
    print(f"DEBUG: Register Data: {request.data}")
    if serializer.is_valid():
        serializer.save()
        if request.accepted_renderer.format == 'json':
            return Response({"message": "User registered successfully"}, status=201)
        return redirect('login')
    
    print(f"DEBUG: Register Errors: {serializer.errors}")
    return Response(serializer.errors, status=400)


@api_view(['GET', 'POST'])
def login_api(request):
    if request.method == 'GET':
        return render(request, "user_login.html")
    
    # support both JSON API clients (username) and HTML form (email)
    username = request.data.get('email') or request.data.get('username')
    password = request.data.get('password')


    if username and '@' in username:
        try:
            u = AuthUser.objects.get(email=username)
            username = u.username
        except AuthUser.DoesNotExist:
            username = None
    user = authenticate(username=username, password=password)
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
    return Response({"error": "Invalid credentials"}, status=401)


@api_view(['GET'])
def home_api(request):
    products = Product.objects.all()
    
    
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
    
    if request.accepted_renderer.format == 'json':
        return Response({"message": "Item added to cart", "cart_count": cart.items.count()})
        
    return redirect('home')



@api_view(['GET'])
def cart_view(request):
    if not request.user.is_authenticated:
        if request.accepted_renderer.format == 'json':
            return Response({"error": "Authentication required"}, status=401)
        return redirect('login')
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
def checkout_view(request):
    if not request.user.is_authenticated:
        if request.accepted_renderer.format == 'json':
            return Response({"error": "Authentication required"}, status=401)
        return redirect('login')
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
def process_payment(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=401)
    payment_mode = request.data.get('payment_mode')
    transaction_id = request.data.get('transaction_id')
    items_data = request.data.get('items')

    if not payment_mode:
        print(f"DEBUG: Payment Error - Missing payment_mode. Data: {request.data}")
        return Response({"error": "Payment mode required"}, status=400)


    items_to_process = []
    
    if items_data:
        items_to_process = items_data
    else:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all()
            if not cart_items:
                 return Response({"error": "Cart is empty"}, status=400)
            
            for item in cart_items:
                items_to_process.append({
                    "name": item.product.name,
                    "quantity": item.quantity,
                    "price": float(item.product.price)
                })
            cart.items.all().delete()
        except Cart.DoesNotExist:
            return Response({"error": "No cart items found"}, status=400)

    if not items_to_process:
        print(f"DEBUG: Payment Error - No items to process.")
        return Response({"error": "No items to process"}, status=400)

    
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
            product_name=item.get('name', 'Product'),
            quantity=item.get('quantity', 1),
            price=item.get('price', 0)
        )
        
    return Response({
        "message": "Payment successful and order recorded", 
        "order_id": order.id,
        "transaction_id": transaction_id
    }, status=201)



@api_view(['GET'])
def my_orders(request):
    if not request.user.is_authenticated:
        if request.accepted_renderer.format == 'json':
            return Response({"error": "Authentication required"}, status=401)
        return redirect('login')
    orders = Order.objects.filter(user=request.user).order_by('-order_date')
    
    if request.accepted_renderer.format == 'json':
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
        
    return render(request, "my_orders.html", {"orders": orders})


@api_view(['POST', 'GET'])
def logout_api(request):
    logout(request)
    return redirect('login')

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

def delete_address(request, id):
    addr = get_object_or_404(Address, id=id, user=request.user)
    addr.delete()
    return redirect('address_page')