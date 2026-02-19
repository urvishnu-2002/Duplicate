from django.shortcuts import render

# Create your views here.
import random
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
User = get_user_model()
from django.contrib.auth.decorators import user_passes_test, login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import VendorProfile, Product, ProductImage, Category
from user.models import Order, OrderItem
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
import json
from decimal import Decimal


# ============================================================================
# BINARY DATA SERVING VIEWS
# ============================================================================

def serve_product_image(request, image_id):
    """Serve product image from database"""
    product_image = get_object_or_404(ProductImage, id=image_id)
    if not product_image.image_data:
        return HttpResponse(status=404)
    
    content_type = product_image.image_mimetype or 'image/jpeg'
    return HttpResponse(product_image.image_data, content_type=content_type)


def serve_vendor_document(request, profile_id, doc_type):
    """Serve vendor documents (ID proof or PAN card) from database"""
    vendor = get_object_or_404(VendorProfile, id=profile_id)
    
    if doc_type == 'id_proof':
        data = vendor.id_proof_data
        name = vendor.id_proof_name
        mimetype = vendor.id_proof_mimetype
    elif doc_type == 'pan_card':
        data = vendor.pan_card_data
        name = vendor.pan_card_name
        mimetype = vendor.pan_card_mimetype
    else:
        return HttpResponse(status=400)
    
    if not data:
        return HttpResponse(status=404)
        
    response = HttpResponse(data, content_type=mimetype or 'application/octet-stream')
    if name:
        response['Content-Disposition'] = f'inline; filename="{name}"'
    return response


# ============================================================================
# AUTHENTICATION VIEWS - VENDOR REGISTRATION AND LOGIN
# ============================================================================

@csrf_exempt
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
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            if is_json: return Response({'error': 'Username already exists'}, status=400)
            return render(request, 'register.html', {'error': 'Username already exists'})
            
        if User.objects.filter(email=email).exists():
            if is_json: return Response({'error': 'Email already exists'}, status=400)
            return render(request, 'register.html', {'error': 'Email already exists'})

    # If it's the NEW full registration flow from BankDetails.jsx (Atomic Registration)
    if is_json and data.get('bank_account_number'):
        try:
            with transaction.atomic():
                # Get or Create User
                if request.user.is_authenticated:
                    user = request.user
                else:
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password
                    )
                    print(f"DEBUG: Created new user {user.email} for atomic vendor registration.")

                # Check if they already have a vendor profile
                if VendorProfile.objects.filter(user=user).exists():
                    return Response({'error': 'You already have a vendor profile or a pending request.'}, status=400)
                
                # Get files if any
                id_proof_file = request.FILES.get('id_proof_file')
                pan_card_file = request.FILES.get('pan_card_file')

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
                    
                    id_proof_data=id_proof_file.read() if id_proof_file else None,
                    id_proof_name=id_proof_file.name if id_proof_file else None,
                    id_proof_mimetype=id_proof_file.content_type if id_proof_file else None,
                    
                    pan_card_data=pan_card_file.read() if pan_card_file else None,
                    pan_card_name=pan_card_file.name if pan_card_file else None,
                    pan_card_mimetype=pan_card_file.content_type if pan_card_file else None,
                    
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
        print(f"DEBUG: Attempting to send OTP to {email}")
        send_mail(
            subject="Your Vendor OTP",
            message=f"Your OTP for registration is: {otp}\n\nDo not share this OTP with anyone.",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
        )
        print(f"DEBUG: OTP sent successfully to {email}")
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
            # Create user
            try:
                # Check if user already exists to prevent IntegrityError on double submission
                if User.objects.filter(email=reg_data['email']).exists():
                   user = User.objects.get(email=reg_data['email'])
                else:
                    user = User.objects.create_user(
                        username=reg_data['username'],
                        email=reg_data['email'],
                        password=reg_data['password']
                    )
            except Exception as e:
                 # verify if user was created
                 if User.objects.filter(email=reg_data['email']).exists():
                     user = User.objects.get(email=reg_data['email'])
                 else:
                     return render(request, 'verify_otp.html', {'error': f'Error creating user: {str(e)}'})

            request.session['vendor_user_id'] = user.id
            # Clean up session data only if we successfully got/created a user
            if 'reg_data' in request.session:
                del request.session['reg_data']

            # if request.accessed_from_mobile:
            #     return JsonResponse({'success': True, 'message': 'OTP verified. Please complete your vendor details.'})

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
        id_proof_file = request.FILES.get('id_proof_file')
        pan_card_file = request.FILES.get('pan_card_file')

        defaults = {
            'shop_name': request.POST.get('shop_name'),
            'shop_description': request.POST.get('shop_description'),
            'address': request.POST.get('address'),
            'business_type': request.POST.get('business_type'),
            'id_type': request.POST.get('id_type'),
            'id_number': request.POST.get('id_number'),
            'approval_status': 'pending'
        }

        if id_proof_file:
            defaults.update({
                'id_proof_data': id_proof_file.read(),
                'id_proof_name': id_proof_file.name,
                'id_proof_mimetype': id_proof_file.content_type,
            })

        if pan_card_file:
            defaults.update({
                'pan_card_data': pan_card_file.read(),
                'pan_card_name': pan_card_file.name,
                'pan_card_mimetype': pan_card_file.content_type,
            })

        VendorProfile.objects.update_or_create(
            user=user,
            defaults=defaults
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
            try:
                temp_user = User.objects.get(username=username_or_email)
                user = authenticate(request, username=temp_user.email, password=password)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                pass

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
    product_names = list(products.values_list('name', flat=True))

    # Calculate sales and earnings
    vendor_order_items = OrderItem.objects.filter(product_name__in=product_names)
    
    total_sales = vendor_order_items.aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')
    
    # Commission (Assume 5% for now)
    commission_rate = Decimal('0.05')
    total_commission = total_sales * commission_rate
    total_earnings = total_sales - total_commission

    # Sales data for graph (last 7 days)
    seven_days_ago = timezone.now() - timezone.timedelta(days=7)
    sales_by_day = (
        vendor_order_items.filter(order__created_at__gte=seven_days_ago)
        .annotate(date=TruncDate('order__created_at'))
        .values('date')
        .annotate(daily_total=Sum('subtotal'))
        .order_by('date')
    )

    # Format data for Chart.js
    labels = []
    dataPoints = []
    
    # Fill in missing dates with zero
    for i in range(7, -1, -1):
        day = (timezone.now() - timezone.timedelta(days=i)).date()
        labels.append(day.strftime('%b %d'))
        
        daily_amount = 0
        for entry in sales_by_day:
            if entry['date'] == day:
                daily_amount = float(entry['daily_total'])
                break
        dataPoints.append(daily_amount)

    context = {
        'vendor': vendor,
        'products': products,
        'total_sales': float(total_sales),
        'total_commission': float(total_commission),
        'total_earnings': float(total_earnings),
        'graph_labels': json.dumps(labels),
        'graph_data': json.dumps(dataPoints),
        # 'categories': Product.CATEGORY_CHOICES, # Old
        'categories': Category.objects.all(), # New
    }

    return render(request, 'vendor_dashboard.html', context)


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

@login_required(login_url='login')
def add_product_view(request):
    """Add new product with minimum 4 images"""

    try:
        vendor = request.user.vendor_profile
    except VendorProfile.DoesNotExist:
        return redirect('login')

    if vendor.approval_status != 'approved':
        return redirect('approval_status')

    if request.method == "POST":
        category_id = request.POST.get('category')
        custom_category_name = request.POST.get('custom_category')
        
        category = None
        
        # Handle custom category or selection
        if category_id and category_id != 'other':
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                pass
        
        # Handle "Other" category with custom name
        if category_id == 'other' or (category_id and not category and custom_category_name):
            if custom_category_name:
                # Create new category from custom name
                slug = slugify(custom_category_name)
                category, created = Category.objects.get_or_create(
                    slug=slug,
                    defaults={'name': custom_category_name}
                )
        
        # If still no category, try to get "other" fallback or error
        if not category:
            category = Category.objects.filter(slug='other').first()
            if not category:
                return render(request, 'add_product.html', {
                    'vendor': vendor,
                    'categories': Category.objects.all(),
                    'error': 'Please select a valid category or provide a custom category name.'
                })


        # 🔥 Get multiple images
        images = request.FILES.getlist('images')

        # 🔥 Validate minimum 4 images
        if len(images) < 4:
            return render(request, 'add_product.html', {
                'vendor': vendor,
                'categories': Category.objects.all(),
                'error': 'Minimum 4 images required.'
            })

        # ✅ Create Product
        product = Product.objects.create(
            vendor=vendor,
            name=request.POST.get('name'),
            description=request.POST.get('description'),
            category=category, # Assign Category object
            price=request.POST.get('price'),
            quantity=request.POST.get('quantity'),
            status='active'
        )

        # ✅ Save Images to Database
        for image_file in images:
            ProductImage.objects.create(
                product=product,
                image_data=image_file.read(),
                image_name=image_file.name,
                image_mimetype=image_file.content_type
            )

        return redirect('vendor_home')

    return render(request, 'add_product.html', {
        'vendor': vendor,
        'categories': Category.objects.all()
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

        category_id = request.POST.get('category')
        custom_category_name = request.POST.get('custom_category')
        
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
                if category.slug == 'other' and custom_category_name:
                     slug = slugify(custom_category_name)
                     category, _ = Category.objects.get_or_create(
                        slug=slug,
                        defaults={'name': custom_category_name}
                     )
                product.category = category
            except Category.DoesNotExist:
                pass


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
                    'categories': Category.objects.all(),
                    'error': 'Minimum 4 images required.'
                })

            # Delete old images
            product.images.all().delete()

            # Save new images to database
            for image_file in new_images:
                ProductImage.objects.create(
                    product=product, 
                    image_data=image_file.read(),
                    image_name=image_file.name,
                    image_mimetype=image_file.content_type
                )

        return redirect('vendor_home')

    return render(request, 'edit_product.html', {
        'vendor': vendor,
        'product': product,
        'categories': Category.objects.all()
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