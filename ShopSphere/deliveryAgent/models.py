from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, Avg
from decimal import Decimal


# ===============================================
#        DELIVERY AGENT PROFILE MODEL
# ===============================================

class DeliveryAgentProfile(models.Model):
    """Delivery Agent Profile for order delivery management"""
    
    VEHICLE_CHOICES = [
        ('bicycle', 'Bicycle'),
        ('motorcycle', 'Motorcycle'),
        ('scooter', 'Scooter'),
        ('car', 'Car'),
        ('van', 'Van'),
        ('truck', 'Truck'),
        ('on_foot', 'On Foot'),
    ]
    
    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    AVAILABILITY_CHOICES = [
        ('available', 'Available'),
        ('on_delivery', 'On Delivery'),
        ('on_break', 'On Break'),
        ('offline', 'Offline'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_agent_profile')
    
    # Personal Information
    date_of_birth = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    postal_code = models.CharField(max_length=10)
    
    # Vehicle Information
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_CHOICES)
    vehicle_number = models.CharField(max_length=20, blank=True, null=True)
    vehicle_registration = models.FileField(upload_to='vehicle_docs/', blank=True, null=True)
    vehicle_insurance = models.FileField(upload_to='vehicle_docs/', blank=True, null=True)
    
    # License & Documentation
    license_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    license_file = models.FileField(upload_to='license_docs/', blank=True, null=True)
    license_expires = models.DateField(blank=True, null=True)
    
    # Identity Verification
    id_type = models.CharField(max_length=20, default='aadhar', choices=[
        ('aadhar', 'Aadhar'),
        ('passport', 'Passport'),
        ('pan', 'PAN'),
        ('drivers_license', 'Driver\'s License'),
    ])
    id_number = models.CharField(max_length=50, blank=True, null=True)
    id_proof_file = models.FileField(upload_to='id_proofs/', blank=True, null=True)
    
    # Bank Details for Payout
    bank_holder_name = models.CharField(max_length=100)
    bank_account_number = models.CharField(max_length=20)
    bank_ifsc_code = models.CharField(max_length=11)
    bank_name = models.CharField(max_length=100)
    
    # Approval & Status
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)
    availability_status = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='offline')
    
    # Performance Metrics
    is_active = models.BooleanField(default=True)
    is_blocked = models.BooleanField(default=False)
    blocked_reason = models.TextField(blank=True, null=True)
    
    # Service Area
    service_cities = models.JSONField(default=list, help_text="List of cities where agent provides service")
    preferred_delivery_radius = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="Preferred delivery radius in kilometers"
    )
    
    # Operational Info
    working_hours_start = models.TimeField(null=True, blank=True)
    working_hours_end = models.TimeField(null=True, blank=True)
    
    # Statistics (denormalized for performance)
    total_deliveries = models.IntegerField(default=0)
    completed_deliveries = models.IntegerField(default=0)
    cancelled_deliveries = models.IntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.00), MaxValueValidator(5.00)]
    )
    total_reviews = models.IntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Last online
    last_online = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['approval_status']),
            models.Index(fields=['availability_status']),
            models.Index(fields=['is_blocked']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.vehicle_type}"
    
    @property
    def is_approved(self):
        return self.approval_status == 'approved'
    
    def get_current_active_orders(self):
        """Get active orders assigned to this agent"""
        return DeliveryAssignment.objects.filter(
            agent=self,
            status__in=['assigned', 'picked_up', 'in_transit']
        ).count()
    
    def get_pending_commission(self):
        """Get total commission pending payout"""
        return DeliveryCommission.objects.filter(
            agent=self,
            status='pending'
        ).aggregate(Sum('total_commission'))['total_commission__sum'] or Decimal('0.00')


# ===============================================
#      DELIVERY ASSIGNMENT MODEL
# ===============================================

class DeliveryAssignment(models.Model):
    """Assignment of orders to delivery agents"""
    
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('attempting_delivery', 'Attempting Delivery'),
        ('delivered', 'Delivered'),
        ('failed', 'Delivery Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Assignment Details
    agent = models.ForeignKey(DeliveryAgentProfile, on_delete=models.PROTECT, related_name='delivery_assignments')
    order = models.OneToOneField('user.Order', on_delete=models.PROTECT, related_name='delivery_assignment')
    
    # Status Tracking
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='assigned')
    
    # Delivery Details
    pickup_address = models.TextField()
    delivery_address = models.TextField()
    delivery_city = models.CharField(max_length=50)
    delivery_coordinates = models.JSONField(default=dict, blank=True)  # {"latitude": x, "longitude": y}
    
    # Estimated Info
    estimated_delivery_date = models.DateField()
    estimated_delivery_time = models.TimeField(null=True, blank=True)
    
    # Actual Info
    pickup_time = models.DateTimeField(null=True, blank=True)
    delivery_time = models.DateTimeField(null=True, blank=True)
    attempts_count = models.IntegerField(default=0)
    
    # Special Instructions
    special_instructions = models.TextField(blank=True, null=True)
    recipient_notes = models.TextField(blank=True, null=True)
    
    # Tracking
    current_location = models.JSONField(default=dict, blank=True)  # Real-time GPS location
    route_distance = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)  # in km
    
    # Earnings
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Communication
    customer_contact = models.CharField(max_length=15, blank=True)
    agent_contact_allowed = models.BooleanField(default=True)
    
    # Timestamps
    assigned_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Proof of Delivery
    signature_image = models.ImageField(upload_to='delivery_proofs/', null=True, blank=True)
    delivery_photo = models.ImageField(upload_to='delivery_proofs/', null=True, blank=True)
    otp_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True)

    class Meta:
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['agent', 'status']),
            models.Index(fields=['order']),
            models.Index(fields=['-assigned_at']),
        ]

    def __str__(self):
        return f"Delivery: {self.order.id} - Agent: {self.agent.user.username}"
    
    def accept_delivery(self):
        """Mark delivery as accepted by agent"""
        self.status = 'accepted'
        self.accepted_at = timezone.now()
        self.save()
        
        # Update order status to shipping
        if self.order:
            self.order.status = 'shipping'
            self.order.save()
            
            # Transition all items to out_for_delivery status ONLY after agent accepts
            self.order.items.all().update(vendor_status='out_for_delivery')
    
    def start_delivery(self):
        """Mark delivery as started (picked up from vendor)"""
        self.status = 'picked_up'
        self.pickup_time = timezone.now()
        self.save()
    
    def mark_in_transit(self):
        """Mark as in transit to customer"""
        self.status = 'in_transit'
        self.save()
    
    def mark_delivered(self):
        """Mark delivery as completed, credit agent wallet and create commission record"""
        if self.status == 'delivered':
            return
            
        from user.models import UserWallet, Order, OrderItem, OrderTracking
        from .models import DeliveryCommission, DeliveryDailyStats
        
        self.delivery_time = timezone.now()
        self.completed_at = self.delivery_time
        self.status = 'delivered'
        self.save()

        # 1. Update order and item status
        if self.order:
            self.order.status = 'delivered'
            self.order.delivered_at = self.delivery_time
            self.order.save()
            
            # Update all items in the order to delivered
            self.order.items.all().update(vendor_status='delivered')

            # Add tracking record
            OrderTracking.objects.create(
                order=self.order,
                status='Delivered',
                location=self.delivery_city or 'City N/A',
                notes=f'Order delivered by agent {self.agent.user.username}'
            )

        # 2. Calculate Commission Based on Type (Local vs Out-of-city)
        fee = self.delivery_fee or Decimal('0.00')
        d_city = str(self.delivery_city or "City N/A").lower()
        a_city = str(self.agent.city or "Agent City N/A").lower()
        
        is_local = d_city == a_city
        
        distance_bonus = Decimal('0.00')
        if not is_local:
            # Out-of-city bonus: 20% of base fee
            distance_bonus = fee * Decimal('0.20')
        
        total_commission = fee + distance_bonus

        # Create commission record
        commission = DeliveryCommission.objects.create(
            agent=self.agent,
            delivery_assignment=self,
            base_fee=fee,
            distance_bonus=distance_bonus,
            total_commission=total_commission,
            status='approved',
            approved_at=timezone.now(),
            notes="Local Delivery" if is_local else "Out-of-city Delivery"
        )
        
        # 3. Credit agent's wallet
        wallet, created = UserWallet.objects.get_or_create(user=self.agent.user)
        wallet_desc = f"Delivery Commission for Order {self.order.order_number if self.order else 'N/A'}"
        wallet.add_balance(total_commission, wallet_desc)
        
        # 4. Update daily stats
        stats, created = DeliveryDailyStats.objects.get_or_create(
            agent=self.agent,
            date=timezone.now().date()
        )
        stats.total_deliveries_completed += 1
        stats.total_earnings += total_commission
        stats.save()
        
        # 5. Update agent profile stats
        self.agent.total_deliveries += 1
        self.agent.completed_deliveries += 1
        self.agent.total_earnings = (self.agent.total_earnings or Decimal('0.00')) + total_commission
        self.agent.save()
    
    def mark_failed(self):
        """Mark delivery as failed"""
        self.status = 'failed'
        self.attempts_count += 1
        self.save()


# ===============================================
#          DELIVERY TRACKING MODEL
# ===============================================

class DeliveryTracking(models.Model):
    """Real-time delivery tracking with location updates"""
    
    delivery_assignment = models.ForeignKey(DeliveryAssignment, on_delete=models.CASCADE, related_name='tracking_history')
    
    # Location Information
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    address = models.TextField(blank=True)
    
    # Tracking Status
    status = models.CharField(max_length=50)  # e.g., "Picked Up", "In Transit", "Arrived"
    speed = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # in km/h
    
    # Timestamp
    tracked_at = models.DateTimeField(auto_now_add=True)
    
    # Additional Info
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-tracked_at']
        indexes = [
            models.Index(fields=['delivery_assignment', '-tracked_at']),
            models.Index(fields=['-tracked_at']),
        ]
        verbose_name_plural = "Delivery Tracking Records"

    def __str__(self):
        return f"Tracking: {self.delivery_assignment.order.id} at {self.tracked_at}"


# ===============================================
#        DELIVERY COMMISSION MODEL
# ===============================================

class DeliveryCommission(models.Model):
    """Commission/earnings tracking for delivery agents"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]
    
    agent = models.ForeignKey(DeliveryAgentProfile, on_delete=models.CASCADE, related_name='delivery_commissions')
    delivery_assignment = models.ForeignKey(DeliveryAssignment, on_delete=models.SET_NULL, null=True, blank=True, related_name='commission')
    
    # Commission Details
    base_fee = models.DecimalField(max_digits=10, decimal_places=2)
    distance_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    time_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    rating_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    total_commission = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment = models.OneToOneField('DeliveryPayment', on_delete=models.SET_NULL, null=True, blank=True, related_name='commission')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['agent', 'status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Commission: {self.agent.user.username} - {self.total_commission}"
    
    def approve(self):
        """Approve pending commission"""
        if self.status == 'pending':
            self.status = 'approved'
            self.approved_at = timezone.now()
            self.save()


# ===============================================
#         DELIVERY PAYMENT MODEL
# ===============================================

class DeliveryPayment(models.Model):
    """Delivery agent payout/payment tracking"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('upi', 'UPI'),
        ('wallet', 'Wallet'),
    ]
    
    agent = models.ForeignKey(DeliveryAgentProfile, on_delete=models.CASCADE, related_name='payments')
    
    # Payment Details
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='bank_transfer')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Commission Batching
    from_date = models.DateField()
    to_date = models.DateField()
    total_commissions = models.IntegerField(default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    failed_reason = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Audit Trail
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='delivery_payments_processed',
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['agent', 'status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Payment: {self.agent.user.username} - {self.amount}"
    
    def mark_as_completed(self, transaction_id=None):
        """Mark payment as completed"""
        if self.status in ['pending', 'processing']:
            self.status = 'completed'
            self.completed_at = timezone.now()
            if transaction_id:
                self.transaction_id = transaction_id
            self.save()


# ===============================================
#  DELIVERY DAILY STATISTICS MODEL
# ===============================================

class DeliveryDailyStats(models.Model):
    """Daily statistics for delivery agents"""
    
    agent = models.ForeignKey(DeliveryAgentProfile, on_delete=models.CASCADE, related_name='daily_stats')
    date = models.DateField()
    
    # Delivery Metrics
    total_deliveries_assigned = models.IntegerField(default=0)
    total_deliveries_completed = models.IntegerField(default=0)
    total_deliveries_failed = models.IntegerField(default=0)
    
    # Time Metrics
    total_hours_worked = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    average_delivery_time = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)  # in minutes
    
    # Distance Metrics
    total_distance = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)  # in km
    average_distance_per_delivery = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    
    # Financial Metrics
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Rating Metrics
    customer_ratings_received = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['agent', '-date']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['agent', 'date'], name='unique_agent_daily_stats')
        ]
        verbose_name_plural = "Delivery Daily Statistics"

    def __str__(self):
        return f"{self.agent.user.username} - {self.date}"


# ===============================================
#      DELIVERY FEEDBACK/RATING MODEL
# ===============================================

class DeliveryFeedback(models.Model):
    """Customer feedback and ratings for delivery"""
    
    delivery_assignment = models.OneToOneField(DeliveryAssignment, on_delete=models.CASCADE, related_name='feedback')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_feedbacks')
    agent = models.ForeignKey(DeliveryAgentProfile, on_delete=models.CASCADE, related_name='feedbacks_received')
    
    # Rating Dimensions
    overall_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Overall delivery experience rating (1-5)"
    )
    delivery_speed_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Speed of delivery rating"
    )
    item_condition_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Condition of items upon delivery"
    )
    behavior_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Behavior and professionalism of agent"
    )
    
    # Feedback
    comments = models.TextField(blank=True, null=True)
    reported_issues = models.JSONField(default=list, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Is Complaint
    is_complaint = models.BooleanField(default=False)
    complaint_details = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['agent']),
            models.Index(fields=['customer']),
        ]

    def __str__(self):
        return f"Feedback: Order {self.delivery_assignment.order.id} - Rating {self.overall_rating}"
    
    @property
    def average_rating(self):
        """Calculate average of all rating dimensions"""
        return (self.overall_rating + self.delivery_speed_rating + 
                self.item_condition_rating + self.behavior_rating) / 4


# ===============================================
#          DELIVERY AGENT WALLET & EARNINGS
# ===============================================

class DeliveryAgentWallet(models.Model):
    """Wallet for delivery agent earnings"""
    agent = models.OneToOneField(DeliveryAgentProfile, on_delete=models.CASCADE, related_name='wallet')
    
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_withdrawn = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    payout_frequency = models.CharField(max_length=20, default='weekly', choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ])
    
    bank_account_name = models.CharField(max_length=255, blank=True, null=True)
    bank_account_number = models.CharField(max_length=20, blank=True, null=True)
    bank_ifsc = models.CharField(max_length=11, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet - {self.agent.user.username}"

    def add_earnings(self, amount, description=''):
        """Add earnings to wallet"""
        if amount > 0:
            self.current_balance += amount
            self.total_earnings += amount
            self.save()
            DeliveryAgentTransaction.objects.create(
                wallet=self,
                transaction_type='earning',
                amount=amount,
                description=description
            )
            return True
        return False

    def process_withdrawal(self, amount, description=''):
        """Process withdrawal from wallet"""
        if amount > 0 and self.current_balance >= amount:
            self.current_balance -= amount
            self.total_withdrawn += amount
            self.save()
            DeliveryAgentTransaction.objects.create(
                wallet=self,
                transaction_type='withdrawal',
                amount=amount,
                description=description
            )
            return True
        return False


class DeliveryAgentTransaction(models.Model):
    """Transaction history for delivery agents"""
    TRANSACTION_TYPES = [
        ('earning', 'Earning'),
        ('withdrawal', 'Withdrawal'),
        ('refund', 'Refund'),
        ('bonus', 'Bonus'),
    ]

    wallet = models.ForeignKey(DeliveryAgentWallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    reference_id = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.wallet.agent.user.username} - {self.transaction_type} ₹{self.amount}"


# ===============================================
#          DELIVERY AGENT PERFORMANCE RATING
# ===============================================

class DeliveryAgentPerformance(models.Model):
    """Performance metrics for delivery agents"""
    agent = models.OneToOneField(DeliveryAgentProfile, on_delete=models.CASCADE, related_name='performance')
    
    # Metrics
    total_deliveries = models.IntegerField(default=0)
    successful_deliveries = models.IntegerField(default=0)
    failed_deliveries = models.IntegerField(default=0)
    returned_deliveries = models.IntegerField(default=0)
    
    on_time_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    customer_satisfaction_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    average_delivery_time_minutes = models.IntegerField(default=0)
    
    # Safety metrics
    damaged_items_count = models.IntegerField(default=0)
    customer_complaints_count = models.IntegerField(default=0)
    
    # Status
    status = models.CharField(max_length=20, default='good', choices=[
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('poor', 'Poor'),
    ])
    
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Performance - {self.agent.user.username}"


# ===============================================
#          DELIVERY INCENTIVES & BONUSES
# ===============================================

class DeliveryIncentive(models.Model):
    """Incentives and bonuses for delivery agents"""
    INCENTIVE_TYPE_CHOICES = [
        ('daily_bonus', 'Daily Bonus'),
        ('milestone_bonus', 'Milestone Bonus'),
        ('performance_bonus', 'Performance Bonus'),
        ('safety_bonus', 'Safety Bonus'),
        ('special_promo', 'Special Promotion'),
    ]

    agent = models.ForeignKey(DeliveryAgentProfile, on_delete=models.CASCADE, related_name='incentives')
    
    incentive_type = models.CharField(max_length=30, choices=INCENTIVE_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    bonus_amount = models.DecimalField(max_digits=10, decimal_places=2)
    condition = models.CharField(max_length=500, blank=True)  # e.g., "Complete 10 deliveries"
    
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_till = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.incentive_type} - {self.agent.user.username}"