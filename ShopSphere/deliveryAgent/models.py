from django.db import models
from django.conf import settings

class DeliveryProfile(models.Model):
    """Delivery Partner Profile"""
    
    VEHICLE_CHOICES = [
        ('bike', 'Bike'),
        ('scooter', 'Scooter'),
        ('car', 'Car'),
        ('van', 'Van'),
        ('truck', 'Truck'),
    ]

    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_profile')
    
    # Personal & Vehicle Details
    address = models.TextField()
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_CHOICES)
    vehicle_number = models.CharField(max_length=20)
    driving_license_number = models.CharField(max_length=50)
    dl_image = models.FileField(upload_to='delivery_docs/license/', blank=True, null=True)
    
    # Bank Details
    bank_holder_name = models.CharField(max_length=100, blank=True, null=True)
    bank_account_number = models.CharField(max_length=20, blank=True, null=True)
    bank_ifsc_code = models.CharField(max_length=11, blank=True, null=True)
    
    # Status
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='pending')
    is_blocked = models.BooleanField(default=False)
    blocked_reason = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.vehicle_type}"

    @property
    def is_approved(self):
        return self.approval_status == 'approved'


class Order(models.Model):
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('ON_ROUTE', 'On Route'),
        ('DELIVERED', 'Delivered'),
    ]

    order_id = models.CharField(max_length=10, unique=True)
    customer_name = models.CharField(max_length=100)
    vendor_address = models.TextField()
    delivery_address = models.TextField()
    earning = models.DecimalField(max_digits=6, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='AVAILABLE')

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_orders'
    )

    def __str__(self):
        return self.order_id
