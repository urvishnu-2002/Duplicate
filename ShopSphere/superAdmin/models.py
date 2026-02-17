from django.db import models
from django.conf import settings
from django.utils import timezone
from vendor.models import VendorProfile, Product
from deliveryAgent.models import DeliveryAgentProfile
from user.models import AuthUser, Order

class VendorApprovalLog(models.Model):
    
    ACTION_CHOICES = [
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('blocked', 'Blocked'),
        ('unblocked', 'Unblocked'),
        ('reviewed', 'Reviewed'),
    ]

    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='approval_logs')
    admin_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='vendor_approvals')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    reason = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.vendor.shop_name} - {self.action} by {self.admin_user.username if self.admin_user else 'System'}"

class ProductApprovalLog(models.Model):
    
    ACTION_CHOICES = [
        ('blocked', 'Blocked'),
        ('unblocked', 'Unblocked'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='approval_logs')
    admin_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='product_approvals')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    reason = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.product.name} - {self.action} by {self.admin_user.username if self.admin_user else 'System'}"


# ===============================================
#          DELIVERY AGENT APPROVAL LOGS
# ===============================================

class DeliveryAgentApprovalLog(models.Model):
    """Logs for delivery agent approvals/rejections"""
    ACTION_CHOICES = [
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('blocked', 'Blocked'),
        ('unblocked', 'Unblocked'),
        ('reviewed', 'Reviewed'),
    ]

    agent = models.ForeignKey(DeliveryAgentProfile, on_delete=models.CASCADE, related_name='approval_logs')
    admin_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='delivery_agent_approvals')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    reason = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.agent.user.username} - {self.action}"


# ===============================================
#          COMMISSION MANAGEMENT
# ===============================================

class CommissionStructure(models.Model):
    """Define commission rates for vendors and delivery agents"""
    ENTITY_TYPE_CHOICES = [
        ('vendor', 'Vendor'),
        ('delivery_agent', 'Delivery Agent'),
    ]

    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPE_CHOICES)
    
    # Commission calculation
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_commission_cap = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Time-based structure
    valid_from = models.DateTimeField(default=timezone.now)
    valid_till = models.DateTimeField(null=True, blank=True)
    
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.entity_type.title()} Commission - {self.commission_percentage}%"


class DeliveryAgentCommission(models.Model):
    """Track commissions for delivery agents"""
    COMMISSION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('disputed', 'Disputed'),
    ]

    agent = models.ForeignKey(DeliveryAgentProfile, on_delete=models.CASCADE, related_name='commissions')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='delivery_commissions')
    
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_structure = models.ForeignKey(CommissionStructure, on_delete=models.SET_NULL, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=COMMISSION_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"DA Commission - {self.agent.user.username} - ₹{self.commission_amount}"


# ===============================================
#          ANALYTICS & REPORTING
# ===============================================

class DailyAnalytics(models.Model):
    """Daily analytics snapshot"""
    date = models.DateField(unique=True)
    
    # Orders
    total_orders = models.IntegerField(default=0)
    completed_orders = models.IntegerField(default=0)
    pending_orders = models.IntegerField(default=0)
    cancelled_orders = models.IntegerField(default=0)
    
    # Revenue
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Users
    new_customer_registrations = models.IntegerField(default=0)
    new_vendor_registrations = models.IntegerField(default=0)
    
    # Products
    total_products_listed = models.IntegerField(default=0)
    total_products_sold = models.IntegerField(default=0)
    
    # Deliveries
    total_deliveries = models.IntegerField(default=0)
    successful_deliveries = models.IntegerField(default=0)
    failed_deliveries = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Daily Analytics'

    def __str__(self):
        return f"Analytics - {self.date}"


class SalesReport(models.Model):
    """Track sales metrics for analytics"""
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='sales_reports', null=True, blank=True)
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    total_orders = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    top_products = models.JSONField(default=list, blank=True)  # List of top selling products
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-period_start']

    def __str__(self):
        return f"Sales Report - {self.period_start.date()} to {self.period_end.date()}"


class DeliveryReport(models.Model):
    """Track delivery metrics"""
    agent = models.ForeignKey(DeliveryAgentProfile, on_delete=models.CASCADE, related_name='delivery_reports', null=True, blank=True)
    date = models.DateField()
    
    assigned_orders = models.IntegerField(default=0)
    completed_orders = models.IntegerField(default=0)
    failed_orders = models.IntegerField(default=0)
    returned_orders = models.IntegerField(default=0)
    
    total_distance_km = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    average_delivery_time_minutes = models.IntegerField(default=0)
    
    earnings_today = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        unique_together = ('agent', 'date')

    def __str__(self):
        return f"Delivery Report - {self.date}"


# ===============================================
#          DISPUTE & COMPLAINT MANAGEMENT
# ===============================================

class DisputeResolution(models.Model):
    """Track dispute resolutions"""
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('escalated', 'Escalated'),
        ('closed', 'Closed'),
    ]

    RESOLUTION_CHOICES = [
        ('refund_issued', 'Refund Issued'),
        ('replacement_sent', 'Replacement Sent'),
        ('partial_refund', 'Partial Refund'),
        ('no_action', 'No Action'),
    ]

    dispute = models.OneToOneField('user.Dispute', on_delete=models.CASCADE, related_name='resolution')
    admin_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='dispute_resolutions')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    resolution_type = models.CharField(max_length=30, choices=RESOLUTION_CHOICES, blank=True, null=True)
    
    resolution_notes = models.TextField()
    supporting_documents = models.FileField(upload_to='dispute_documents/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Resolution - Dispute {self.dispute.id}"


# ===============================================
#          SYSTEM CONFIGURATION
# ===============================================

class SystemConfiguration(models.Model):
    """Store system-wide settings"""
    
    # Commission rates
    default_vendor_commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    default_delivery_agent_commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    
    # Refund settings
    refund_window_days = models.IntegerField(default=7)  # Days to request refund after delivery
    
    # Wallet settings
    minimum_withdrawal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    
    # Notification settings
    email_notifications_enabled = models.BooleanField(default=True)
    sms_notifications_enabled = models.BooleanField(default=False)
    
    # Maintenance mode
    is_maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True)
    
    # Contact
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=15, blank=True)
    
    last_updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='system_config_changes')

    class Meta:
        verbose_name_plural = 'System Configuration'

    def __str__(self):
        return "System Configuration"


# ===============================================
#          PLATFORM ACTIVITY LOG
# ===============================================

class ActivityLog(models.Model):
    """Log all significant platform activities"""
    ACTIVITY_TYPES = [
        ('user_registration', 'User Registration'),
        ('vendor_approval', 'Vendor Approval'),
        ('order_placed', 'Order Placed'),
        ('payment_processed', 'Payment Processed'),
        ('refund_issued', 'Refund Issued'),
        ('dispute_created', 'Dispute Created'),
        ('admin_action', 'Admin Action'),
        ('system_event', 'System Event'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs')
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    description = models.TextField()
    
    related_order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    related_vendor = models.ForeignKey(VendorProfile, on_delete=models.SET_NULL, null=True, blank=True)
    related_agent = models.ForeignKey(DeliveryAgentProfile, on_delete=models.SET_NULL, null=True, blank=True)
    
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=500, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['activity_type', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.activity_type} - {self.created_at}"