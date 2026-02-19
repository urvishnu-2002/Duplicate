from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render

# Create your views here.
import random
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import user_passes_test, login_required
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import VendorProfile, Product, ProductImage
from django.db import transaction

User = get_user_model()


# ============================================================================
# AUTHENTICATION VIEWS - VENDOR REGISTRATION AND LOGIN
# ============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp_api(request):
    """API to send OTP via backend SMTP. Stores OTP in session server-side."""
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email is required'}, status=400)

    otp = str(random.randint(100000, 999999))

    # Store OTP in session (server-side, never exposed to client)
    request.session['otp_code'] = otp
    request.session['otp_email'] = email
    request.session.modified = True

    try:
        send_mail(
            subject="Your ShopSphere Verification Code",
            message=(
                f"Hello,\n\n"
                f"Your OTP for ShopSphere account verification is:\n\n"
                f"  {otp}\n\n"
                f"This OTP is valid for 10 minutes. Do not share it with anyone.\n\n"
                f"- ShopSphere Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return Response({
            'success': True,
            'message': f'OTP sent successfully to {email}',
        })
    except Exception as e:
        error_msg = str(e)
        print(f"[OTP ERROR] Failed to send email to {email}: {error_msg}")
        # Clear session OTP if email failed
        request.session.pop('otp_code', None)
        request.session.pop('otp_email', None)
        return Response({'error': f'Failed to send OTP email. Please try again. ({error_msg})'}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp_api(request):
    """API to verify OTP submitted by the user"""
    submitted_otp = request.data.get('otp')
    email = request.data.get('email')

    if not submitted_otp or not email:
        return Response({'error': 'OTP and email are required'}, status=400)

    session_otp = request.session.get('otp_code')
    session_email = request.session.get('otp_email')

    if not session_otp:
        return Response({'error': 'OTP expired or not generated. Please request a new OTP.'}, status=400)

    if session_email != email:
        return Response({'error': 'Email does not match the OTP request.'}, status=400)

    if str(submitted_otp) == str(session_otp):
        # Clear OTP from session after successful verification
        request.session.pop('otp_code', None)
        request.session.pop('otp_email', None)
        return Response({'success': True, 'message': 'OTP verified successfully'})
    else:
        return Response({'error': 'Invalid OTP. Please try again.'}, status=400)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Vendor registration - handles both traditional form and JSON API"""
    if request.method == "GET":
        return render(request, 'register.html')

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
            return render(request, 'register.html', {'error': 'Required fields missing'})
        
        pass

    # If it's the NEW full registration flow from BankDetails.jsx (Atomic Registration)
    if is_json and data.get('bank_account_number'):
        try:
            with transaction.atomic():
                # Get or Create User
                if request.user.is_authenticated:
                    user = request.user
                    # Ensure role is vendor
                    if user.role == 'customer':
                        user.role = 'vendor'
                        user.save()
                else:
                    # Check for existing user by email
                    user = User.objects.filter(email=email).first()
                    if user:
                        # Update existing user role
                        if user.role == 'customer':
                            user.role = 'vendor'
                            user.save()
                        # Verify or set password
                        if password:
                            user.set_password(password)
                            user.save()
                    else:
                        # Create new user
                        user = User.objects.create_user(
                            username=username if username else email.split('@')[0],
                            email=email,
                            password=password,
                            role='vendor'
                        )
                    print(f"DEBUG: Using user {user.email} for atomic vendor registration.")

                # Check if they already have a vendor profile
                if VendorProfile.objects.filter(user=user).exists():
                    return Response({'error': 'You already have a vendor profile or a pending request.'}, status=400)
                
                # Create the vendor profile with all registration data
                VendorProfile.objects.create(
                    user=user,
                    shop_name=data.get('shop_name', data.get('storeName', '')),
                    shop_description=data.get('shop_description', data.get('shopDescription', '')),
                    address=data.get('address', data.get('shippingAddress', '')),
                    business_type=data.get('business_type', data.get('businessType', 'retail')),
                    gst_number=data.get('gst_number', data.get('gstNumber', '')),
                    pan_number=data.get('pan_number', data.get('panNumber', '')),
                    pan_name=data.get('pan_name', data.get('panName', '')),
                    id_type=data.get('id_type', data.get('idType', 'gst')),
                    id_number=data.get('id_number', data.get('idNumber', '')),
                    bank_holder_name=data.get('bank_holder_name', ''),
                    bank_account_number=data.get('bank_account_number', ''),
                    bank_ifsc_code=data.get('bank_ifsc_code', ''),
                    shipping_fee=data.get('shipping_fee') if data.get('shipping_fee') else 0.00,
                    approval_status='pending'
                )
                
                print(f"DEBUG: Vendor details for {user.username} sent to Admin for approval.")
                return Response({'success': True, 'message': 'Registration submitted! Details have been sent to the Admin for approval.'}, status=201)
        except Exception as e:
            print(f"DEBUG: Error during vendor registration: {str(e)}")
            return Response({'error': str(e)}, status=500)

    # LEGACY / OTP FLOW
    otp = random.randint(100000, 999999)
    request.session['reg_data'] = {
        'username': username,
        'email': email,
        'password': password,
        'otp': otp
    }

    try:
        send_mail(
            subject="Your Vendor OTP",
            message=f"Your OTP for registration is: {otp}\n\nDo not share this OTP with anyone.",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
        )
    except Exception as e:
        if is_json: return Response({'error': f'Error sending OTP: {str(e)}'}, status=500)
        return render(request, 'register.html', {'error': f'Error sending OTP: {str(e)}'})

    if is_json:
        return Response({'success': True, 'message': 'OTP sent to email', 'otp_required': True})
    return redirect('verify_otp')


def verify_otp_view(request):
    """Verify OTP and create user account"""
    if request.method == "POST":
        entered_otp = request.POST.get('otp')
        reg_data = request.session.get('reg_data')

        if not reg_data:
            return render(request, 'verify_otp.html', {
                'error': 'Session expired. Please register again.'
            })

        if str(reg_data['otp']) == entered_otp:
            # Check for existing user
            user = User.objects.filter(email=reg_data['email']).first()
            if user:
                # Update role if needed
                if user.role == 'customer':
                    user.role = 'vendor'
                    user.save()
            else:
                # Create user
                user = User.objects.create_user(
                    username=reg_data['username'],
                    email=reg_data['email'],
                    password=reg_data['password'],
                    role='vendor'
                )
            request.session['vendor_user_id'] = user.id
            del request.session['reg_data']
            return redirect('vendor_details')
        else:
            return render(request, 'verify_otp.html', {
                'error': 'Invalid OTP. Please try again.'
            })

    return render(request, 'verify_otp.html')


def vendor_details_view(request):
    """Vendor submits shop details to complete registration"""
    user_id = request.session.get('vendor_user_id')
    
    if not user_id:
        return redirect('register')

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        VendorProfile.objects.create(
            user=user,
            shop_name=request.POST.get('shop_name'),
            shop_description=request.POST.get('shop_description'),
            address=request.POST.get('address'),
            business_type=request.POST.get('business_type'),
            id_type=request.POST.get('id_type'),
            id_number=request.POST.get('id_number'),
            id_proof_file=request.FILES.get('id_proof_file'),
            approval_status='pending'
        )
        if 'vendor_user_id' in request.session:
            del request.session['vendor_user_id']
        return redirect('login')
    return render(request, 'vendor_details.html')


def login_view(request):
    """Vendor login"""
    if request.method == "POST":
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')

        # First try authentication with the provided identifier as email (since it's the USERNAME_FIELD)
        user = authenticate(request, username=username_or_email, password=password)

        # If that fails, try to find a user with that username and use their email to authenticate
        if not user:
            # Check for non-unique username matches
            potential_users = User.objects.filter(username=username_or_email)
            for u in potential_users:
                # Try authenticating with each user's email
                authenticated_user = authenticate(request, username=u.email, password=password)
                if authenticated_user:
                    user = authenticated_user
                    break

        if user:
            login(request, user)
            return redirect('vendor_home')
        else:
            return render(request, 'login.html', {
                'error': 'Invalid credentials'
            })
    return render(request, 'login.html')


def logout_view(request):
    """Vendor logout"""
    logout(request)
    return redirect('login')


# ============================================================================
# VENDOR DASHBOARD - APPROVAL STATUS AND PRODUCT MANAGEMENT
# ============================================================================

@login_required(login_url='login')
def vendor_home_view(request):
    """
    Vendor home page with approval status.
    If not approved, show status (pending/rejected).
    If approved, show vendor dashboard.
    """
    try:
        vendor = request.user.vendor_profile
    except VendorProfile.DoesNotExist:
        return redirect('login')

    # Check if vendor is blocked
    if vendor.is_blocked:
        return render(request, 'vendor_blocked.html', {
            'vendor': vendor
        })

    # If not approved, show status page
    if vendor.approval_status != 'approved':
        return render(request, 'approval_status.html', {
            'vendor': vendor,
            'status': vendor.approval_status,
            'rejection_reason': vendor.rejection_reason
        })

    # If approved, show products dashboard
    products = vendor.products.all()
    return render(request, 'vendor_dashboard.html', {
        'vendor': vendor,
        'products': products
    })


@login_required(login_url='login')
def approval_status_view(request):
    """
    Show approval status page.
    Accessible only when not approved.
    """
    try:
        vendor = request.user.vendor_profile
    except VendorProfile.DoesNotExist:
        return redirect('login')

    if vendor.approval_status == 'approved':
        return redirect('vendor_home')

    return render(request, 'approval_status.html', {
        'vendor': vendor,
        'status': vendor.approval_status,
        'rejection_reason': vendor.rejection_reason
    })


# ============================================================================
# PRODUCT MANAGEMENT - VENDOR SIDE
# ============================================================================

# ============================================================================
# PRODUCT MANAGEMENT - VENDOR SIDE (UPDATED FOR MULTIPLE IMAGES)
# ============================================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def add_product_view(request):
    """Add new product with minimum 4 images"""

    try:
        vendor = request.user.vendor_profile
    except VendorProfile.DoesNotExist:
        return redirect('login')

    if vendor.approval_status != 'approved':
        return redirect('approval_status')

    if request.method == "POST":
        category = request.POST.get('category')
        if category == 'other':
            category = request.POST.get('custom_category', 'other')

        # 🔥 Get multiple images
        images = request.FILES.getlist('images')

        # 🔥 Validate minimum 4 images
        if len(images) < 4:
            return render(request, 'add_product.html', {
                'vendor': vendor,
                'categories': Product.CATEGORY_CHOICES,
                'error': 'Minimum 4 images required.'
            })

        # ✅ Create Product (WITHOUT image field)
        product = Product.objects.create(
            vendor=vendor,
            name=request.POST.get('name'),
            description=request.POST.get('description'),
            category=category,
            price=request.POST.get('price'),
            quantity=request.POST.get('quantity'),
            status='active'
        )

        # ✅ Save Images
        for image in images:
            ProductImage.objects.create(
                product=product,
                image=image
            )

        return redirect('vendor_home')

    return render(request, 'add_product.html', {
        'vendor': vendor,
        'categories': Product.CATEGORY_CHOICES
    })


# ------------------------------------------------------------

@login_required(login_url='login')
def edit_product_view(request, product_id):
    """Edit product and optionally replace images"""

    try:
        vendor = request.user.vendor_profile
    except VendorProfile.DoesNotExist:
        return redirect('login')

    if vendor.approval_status != 'approved':
        return redirect('approval_status')

    product = get_object_or_404(Product, id=product_id, vendor=vendor)

    if request.method == "POST":

        product.name = request.POST.get('name', product.name)
        product.description = request.POST.get('description', product.description)

        category = request.POST.get('category')
        if category == 'other':
            category = request.POST.get('custom_category', product.category)

        product.category = category
        product.price = request.POST.get('price', product.price)
        product.quantity = request.POST.get('quantity', product.quantity)
        product.save()

        # 🔥 If new images uploaded, replace old images
        new_images = request.FILES.getlist('images')

        if new_images:
            if len(new_images) < 4:
                return render(request, 'edit_product.html', {
                    'vendor': vendor,
                    'product': product,
                    'categories': Product.CATEGORY_CHOICES,
                    'error': 'Minimum 4 images required.'
                })

            # Delete old images
            product.images.all().delete()

            # Save new images
            for image in new_images:
                ProductImage.objects.create(product=product, image=image)

        return redirect('vendor_home')

    return render(request, 'edit_product.html', {
        'vendor': vendor,
        'product': product,
        'categories': Product.CATEGORY_CHOICES
    })


# ------------------------------------------------------------

@login_required(login_url='login')
def delete_product_view(request, product_id):
    """Delete product and its images"""

    try:
        vendor = request.user.vendor_profile
    except VendorProfile.DoesNotExist:
        return redirect('login')

    if vendor.approval_status != 'approved':
        return redirect('approval_status')

    product = get_object_or_404(Product, id=product_id, vendor=vendor)

    # 🔥 Delete related images first
    product.images.all().delete()

    product.delete()

    return redirect('vendor_home')


# ------------------------------------------------------------

@login_required(login_url='login')
def view_product_view(request, product_id):
    """View product with all images"""

    try:
        vendor = request.user.vendor_profile
    except VendorProfile.DoesNotExist:
        return redirect('login')

    product = get_object_or_404(Product, id=product_id, vendor=vendor)

    images = product.images.all()

    context = {
        'vendor': vendor,
        'product': product,
        'images': images,
        'is_blocked': product.is_blocked,
        'blocked_reason': product.blocked_reason
    }

    return render(request, 'product_detail.html', context)