from django.db import models
from django.conf import settings
from django.utils import timezone
from vendor.models import VendorProfile, Product

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
