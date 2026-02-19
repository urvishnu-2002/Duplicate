from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class AuthUser(AbstractUser):
    """Extended user model with role-based access"""
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=False)
    phone = models.CharField(max_length=15, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)

    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('delivery', 'Delivery Agent'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    
    # Account status
    is_blocked = models.BooleanField(default=False)
    blocked_reason = models.TextField(blank=True, null=True)
    suspended_until = models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.email} - {self.role}"

    def save(self, *args, **kwargs):
        if (self.is_staff or self.is_superuser) and self.role == 'customer':
            self.role = 'admin'
        super().save(*args, **kwargs)

    def is_account_active(self):
        """Check if account is truly active (not blocked/suspended)"""
        from django.utils import timezone
        if self.is_blocked:
            return False
        if self.suspended_until and timezone.now() < self.suspended_until:
            return False
        return self.is_active


class Wishlist(models.Model):
    """User's wishlist for products"""
    user = models.OneToOneField(AuthUser, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Wishlists'

    def __str__(self):
        return f"{self.user.username}'s Wishlist"


class WishlistItem(models.Model):
    """Items in wishlist"""
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('vendor.Product', on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('wishlist', 'product')

    def __str__(self):
        return f"{self.product.name} in {self.wishlist.user.username}'s wishlist"


class Cart(models.Model):
    """Shopping cart for users"""
    user = models.OneToOneField(AuthUser, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Carts'

    def __str__(self):
        return f"{self.user.username}'s Cart"

    def get_total(self):
        """Calculate total cart value"""
        return sum(item.get_total() for item in self.items.all())

    def get_item_count(self):
        """Get total items in cart"""
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """Individual items in cart"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('vendor.Product', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in {self.cart.user.username}'s cart"

    def get_total(self):
        """Calculate total for this cart item"""
        return self.product.price * self.quantity


class Address(models.Model):
    """Delivery addresses for users"""
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name='addresses')
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=100, default='India')
    
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.name} - {self.city}, {self.state}"
    
    @property
    def full_address(self):
        return f"{self.address_line1}, {self.address_line2}, {self.city}, {self.state} - {self.pincode}"


class Order(models.Model):
    """User orders"""
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipping', 'Shipping'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=50, unique=True)
    delivery_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    
    # Order status
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    
    # Payment information
    payment_method = models.CharField(max_length=50)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    
    # Amounts
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Tracking
    delivery_agent = models.ForeignKey('deliveryAgent.DeliveryAgentProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tracked_location = models.CharField(max_length=255, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['order_number']),
        ]

    def __str__(self):
        return f"Order {self.order_number}"

    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        return self.status in ['pending', 'confirmed']

    def can_be_returned(self):
        """Check if order can be returned"""
        return self.status == 'delivered'


class OrderItem(models.Model):
    """Individual items in an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('vendor.Product', on_delete=models.SET_NULL, null=True)
    vendor = models.ForeignKey('vendor.VendorProfile', on_delete=models.SET_NULL, null=True, related_name='order_items')
    
    product_name = models.CharField(max_length=255)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Vendor order status (separate from main order status)
    VENDOR_STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('confirmed', 'Order Confirmed'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    vendor_status = models.CharField(max_length=20, choices=VENDOR_STATUS_CHOICES, default='waiting')

    class Meta:
        ordering = ['-order__created_at']

    def __str__(self):
        return f"{self.product_name} x {self.quantity} in {self.order.order_number}"


class OrderTracking(models.Model):
    """Order tracking history"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tracking_history')
    status = models.CharField(max_length=50)
    location = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.order.order_number} - {self.status}"


class Payment(models.Model):
    """Payment records"""
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('upi', 'UPI'),
        ('net_banking', 'Net Banking'),
        ('wallet', 'Wallet'),
        ('cod', 'Cash on Delivery'),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name='payments')
    
    method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_id = models.CharField(max_length=100, unique=True)
    
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.status}"


class ProductReview(models.Model):
    """Product reviews and ratings"""
    product = models.ForeignKey('vendor.Product', on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name='product_reviews')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, related_name='reviews')
    
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    
    is_verified = models.BooleanField(default=False)  # Verified purchase
    helpful_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating}★)"


class VendorReview(models.Model):
    """Vendor reviews and ratings"""
    vendor = models.ForeignKey('vendor.VendorProfile', on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name='vendor_reviews')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, related_name='vendor_reviews')
    
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    
    is_verified = models.BooleanField(default=False)
    helpful_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('vendor', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.vendor.shop_name} ({self.rating}★)"


# ===============================================
#          WALLET & PAYMENT MODELS
# ===============================================

class UserWallet(models.Model):
    """User wallet for storing balance and transaction history"""
    user = models.OneToOneField(AuthUser, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_credited = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_debited = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.email} - Balance: ₹{self.balance}"

    def add_balance(self, amount, description=''):
        """Add balance to wallet"""
        if amount > 0:
            self.balance += amount
            self.total_credited += amount
            self.save()
            WalletTransaction.objects.create(
                wallet=self,
                transaction_type='credit',
                amount=amount,
                description=description
            )
            return True
        return False

    def deduct_balance(self, amount, description=''):
        """Deduct balance from wallet"""
        if amount > 0 and self.balance >= amount:
            self.balance -= amount
            self.total_debited += amount
            self.save()
            WalletTransaction.objects.create(
                wallet=self,
                transaction_type='debit',
                amount=amount,
                description=description
            )
            return True
        return False


class WalletTransaction(models.Model):
    """Transaction history for wallets"""
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
        ('refund', 'Refund'),
    ]

    wallet = models.ForeignKey(UserWallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    reference_id = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.wallet.user.email} - {self.transaction_type} ₹{self.amount}"


# ===============================================
#          RETURN & REFUND MODELS
# ===============================================

class OrderReturn(models.Model):
    """Product return requests from customers"""
    RETURN_STATUS_CHOICES = [
        ('requested', 'Return Requested'),
        ('approved', 'Return Approved'),
        ('rejected', 'Return Rejected'),
        ('shipped_back', 'Shipped Back'),
        ('received', 'Received'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    RETURN_REASON_CHOICES = [
        ('damaged', 'Damaged Product'),
        ('defective', 'Defective Product'),
        ('wrong_item', 'Wrong Item Received'),
        ('not_as_described', 'Not As Described'),
        ('size_mismatch', 'Size/Fit Mismatch'),
        ('quality_issue', 'Quality Issue'),
        ('changed_mind', 'Changed Mind'),
        ('other', 'Other'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='returns')
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name='order_return')
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name='returns')
    
    reason = models.CharField(max_length=50, choices=RETURN_REASON_CHOICES)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=RETURN_STATUS_CHOICES, default='requested')
    
    return_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refund_status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Return Request - {self.order.order_number}"


class Refund(models.Model):
    """Refund transactions"""
    REFUND_STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    REFUND_METHOD_CHOICES = [
        ('wallet', 'Wallet'),
        ('original_payment', 'Original Payment Method'),
        ('bank_transfer', 'Bank Transfer'),
    ]

    order_return = models.OneToOneField(OrderReturn, on_delete=models.CASCADE, related_name='refund')
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name='refunds')
    
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    refund_method = models.CharField(max_length=20, choices=REFUND_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='initiated')
    
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    failure_reason = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Refund {self.transaction_id} - ₹{self.refund_amount}"


# ===============================================
#          TWO-FACTOR AUTHENTICATION
# ===============================================

class TwoFactorAuth(models.Model):
    """Two-factor authentication for enhanced security"""
    METHODS = [
        ('email', 'Email OTP'),
        ('sms', 'SMS OTP'),
        ('authenticator', 'Authenticator App'),
    ]

    user = models.OneToOneField(AuthUser, on_delete=models.CASCADE, related_name='two_factor_auth')
    is_enabled = models.BooleanField(default=False)
    method = models.CharField(max_length=20, choices=METHODS, default='email')
    
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    otp_verified_at = models.DateTimeField(null=True, blank=True)
    
    # For authenticator app
    secret_key = models.CharField(max_length=255, blank=True, null=True)
    backup_codes = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"2FA - {self.user.email}"


# ===============================================
#          NOTIFICATION MODELS
# ===============================================

class Notification(models.Model):
    """User notifications"""
    NOTIFICATION_TYPES = [
        ('order', 'Order Update'),
        ('delivery', 'Delivery Update'),
        ('payment', 'Payment Update'),
        ('promotion', 'Promotion'),
        ('refund', 'Refund'),
        ('system', 'System Alert'),
        ('vendor_request', 'Vendor Request'),
    ]

    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    is_read = models.BooleanField(default=False)
    related_order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"{self.title} - {self.user.email}"


# ===============================================
#          DISPUTE/COMPLAINT MODELS
# ===============================================

class Dispute(models.Model):
    """Customer disputes and complaints"""
    DISPUTE_STATUS_CHOICES = [
        ('open', 'Open'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('escalated', 'Escalated'),
    ]

    DISPUTE_CATEGORY_CHOICES = [
        ('product_quality', 'Product Quality'),
        ('late_delivery', 'Late Delivery'),
        ('wrong_item', 'Wrong Item'),
        ('incomplete_order', 'Incomplete Order'),
        ('payment_issue', 'Payment Issue'),
        ('refund_issue', 'Refund Issue'),
        ('seller_behavior', 'Seller Behavior'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name='disputes')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='disputes')
    
    category = models.CharField(max_length=50, choices=DISPUTE_CATEGORY_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=DISPUTE_STATUS_CHOICES, default='open')
    
    evidence_file = models.FileField(upload_to='dispute_evidence/', blank=True, null=True)
    resolution_notes = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey(AuthUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='disputes_assigned')
    
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Dispute - {self.order.order_number} ({self.status})"


# ===============================================
#          COUPON & DISCOUNT MODELS
# ===============================================

class Coupon(models.Model):
    """Discount coupons"""
    COUPON_TYPE_CHOICES = [
        ('percentage', 'Percentage Discount'),
        ('fixed', 'Fixed Amount'),
        ('free_shipping', 'Free Shipping'),
    ]

    code = models.CharField(max_length=50, unique=True)
    coupon_type = models.CharField(max_length=20, choices=COUPON_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    valid_from = models.DateTimeField()
    valid_till = models.DateTimeField()
    
    usage_limit = models.IntegerField(default=None, null=True, blank=True)  # None = unlimited
    usage_per_user = models.IntegerField(default=1)
    current_usage = models.IntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    applicable_for_all = models.BooleanField(default=True)  # False = specific users/vendors
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} - {self.discount_value}{('% off' if self.coupon_type == 'percentage' else ' off')}"

    def is_valid(self):
        """Check if coupon is valid"""
        from django.utils import timezone
        return (self.is_active and 
                timezone.now() >= self.valid_from and 
                timezone.now() <= self.valid_till and 
                (self.usage_limit is None or self.current_usage < self.usage_limit))


class CouponUsage(models.Model):
    """Track coupon usage per user"""
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name='coupon_usages')
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='coupon_usages')
    
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'coupon', 'order')
        ordering = ['-used_at']

    def __str__(self):
        return f"{self.user.email} - {self.coupon.code}"


class Review(models.Model):
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE)
    Product = models.ForeignKey('vendor.Product', on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField()
    pictures = models.ImageField(upload_to='review_pics/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review by {self.user.username} for {self.Product.name}"

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=AuthUser)
def create_user_wallet(sender, instance, created, **kwargs):
    """Automatically create a wallet for every new user"""
    if created:
        UserWallet.objects.get_or_create(user=instance)

@receiver(post_save, sender=AuthUser)
def save_user_wallet(sender, instance, **kwargs):
    """Ensure wallet is saved when user is saved"""
    if hasattr(instance, 'wallet'):
        instance.wallet.save()