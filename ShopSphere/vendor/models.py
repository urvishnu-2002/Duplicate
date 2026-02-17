from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum, Q
from decimal import Decimal


class VendorProfile(models.Model):
    """Vendor Profile Model for vendor registration and management"""
    
    BUSINESS_CHOICES = [
        ('retail', 'Retail'),
        ('wholesale', 'Wholesale'),
        ('manufacturer', 'Manufacturer'),
        ('service', 'Service'),
    ]

    ID_PROOF_CHOICES = [
        ('gst', 'GST'),
        ('pan', 'PAN'),
    ]
    
    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vendor_profile')
    shop_name = models.CharField(max_length=100)
    shop_description = models.TextField()
    address = models.TextField() 
    business_type = models.CharField(max_length=20, choices=BUSINESS_CHOICES)
    
    # Legacy fields
    id_type = models.CharField(max_length=10, choices=ID_PROOF_CHOICES, blank=True, null=True)
    id_number = models.CharField(max_length=50, blank=True, null=True)
    id_proof_file = models.FileField(upload_to='vendor_docs/', blank=True, null=True)
    
    # GST / PAN fields
    gst_number = models.CharField(max_length=15, blank=True, null=True)
    pan_number = models.CharField(max_length=10, blank=True, null=True)
    pan_name = models.CharField(max_length=100, blank=True, null=True)
    pan_card_file = models.FileField(upload_to='pan_cards/', blank=True, null=True)
    
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_blocked = models.BooleanField(default=False)
    blocked_reason = models.TextField(blank=True, null=True)
    
    # Bank Details
    bank_holder_name = models.CharField(max_length=100, blank=True, null=True)
    bank_account_number = models.CharField(max_length=20, blank=True, null=True)
    bank_ifsc_code = models.CharField(max_length=11, blank=True, null=True)
    
    # Shipping Preferences
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Vendor Statistics (denormalized for performance)
    total_products = models.IntegerField(default=0)
    total_orders = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['approval_status']),
            models.Index(fields=['is_blocked']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.shop_name} ({self.user.username})"
    
    @property
    def is_approved(self):
        return self.approval_status == 'approved'
    
    def get_total_revenue(self):
        """Calculate total revenue from all completed orders"""
        from user.models import OrderItem
        total = OrderItem.objects.filter(
            vendor=self,
            order__status__in=['delivered', 'completed']
        ).aggregate(Sum('total_price'))['total_price__sum'] or Decimal('0.00')
        return total
    
    def get_pending_commission(self):
        """Get total commission pending payout"""
        return VendorCommission.objects.filter(
            vendor=self,
            status='pending'
        ).aggregate(Sum('commission_amount'))['commission_amount__sum'] or Decimal('0.00')
    
    def get_total_commission_paid(self):
        """Get total commission already paid out"""
        return VendorCommission.objects.filter(
            vendor=self,
            status='paid'
        ).aggregate(Sum('commission_amount'))['commission_amount__sum'] or Decimal('0.00')



# ===============================================
#               PRODUCT MODEL
# ===============================================

class Product(models.Model):
    """Product Model for vendor products"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    CATEGORY_CHOICES = [
        ('electronics', 'Electronics'),
        ('fashion', 'Fashion'),
        ('home_kitchen', 'Home & Kitchen'),
        ('beauty_personal_care', 'Beauty & Personal Care'),
        ('sports_fitness', 'Sports & Fitness'),
        ('toys_games', 'Toys & Games'),
        ('automotive', 'Automotive'),
        ('grocery', 'Grocery'),
        ('books', 'Books'),
        ('services', 'Services'),
        ('other', 'Other'),
    ]

    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_blocked = models.BooleanField(default=False)
    blocked_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Product Statistics
    total_sold = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.IntegerField(default=0)
    
    # Product visibility
    views_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor']),
            models.Index(fields=['status']),
            models.Index(fields=['is_blocked']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.name} - {self.vendor.shop_name}"

    def clean(self):
        # Enforce minimum 4 images
        if self.pk and self.images.count() < 4:
            raise ValidationError("Product must have at least 4 images.")
    
    def get_available_quantity(self):
        """Get available quantity (total minus ordered)"""
        from user.models import OrderItem
        ordered = OrderItem.objects.filter(
            product=self,
            order__status__in=['pending', 'confirmed', 'shipping']
        ).aggregate(Sum('quantity'))['quantity__sum'] or 0
        return max(0, self.quantity - ordered)


# ===============================================
#          PRODUCT IMAGE MODEL
# ===============================================

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Image for {self.product.name}"


# ===============================================
#        VENDOR SALES ANALYTICS MODEL
# ===============================================

class VendorSalesAnalytics(models.Model):
    """Daily/monthly sales analytics for vendors"""
    
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='sales_analytics')
    period_type = models.CharField(max_length=20, choices=PERIOD_CHOICES, default='daily')
    date = models.DateField()
    
    # Sales metrics
    total_orders = models.IntegerField(default=0)
    total_items_sold = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Customer metrics
    unique_customers = models.IntegerField(default=0)
    returning_customers = models.IntegerField(default=0)
    
    # Order status breakdown
    completed_orders = models.IntegerField(default=0)
    cancelled_orders = models.IntegerField(default=0)
    returned_orders = models.IntegerField(default=0)
    
    # Product metrics
    top_selling_product = models.CharField(max_length=200, blank=True, null=True)
    category_performance = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['vendor', '-date']),
            models.Index(fields=['period_type']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['vendor', 'date', 'period_type'], name='unique_vendor_analytics')
        ]

    def __str__(self):
        return f"{self.vendor.shop_name} - {self.period_type.title()} ({self.date})"


# ===============================================
#        VENDOR COMMISSION MODEL
# ===============================================

class VendorCommission(models.Model):
    """Commission tracking for vendor payouts"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]
    
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='commissions')
    
    # Commission details
    order = models.ForeignKey('user.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='vendor_commissions')
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)  # Percentage (0-100)
    order_amount = models.DecimalField(max_digits=12, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment = models.OneToOneField('VendorPayment', on_delete=models.SET_NULL, null=True, blank=True, related_name='commission')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Commission for {self.vendor.shop_name} - {self.commission_amount} ({self.status})"
    
    def approve(self):
        """Approve pending commission"""
        if self.status == 'pending':
            self.status = 'approved'
            self.approved_at = timezone.now()
            self.save()
    
    def mark_as_paid(self, payment=None):
        """Mark commission as paid"""
        if self.status in ['approved', 'processing']:
            self.status = 'paid'
            self.paid_at = timezone.now()
            if payment:
                self.payment = payment
            self.save()


# ===============================================
#        VENDOR PAYMENT MODEL
# ===============================================

class VendorPayment(models.Model):
    """Vendor payout/payment tracking"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('wallet', 'Wallet'),
        ('crypto', 'Cryptocurrency'),
    ]
    
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='payments')
    
    # Payment details
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='bank_transfer')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Commission batching
    from_date = models.DateField()
    to_date = models.DateField()
    total_commissions = models.IntegerField(default=0)  # Number of commissions included
    
    # Status and reference
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    utr_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Notes and tracking
    notes = models.TextField(blank=True, null=True)
    failed_reason = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Audit trail
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='vendor_payments_processed',
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Payment for {self.vendor.shop_name} - {self.amount} ({self.status})"
    
    def mark_as_completed(self, transaction_id=None):
        """Mark payment as completed"""
        if self.status in ['pending', 'processing']:
            self.status = 'completed'
            self.completed_at = timezone.now()
            if transaction_id:
                self.transaction_id = transaction_id
            self.save()
    
    def mark_as_failed(self, reason=''):
        """Mark payment as failed"""
        self.status = 'failed'
        self.failed_reason = reason
        self.save()


# ===============================================
#    VENDOR ORDER SUMMARY MODEL
# ===============================================

class VendorOrderSummary(models.Model):
    """Quick access to vendor's order statistics and metrics"""
    
    vendor = models.OneToOneField(VendorProfile, on_delete=models.CASCADE, related_name='order_summary')
    
    # Order metrics
    total_orders = models.IntegerField(default=0)
    pending_orders = models.IntegerField(default=0)
    processing_orders = models.IntegerField(default=0)
    shipped_orders = models.IntegerField(default=0)
    delivered_orders = models.IntegerField(default=0)
    cancelled_orders = models.IntegerField(default=0)
    returned_orders = models.IntegerField(default=0)
    
    # Customer metrics
    total_customers = models.IntegerField(default=0)
    repeat_customers = models.IntegerField(default=0)
    
    # Financial metrics
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_commission_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    pending_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Rating metrics
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Vendor Order Summaries"

    def __str__(self):
        return f"{self.vendor.shop_name} Order Summary"
    
    def refresh_metrics(self):
        """Recalculate all metrics from actual data"""
        from user.models import OrderItem, Order
        
        # Calculate order statuses
        order_items = OrderItem.objects.filter(vendor=self.vendor)
        self.total_orders = order_items.values('order').distinct().count()
        self.pending_orders = order_items.filter(vendor_status='pending').count()
        self.processing_orders = order_items.filter(vendor_status='processing').count()
        self.shipped_orders = order_items.filter(vendor_status='shipped').count()
        
        # Calculate revenue
        self.total_revenue = order_items.filter(
            order__status__in=['delivered', 'completed']
        ).aggregate(Sum('total_price'))['total_price__sum'] or Decimal('0.00')
        
        # Calculate commissions
        self.total_commission_paid = self.vendor.get_total_commission_paid()
        self.pending_commission = self.vendor.get_pending_commission()
        
        self.save()


# ===============================================
#          PRODUCT VARIANTS & ATTRIBUTES
# ===============================================

class ProductVariant(models.Model):
    """Product variants like size, color, etc."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    
    attribute_name = models.CharField(max_length=100)  # e.g., 'Size', 'Color'
    attribute_value = models.CharField(max_length=100)  # e.g., 'M', 'Red'
    sku = models.CharField(max_length=100, unique=True)
    
    price_modifier = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Additional price
    quantity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'sku']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.attribute_name}: {self.attribute_value}"

    def get_price(self):
        """Get actual price for this variant"""
        return self.product.price + self.price_modifier


class InventoryAlert(models.Model):
    """Low stock alerts for vendors"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='inventory_alert')
    low_stock_threshold = models.IntegerField(default=10)
    reorder_quantity = models.IntegerField(default=50)
    
    alert_sent = models.BooleanField(default=False)
    last_alert_sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Alert - {self.product.name}"


# ===============================================
#          PRODUCT BUNDLE & BULK UPLOAD
# ===============================================

class ProductBundle(models.Model):
    """Bundle multiple products with discount"""
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='product_bundles')
    name = models.CharField(max_length=255)
    description = models.TextField()
    
    bundle_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_till = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.vendor.shop_name}"


class BundleProduct(models.Model):
    """Individual products in a bundle"""
    bundle = models.ForeignKey(ProductBundle, on_delete=models.CASCADE, related_name='products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    class Meta:
        unique_together = ('bundle', 'product')

    def __str__(self):
        return f"{self.product.name} x{self.quantity} in {self.bundle.name}"


class BulkProductUpload(models.Model):
    """Track bulk product uploads via CSV"""
    UPLOAD_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='bulk_uploads')
    csv_file = models.FileField(upload_to='bulk_uploads/')
    status = models.CharField(max_length=20, choices=UPLOAD_STATUS_CHOICES, default='pending')
    
    total_rows = models.IntegerField(default=0)
    successful_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    
    error_log = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Bulk Upload - {self.vendor.shop_name} ({self.status})"


# ===============================================
#          SELLER PERFORMANCE & RATINGS
# ===============================================

class SellerPerformanceRating(models.Model):
    """Automatic performance rating based on metrics"""
    vendor = models.OneToOneField(VendorProfile, on_delete=models.CASCADE, related_name='performance_rating')
    
    # Ratings (0-5)
    product_quality_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    delivery_timeliness_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    customer_service_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    # Overall performance
    overall_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    # Metrics
    total_orders = models.IntegerField(default=0)
    on_time_delivery_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    product_return_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    dispute_resolution_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Status
    status = models.CharField(max_length=20, default='good', choices=[
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('poor', 'Poor'),
    ])
    
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Seller Performance Ratings'

    def __str__(self):
        return f"Performance - {self.vendor.shop_name} ({self.overall_rating}★)"


class VendorWallet(models.Model):
    """Vendor wallet for earnings and payouts"""
    vendor = models.OneToOneField(VendorProfile, on_delete=models.CASCADE, related_name='wallet')
    
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pending_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    bank_account_name = models.CharField(max_length=255, blank=True, null=True)
    bank_account_number = models.CharField(max_length=20, blank=True, null=True)
    bank_ifsc = models.CharField(max_length=11, blank=True, null=True)
    
    payout_frequency = models.CharField(max_length=20, default='weekly', choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet - {self.vendor.shop_name}"


class VendorPayout(models.Model):
    """Payout transactions for vendors"""
    PAYOUT_STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('rejected', 'Rejected'),
    ]

    vendor_wallet = models.ForeignKey(VendorWallet, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYOUT_STATUS_CHOICES, default='requested')
    
    payout_method = models.CharField(max_length=50)  # Bank Transfer, UPI, etc.
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"Payout - {self.vendor_wallet.vendor.shop_name} - ₹{self.amount}"
