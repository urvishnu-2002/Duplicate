from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from decimal import Decimal

from .models import AuthUser, Cart, CartItem, Order, OrderItem, Address, Review, OrderReturn, Refund
from .serializers import RegisterSerializer, ProductSerializer, CartSerializer, OrderSerializer, AddressSerializer
from .forms import AddressForm
import uuid
from django.db import transaction
from vendor.models import Product

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

    # If multiple users have the same email/username, we need to find the one with the correct password.
    # The default authenticate() might fail or return MultipleObjectsReturned if email/username is non-unique.
    users = AuthUser.objects.filter(email=username_or_email) if '@' in (username_or_email or '') else AuthUser.objects.filter(username=username_or_email)
    
    user = None
    for u in users:
        if u.check_password(password):
            user = u
            break

    if user:
        login(request, user)
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        
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
#permission_classes([IsAuthenticated])
def home_api(request):
    # Only show active and unblocked products to customers
    products = Product.objects.filter(is_blocked=False, status='active')
    
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

@api_view(['GET'])
def get_product(request):
    # Only show active and unblocked products to customers
    products = Product.objects.filter(is_blocked=False, status='active')
    
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
@permission_classes([IsAuthenticated])
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    if request.accepted_renderer.format == 'json':
        serializer = CartSerializer(cart)
        return Response(serializer.data)
        
    total_price = sum(item.get_total() for item in cart_items)
    
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
                    product_id = item_data.get('id') or item_data.get('product_id')
                    product = Product.objects.filter(id=product_id).first()
                    
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        vendor=product.vendor if product else None,
                        product_name=item_data.get('name') or (product.name if product else "Unknown Product"),
                        quantity=quantity,
                        product_price=price,
                        subtotal=price * quantity,
                        vendor_status='waiting'
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
                        vendor=item.product.vendor,
                        product_name=item.product.name,
                        quantity=item.quantity,
                        product_price=item.product.price,
                        subtotal=item.get_total(),
                        vendor_status='waiting'
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
@permission_classes([IsAuthenticated])
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    if request.accepted_renderer.format == 'json':
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
        
    return render(request, "my_orders.html", {"orders": orders})

@api_view(['GET', 'POST'])
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_info(request):
    user = request.user
    data = {
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_vendor": hasattr(user, 'vendor_profile'),
    }
    if data["is_vendor"]:
        vendor = user.vendor_profile
        data["vendor_status"] = vendor.approval_status
        data["is_approved_vendor"] = vendor.approval_status == 'approved'
    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_return_api(request, order_item_id):
    """Customer requests a return for a specific order item"""
    try:
        order_item = OrderItem.objects.get(id=order_item_id, order__user=request.user)
        
        if order_item.order.status != 'delivered':
            return Response({'error': 'Order not yet delivered'}, status=400)
            
        reason = request.data.get('reason')
        description = request.data.get('description', '')
        
        if not reason:
            return Response({'error': 'Reason for return required'}, status=400)
            
        # Check if already requested
        if hasattr(order_item, 'order_return'):
            return Response({'error': 'Return already requested for this item'}, status=400)
            
        return_req = OrderReturn.objects.create(
            order=order_item.order,
            order_item=order_item,
            user=request.user,
            reason=reason,
            description=description,
            status='requested'
        )
        
        return Response({'message': 'Return request submitted', 'id': return_req.id})
    except OrderItem.DoesNotExist:
        return Response({'error': 'Order item not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_returns(request):
    """List customer return requests"""
    returns = OrderReturn.objects.filter(user=request.user).order_by('-created_at')
    data = []
    for r in returns:
        data.append({
            'id': r.id,
            'order_number': r.order.order_number,
            'product': r.order_item.product_name,
            'reason': r.get_reason_display(),
            'status': r.get_status_display(),
            'created_at': r.created_at
        })
    return Response(data)

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
@api_view(['GET', 'POST'])
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    user_review = None
    can_edit_review = False
    days_left = 0
    
    if request.user.is_authenticated:
        user_review = Review.objects.filter(user=request.user, Product=product).first()
        if user_review:
            # Check 5-day window
            time_diff = timezone.now() - user_review.created_at
            if time_diff.days < 5:
                can_edit_review = True
                days_left = 5 - time_diff.days
    
    if request.method == 'POST':
        reviewer_name = request.data.get('reviewer_name')
        rating = request.data.get('rating')
        comment = request.data.get('comment')
        pictures = request.FILES.get('pictures')
        
        if rating:
            if user_review:
                # Update existing review
                if can_edit_review:
                    user_review.reviewer_name = reviewer_name
                    user_review.rating = int(rating)
                    user_review.comment = comment
                    if pictures:
                        user_review.pictures = pictures
                    user_review.save()
            else:
                # Create new review
                Review.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    Product=product,
                    reviewer_name=reviewer_name,
                    rating=int(rating),
                    comment=comment,
                    pictures=pictures
                )
            
            if request.accepted_renderer.format == 'json':
                return Response({"message": "Review processed successfully"}, status=200)
            return redirect('user_product_detail', product_id=product.id)
    
    reviews = Review.objects.filter(Product=product).order_by('-created_at')
    
    if request.accepted_renderer.format == 'json':
        # Simple serialization for reviews
        reviews_data = [{
            'reviewer_name': r.reviewer_name,
            'rating': r.rating,
            'comment': r.comment,
            'created_at': r.created_at
        } for r in reviews]
        return Response({
            "product": ProductSerializer(product).data,
            "reviews": reviews_data
        })
        
    return render(request, "user_product_detail.html", {
        "product": product,
        "reviews": reviews,
        "user": request.user,
        "user_review": user_review,
        "can_edit_review": can_edit_review,
        "days_left": days_left
    })
