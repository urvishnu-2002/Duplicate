from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, Permission

class Agent(AbstractUser):
    mobile = models.CharField(max_length=15, blank=True, null=True)
    license_number = models.CharField(max_length=50, blank=True, null=True)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    vehicle_type = models.CharField(max_length=20, blank=True, null=True)

    groups = models.ManyToManyField(Group, related_name="agent_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="agent_permissions", blank=True)

    def __str__(self):
        return self.username


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
