from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test

@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    """Render the main Admin Dashboard HTML page"""
    return render(request, 'admin_dashboard.html')  

@user_passes_test(lambda u: u.is_superuser)
def admin_login_view(request):
    """Render the Admin Login HTML page"""
    return render(request, 'admin_login.html')

@user_passes_test(lambda u: u.is_superuser)
def admin_logout_view(request):
    """Handle Admin Logout and redirect to login page"""
    from django.contrib.auth import logout
    logout(request)
    return render(request, 'admin_login.html')

@user_passes_test(lambda u: u.is_superuser)
def manage_vendor_requests(request):
    """Render the Vendor Request Management HTML page"""
    return render(request, 'manage_vendor_requests.html')

@user_passes_test(lambda u: u.is_superuser)
def vendor_request_detail(request, vendor_id):
    """Render the Vendor Request Detail HTML page"""
    return render(request, 'vendor_request_detail.html', {'vendor_id': vendor_id})

@user_passes_test(lambda u: u.is_superuser)
def approve_vendor(request, vendor_id):
    """Handle Vendor Approval and redirect to request detail page"""
    # Logic to approve vendor would go here
    return render(request, 'vendor_request_detail.html', {'vendor_id': vendor_id, 'message': 'Vendor Approved'})

@user_passes_test(lambda u: u.is_superuser)
def reject_vendor(request, vendor_id):
    """Handle Vendor Rejection and redirect to request detail page"""
    # Logic to reject vendor would go here
    return render(request, 'vendor_request_detail.html', {'vendor_id': vendor_id, 'message': 'Vendor Rejected'})

@user_passes_test(lambda u: u.is_superuser)
def manage_vendors(request):
    """Render the Vendor Management HTML page"""
    return render(request, 'manage_vendors.html')

@user_passes_test(lambda u: u.is_superuser)
def vendor_detail(request, vendor_id):
    """Render the Vendor Detail HTML page"""
    return render(request, 'vendor_detail.html', {'vendor_id': vendor_id})

@user_passes_test(lambda u: u.is_superuser)
def block_vendor(request, vendor_id):
    """Handle Vendor Blocking and redirect to vendor detail page"""
    # Logic to block vendor would go here
    return render(request, 'vendor_detail.html', {'vendor_id': vendor_id, 'message': 'Vendor Blocked'})

@user_passes_test(lambda u: u.is_superuser)
def unblock_vendor(request, vendor_id):
    """Handle Vendor Unblocking and redirect to vendor detail page"""
    # Logic to unblock vendor would go here
    return render(request, 'vendor_detail.html', {'vendor_id': vendor_id, 'message': 'Vendor Unblocked'})

@user_passes_test(lambda u: u.is_superuser)
def manage_products(request):
    """Render the Product Management HTML page"""
    return render(request, 'manage_products.html')

@user_passes_test(lambda u: u.is_superuser)
def product_detail(request, product_id):
    """Render the Product Detail HTML page"""
    return render(request, 'product_detail.html', {'product_id': product_id})

@user_passes_test(lambda u: u.is_superuser)
def block_product(request, product_id):
    """Handle Product Blocking and redirect to product detail page"""
    # Logic to block product would go here
    return render(request, 'product_detail.html', {'product_id': product_id, 'message': 'Product Blocked'})

@user_passes_test(lambda u: u.is_superuser)
def unblock_product(request, product_id):
    """Handle Product Unblocking and redirect to product detail page"""
    # Logic to unblock product would go here
    return render(request, 'product_detail.html', {'product_id': product_id, 'message': 'Product Unblocked'})
