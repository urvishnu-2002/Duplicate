from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
import random

from .models import DeliveryProfile, Order

User = get_user_model()

# ============================================================================
# AUTHENTICATION VIEWS - DELIVERY PARTNER REGISTRATION AND LOGIN
# ============================================================================

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Delivery Partner registration - handles both traditional form and JSON API"""
    if request.method == "GET":
        return render(request, 'delivery_agent/register.html')

    # Detect if it's a JSON request (from frontend)
    is_json = 'application/json' in request.headers.get('Accept', '') or \
              'application/json' in request.headers.get('Content-Type', '')

    # Use request.data for DRF/JSON, or request.POST for traditional forms
    data = request.data if is_json else request.POST
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # Validation for new users
    if not request.user.is_authenticated:
        if not (username and email and password):
            if is_json:
                return Response({'error': 'Username, email, and password are required for new users'}, status=400)
            return render(request, 'delivery_agent/register.html', {'error': 'Required fields missing'})
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            if is_json: return Response({'error': 'Username already exists'}, status=400)
            return render(request, 'delivery_agent/register.html', {'error': 'Username already exists'})
            
        if User.objects.filter(email=email).exists():
            if is_json: return Response({'error': 'Email already exists'}, status=400)
            return render(request, 'delivery_agent/register.html', {'error': 'Email already exists'})

    # If it's the NEW full registration flow (Atomic Registration)
    if is_json and data.get('vehicle_number'):
        try:
            with transaction.atomic():
                # Get or Create User
                if request.user.is_authenticated:
                    user = request.user
                else:
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        role='delivery'
                    )
                    print(f"DEBUG: Created new delivery user {user.email}.")

                # Check if they already have a delivery profile
                if hasattr(user, 'delivery_profile'):
                     return Response({'error': 'You already have a delivery profile.'}, status=400)
                
                # Create the delivery profile with all registration data
                DeliveryProfile.objects.create(
                    user=user,
                    address=data.get('address', ''),
                    vehicle_type=data.get('vehicle_type', 'bike'),
                    vehicle_number=data.get('vehicle_number', ''),
                    driving_license_number=data.get('driving_license_number', ''),
                    bank_holder_name=data.get('bank_holder_name', ''),
                    bank_account_number=data.get('bank_account_number', ''),
                    bank_ifsc_code=data.get('bank_ifsc_code', ''),
                    approval_status='pending'
                )
                
                print(f"DEBUG: Delivery profile for {user.username} created.")
                
                # If it's an authenticated user, keep them logged in
                # If it's a new user, log them out so they need to login to access the dashboard
                if not request.user.is_authenticated and not is_json:
                    # For new users, log out and redirect to login
                    from django.contrib.auth import logout as auth_logout
                    auth_logout(request)
                
                if is_json:
                    return Response({'success': True, 'message': 'Registration submitted! Details have been sent to the Admin for approval.'}, status=201)
                else:
                    return redirect('delivery_login')
        except Exception as e:
            print(f"DEBUG: Error during delivery registration: {str(e)}")
            return Response({'error': str(e)}, status=500)

    # LEGACY / OTP FLOW
    otp = random.randint(100000, 999999)
    request.session['delivery_reg_data'] = {
        'username': username,
        'email': email,
        'password': password,
        'otp': otp
    }

    try:
        send_mail(
            subject="Your Delivery Partner OTP",
            message=f"Your OTP for registration is: {otp}\n\nDo not share this OTP with anyone.",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
        )
    except Exception as e:
        if is_json: return Response({'error': f'Error sending OTP: {str(e)}'}, status=500)
        return render(request, 'delivery_agent/register.html', {'error': f'Error sending OTP: {str(e)}'})

    if is_json:
        return Response({'success': True, 'message': 'OTP sent to email', 'otp_required': True})
    return redirect('delivery_verify_otp')


def verify_otp_view(request):
    """Verify OTP and create user account"""
    if request.method == "POST":
        entered_otp = request.POST.get('otp')
        reg_data = request.session.get('delivery_reg_data')

        if not reg_data:
            return render(request, 'delivery_agent/verify_otp.html', {
                'error': 'Session expired. Please register again.'
            })

        if str(reg_data['otp']) == entered_otp:
            # Create user
            user = User.objects.create_user(
                username=reg_data['username'],
                email=reg_data['email'],
                password=reg_data['password'],
                role='delivery'
            )
            request.session['delivery_user_id'] = user.id
            del request.session['delivery_reg_data']

            return redirect('delivery_details')
        else:
            return render(request, 'delivery_agent/verify_otp.html', {
                'error': 'Invalid OTP. Please try again.'
            })

    return render(request, 'delivery_agent/verify_otp.html')


def delivery_details_view(request):
    """Delivery Partner submits details to complete registration"""
    user_id = request.session.get('delivery_user_id')
    
    if not user_id:
        return redirect('delivery_register')

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        DeliveryProfile.objects.create(
            user=user,
            address=request.POST.get('address'),
            vehicle_type=request.POST.get('vehicle_type'),
            vehicle_number=request.POST.get('vehicle_number'),
            driving_license_number=request.POST.get('driving_license_number'),
            dl_image=request.FILES.get('dl_image'),
            bank_holder_name=request.POST.get('bank_holder_name'),
            bank_account_number=request.POST.get('bank_account_number'),
            bank_ifsc_code=request.POST.get('bank_ifsc_code'),
            approval_status='pending'
        )
        if 'delivery_user_id' in request.session:
            del request.session['delivery_user_id']
        return redirect('delivery_login')
    return render(request, 'delivery_agent/delivery_details.html')


def agent_portal(request):
    """Login View"""
    # If already logged in, send them to the dashboard
    if request.user.is_authenticated:
        return redirect('delivery_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('delivery_dashboard')
        else:
            return render(request, 'delivery_agent/delivery_login.html', {'error': 'Invalid credentials'})

    return render(request, 'delivery_agent/delivery_login.html')


@login_required(login_url='delivery_login')
def delivery_dashboard(request):
    try:
        profile = request.user.delivery_profile
    except DeliveryProfile.DoesNotExist:
        return redirect('delivery_login')
        
    # Ensure these queries work with your Order model
    available_orders = Order.objects.filter(status='AVAILABLE')
    delivered_orders = Order.objects.filter(assigned_to=profile, status='DELIVERED')
    active_orders = Order.objects.filter(assigned_to=profile, status='ON_ROUTE')

    # Calculate earnings (using shipping_cost as proxy)
    total_earnings = sum(order.shipping_cost for order in delivered_orders)

    # Annotate orders with 'earning' for template compatibility
    for order in available_orders:
        order.earning = order.shipping_cost
    
    for order in delivered_orders:
        order.earning = order.shipping_cost

    context = {
        'profile': profile,
        'available_orders': available_orders,
        'delivered_orders': delivered_orders,
        'active_orders_count': active_orders.count(),
        'total_earnings': total_earnings,
    }
    return render(request, 'delivery_agent/delivery_dashboard.html', context)
    
@login_required(login_url='delivery_login')
def accept_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status == 'AVAILABLE':
        order.status = 'ON_ROUTE'
        order.assigned_to = request.user
        order.save()
        messages.success(request, f"Order {order.order_id} accepted!")
    else:
        messages.error(request, "This order is no longer available.")

    return redirect('delivery_dashboard')