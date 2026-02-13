from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import AuthUser, Product, Cart, CartItem, Order, OrderItem, Address
from .forms import AddressForm
from .serializers import (
    RegisterSerializer,
    ProductSerializer,
    CartSerializer,
    OrderSerializer
)


# =====================================================
# 🔹 REGISTER
# =====================================================
@api_view(['GET', 'POST'])
def register_api(request):

    if request.method == 'GET':
        return render(request, "user_register.html")

    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return redirect('login')

    return Response(serializer.errors, status=400)


# =====================================================
# 🔹 LOGIN
# =====================================================
@api_view(['GET', 'POST'])
def login_api(request):

    # HTML page
    if request.method == 'GET':
        return render(request, "user_login.html")

    username = request.data.get('email') or request.data.get('username')
    password = request.data.get('password')

    # allow email login
    if username and '@' in username:
        try:
            user_obj = AuthUser.objects.get(email=username)
            username = user_obj.username
        except AuthUser.DoesNotExist:
            username = None

    user = authenticate(username=username, password=password)

    if user:
        login(request, user)

        refresh = RefreshToken.for_user(user)

        # JSON (API)
        if request.accepted_renderer.format == 'json':
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            })

        # HTML
        return redirect('home')

    return Response({"error": "Invalid credentials"}, status=401)


# =====================================================
# 🔹 HOME (PRODUCT LIST)
# =====================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def home_api(request):

    products = Product.objects.all()

    if request.accepted_renderer.format == 'json':
        return Response(ProductSerializer(products, many=True).data)

    cart_count = 0
    try:
        cart = Cart.objects.get(user=request.user)
        cart_count = sum(item.quantity for item in cart.items.all())
    except Cart.DoesNotExist:
        pass

    return render(request, "product_list.html", {
        "products": products,
        "cart_count": cart_count
    })


# =====================================================
# 🔹 ADD TO CART
# =====================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    cart, _ = Cart.objects.get_or_create(user=request.user)

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product
    )

    if not created:
        item.quantity += 1
        item.save()

    return Response({"message": "Added to cart"})


# =====================================================
# 🔹 CART
# =====================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cart_view(request):

    cart, _ = Cart.objects.get_or_create(user=request.user)
    return Response(CartSerializer(cart).data)


# =====================================================
# 🔹 CHECKOUT
# =====================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def checkout_view(request):

    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.all()

    total = sum(i.total_price() for i in items)

    return Response({"total_price": total})


# =====================================================
# 🔹 PROCESS PAYMENT
# =====================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_payment(request):

    cart = Cart.objects.get(user=request.user)
    items = cart.items.all()

    for item in items:
        order = Order.objects.create(
            user=request.user,
            payment_mode=request.data.get('payment_mode'),
            item_names=item.product.name
        )

        OrderItem.objects.create(
            order=order,
            product_name=item.product.name,
            quantity=item.quantity,
            price=item.product.price
        )

        item.delete()

    return Response({"message": "Order placed successfully"})


# =====================================================
# 🔹 MY ORDERS
# =====================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_orders(request):

    orders = Order.objects.filter(user=request.user)
    return Response(OrderSerializer(orders, many=True).data)


# =====================================================
# 🔹 LOGOUT
# =====================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def logout_api(request):

    logout(request)
    return redirect('login')


# =====================================================
# 🔹 ADDRESS PAGE (HTML ONLY)
# =====================================================
@login_required(login_url='/login/')
def address_page(request):

    addresses = Address.objects.filter(user=request.user)

    form = AddressForm()

    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            addr = form.save(commit=False)
            addr.user = request.user
            addr.save()
            return redirect("address_page")

    return render(request, "address.html", {
        "form": form,
        "addresses": addresses
    })


# =====================================================
# 🔹 DELETE ADDRESS
# =====================================================
@login_required(login_url='/login/')
def delete_address(request, id):

    addr = get_object_or_404(Address, id=id, user=request.user)
    addr.delete()

    return redirect('address_page')
