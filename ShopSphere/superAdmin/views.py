from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout, get_user_model
# User = get_user_model() - Moved inside functions to avoid AppRegistryNotReady error

from django.db.models import Q
from django.urls import reverse
from vendor.models import VendorProfile, Product
from .models import VendorApprovalLog, ProductApprovalLog
from rest_framework.permissions import AllowAny,IsAuthenticated
def is_mainapp_admin(user):
    return True

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_login')
        if not is_mainapp_admin(request.user):
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper




from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def admin_login_view(request):
    if request.user.is_authenticated and is_mainapp_admin(request.user):
        return redirect('admin_dashboard')
    
    if request.method == "POST":
        identifier = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=identifier, password=password)

        if not user:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                matching_users = User.objects.filter(username=identifier)
                for potential_user in matching_users:
                    user = authenticate(request, username=potential_user.email, password=password)
                    if user:
                        break
            except Exception:
                pass

        if user:
            login(request, user)
            next_url = request.GET.get('next', 'admin_dashboard')
            return redirect(next_url)
        else:
            error = "Invalid credentials. Please enter your registered email or username."
            return render(request, 'mainApp/admin_login.html', {'error': error})

    return render(request, 'mainApp/admin_login.html')

def admin_logout_view(request):
    logout(request)
    return redirect('admin_login')

@admin_required
def admin_dashboard(request):    
    total_vendors = VendorProfile.objects.count()
    pending_vendors = VendorProfile.objects.filter(approval_status='pending').count()
    approved_vendors = VendorProfile.objects.filter(approval_status='approved').count()
    rejected_vendors = VendorProfile.objects.filter(approval_status='rejected').count()
    blocked_vendors = VendorProfile.objects.filter(is_blocked=True).count()
    
    total_products = Product.objects.count()
    blocked_products = Product.objects.filter(is_blocked=True).count()

    context = {
        'total_vendors': total_vendors,
        'pending_vendors': pending_vendors,
        'approved_vendors': approved_vendors,
        'rejected_vendors': rejected_vendors,
        'blocked_vendors': blocked_vendors,
        'total_products': total_products,
        'blocked_products': blocked_products,
    }

    return render(request, 'mainApp/admin_dashboard.html', context)

@admin_required
def manage_vendor_requests(request):    
    status_filter = request.GET.get('status', 'pending')
    
    if status_filter == 'all':
        vendors = VendorProfile.objects.all().order_by('-created_at')
    else:
        vendors = VendorProfile.objects.filter(approval_status=status_filter).order_by('-created_at')

    context = {
        'vendors': vendors,
        'current_status': status_filter,
        'total': vendors.count()
    }

    return render(request, 'mainApp/manage_vendor_requests.html', context)

@admin_required
def vendor_request_detail(request, vendor_id):
    
    vendor = get_object_or_404(VendorProfile, id=vendor_id)
    approval_logs = vendor.approval_logs.all()

    context = {
        'vendor': vendor,
        'approval_logs': approval_logs
    }

    return render(request, 'mainApp/vendor_request_detail.html', context)

@admin_required
def approve_vendor(request, vendor_id):
    
    vendor = get_object_or_404(VendorProfile, id=vendor_id)

    if request.method == 'POST':
        vendor.approval_status = 'approved'
        vendor.is_blocked = False
        vendor.blocked_reason = None
        vendor.rejection_reason = None
        vendor.save()

        user = vendor.user
        user.role = 'vendor'
        user.save()

        VendorApprovalLog.objects.create(
            vendor=vendor,
            admin_user=request.user,
            action='approved',
            reason=request.POST.get('reason', '')
        )

        return redirect('vendor_request_detail', vendor_id=vendor.id)

    return render(request, 'mainApp/approve_vendor.html', {
        'vendor': vendor
    })

@admin_required
def reject_vendor(request, vendor_id):
    
    vendor = get_object_or_404(VendorProfile, id=vendor_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', 'No reason provided')
        vendor.approval_status = 'rejected'
        vendor.rejection_reason = reason
        vendor.save()

        VendorApprovalLog.objects.create(
            vendor=vendor,
            admin_user=request.user,
            action='rejected',
            reason=reason
        )

        return redirect('vendor_request_detail', vendor_id=vendor.id)

    return render(request, 'mainApp/reject_vendor.html', {
        'vendor': vendor
    })

@admin_required
def manage_vendors(request):    
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    block_filter = request.GET.get('blocked', '')

    vendors = VendorProfile.objects.all()

    if search_query:
        vendors = vendors.filter(
            Q(shop_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    if status_filter:
        vendors = vendors.filter(approval_status=status_filter)

    if block_filter == 'blocked':
        vendors = vendors.filter(is_blocked=True)
    elif block_filter == 'active':
        vendors = vendors.filter(is_blocked=False)

    vendors = vendors.order_by('-created_at')

    context = {
        'vendors': vendors,
        'search_query': search_query,
        'status_filter': status_filter,
        'block_filter': block_filter,
    }

    return render(request, 'mainApp/manage_vendors.html', context)

@admin_required
def block_vendor(request, vendor_id):    
    vendor = get_object_or_404(VendorProfile, id=vendor_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', 'No reason provided')
        vendor.is_blocked = True
        vendor.blocked_reason = reason
        vendor.save()

        VendorApprovalLog.objects.create(
            vendor=vendor,
            admin_user=request.user,
            action='blocked',
            reason=reason
        )

        vendor.products.update(is_blocked=True, blocked_reason=f"Vendor blocked: {reason}")

        return redirect('vendor_detail', vendor_id=vendor.id)

    return render(request, 'mainApp/block_vendor.html', {
        'vendor': vendor
    })

@admin_required
def unblock_vendor(request, vendor_id):    
    vendor = get_object_or_404(VendorProfile, id=vendor_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        vendor.is_blocked = False
        vendor.blocked_reason = None
        vendor.save()

        VendorApprovalLog.objects.create(
            vendor=vendor,
            admin_user=request.user,
            action='unblocked',
            reason=reason
        )

        return redirect('vendor_detail', vendor_id=vendor.id)

    return render(request, 'mainApp/unblock_vendor.html', {
        'vendor': vendor
    })

@admin_required
def vendor_detail(request, vendor_id):    
    vendor = get_object_or_404(VendorProfile, id=vendor_id)
    products = vendor.products.all()
    approval_logs = vendor.approval_logs.all()

    context = {
        'vendor': vendor,
        'products': products,
        'approval_logs': approval_logs,
    }

    return render(request, 'mainApp/vendor_detail.html', context)

@admin_required
def manage_products(request):    
    search_query = request.GET.get('search', '')
    vendor_filter = request.GET.get('vendor', '')
    block_filter = request.GET.get('blocked', '')

    products = Product.objects.all().select_related('vendor')

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if vendor_filter:
        products = products.filter(vendor__id=vendor_filter)

    if block_filter == 'blocked':
        products = products.filter(is_blocked=True)
    elif block_filter == 'active':
        products = products.filter(is_blocked=False)

    products = products.order_by('-created_at')

    vendors = VendorProfile.objects.filter(approval_status='approved').order_by('shop_name')

    context = {
        'products': products,
        'vendors': vendors,
        'search_query': search_query,
        'vendor_filter': vendor_filter,
        'block_filter': block_filter,
    }

    return render(request, 'mainApp/manage_products.html', context)

@admin_required
def product_detail(request, product_id):    
    product = get_object_or_404(Product, id=product_id)
    approval_logs = product.approval_logs.all()

    context = {
        'product': product,
        'vendor': product.vendor,
        'approval_logs': approval_logs,
    }

    return render(request, 'mainApp/product_detail.html', context)

@admin_required
def block_product(request, product_id):
    
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', 'No reason provided')
        product.is_blocked = True
        product.blocked_reason = reason
        product.save()

        ProductApprovalLog.objects.create(
            product=product,
            admin_user=request.user,
            action='blocked',
            reason=reason
        )

        return redirect('product_detail', product_id=product.id)

    return render(request, 'mainApp/block_product.html', {
        'product': product
    })

@admin_required
def unblock_product(request, product_id):    
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        product.is_blocked = False
        product.blocked_reason = None
        product.save()

        ProductApprovalLog.objects.create(
            product=product,
            admin_user=request.user,
            action='unblocked',
            reason=reason
        )

        return redirect('product_detail', product_id=product.id)

    return render(request, 'mainApp/unblock_product.html', {
        'product': product
    })