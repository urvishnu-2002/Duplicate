from rest_framework import serializers
from django.db.models import Sum, Avg
from .models import (
    DeliveryAgentProfile, DeliveryAssignment, DeliveryTracking,
    DeliveryCommission, DeliveryPayment, DeliveryDailyStats, DeliveryFeedback
)
from user.models import Order


# ===============================================
#       DELIVERY TRACKING SERIALIZER
# ===============================================

class DeliveryTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTracking
        fields = [
            'id', 'latitude', 'longitude', 'address', 'status',
            'speed', 'tracked_at', 'notes'
        ]
        read_only_fields = ['id', 'tracked_at']


# ===============================================
#     DELIVERY ASSIGNMENT SERIALIZER
# ===============================================

class DeliveryAssignmentListSerializer(serializers.ModelSerializer):
    """Delivery assignment listing serializer"""
    agent_name = serializers.CharField(source='agent.user.get_full_name', read_only=True)
    order_id = serializers.CharField(source='order.id', read_only=True)
    customer_name = serializers.CharField(source='order.user.get_full_name', read_only=True)
    items = serializers.SerializerMethodField()
    
    class Meta:
        model = DeliveryAssignment
        fields = [
            'id', 'agent_name', 'order_id', 'customer_name',
            'delivery_city', 'status', 'estimated_delivery_date',
            'pickup_time', 'delivery_time', 'delivery_fee', 'assigned_at',
            'pickup_address', 'delivery_address', 'items'
        ]
        read_only_fields = ['id', 'assigned_at']

    def get_items(self, obj):
        items = obj.order.items.all()
        return [{
            'product_name': item.product_name,
            'quantity': item.quantity,
            'price': str(item.product_price),
            'subtotal': str(item.subtotal)
        } for item in items]


class DeliveryAssignmentDetailSerializer(serializers.ModelSerializer):
    """Detailed delivery assignment serializer"""
    agent = serializers.SerializerMethodField()
    order_details = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    tracking_history = DeliveryTrackingSerializer(many=True, read_only=True)
    
    class Meta:
        model = DeliveryAssignment
        fields = [
            'id', 'agent', 'order_details', 'items', 'status', 'pickup_address',
            'delivery_address', 'delivery_city', 'delivery_coordinates',
            'estimated_delivery_date', 'estimated_delivery_time', 'pickup_time',
            'delivery_time', 'attempts_count', 'special_instructions',
            'recipient_notes', 'current_location', 'route_distance',
            'delivery_fee', 'customer_contact', 'agent_contact_allowed',
            'assigned_at', 'accepted_at', 'started_at', 'completed_at',
            'signature_image', 'delivery_photo', 'otp_verified',
            'tracking_history'
        ]
        read_only_fields = [
            'id', 'assigned_at', 'accepted_at', 'started_at', 'completed_at',
            'otp_verified', 'tracking_history'
        ]
    
    def get_agent(self, obj):
        return {
            'id': obj.agent.id,
            'name': obj.agent.user.get_full_name(),
            'vehicle_type': obj.agent.vehicle_type,
            'vehicle_number': obj.agent.vehicle_number,
            'rating': float(obj.agent.average_rating),
        }
    
    def get_items(self, obj):
        items = obj.order.items.all()
        return [{
            'product_name': item.product_name,
            'quantity': item.quantity,
            'price': str(item.product_price),
            'subtotal': str(item.subtotal)
        } for item in items]
    
    def get_order_details(self, obj):
        return {
            'id': obj.order.id,
            'customer': obj.order.customer.get_full_name(),
            'total_amount': str(obj.order.total_amount),
            'status': obj.order.status,
            'items_count': obj.order.items.count(),
        }


class DeliveryAssignmentCreateSerializer(serializers.ModelSerializer):
    """Create/update delivery assignment"""
    class Meta:
        model = DeliveryAssignment
        fields = [
            'order', 'pickup_address', 'delivery_address', 'delivery_city',
            'estimated_delivery_date', 'estimated_delivery_time',
            'special_instructions', 'customer_contact'
        ]


# ===============================================
#      DELIVERY FEEDBACK SERIALIZER
# ===============================================

class DeliveryFeedbackSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source='agent.user.get_full_name', read_only=True)
    
    class Meta:
        model = DeliveryFeedback
        fields = [
            'id', 'delivery_assignment', 'agent_name',
            'overall_rating', 'delivery_speed_rating', 'item_condition_rating',
            'behavior_rating', 'average_rating', 'comments', 'reported_issues',
            'is_complaint', 'complaint_details', 'created_at'
        ]
        read_only_fields = ['id', 'average_rating', 'created_at']


# ===============================================
#     DELIVERY COMMISSION SERIALIZER
# ===============================================

class DeliveryCommissionSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source='agent.user.get_full_name', read_only=True)
    
    class Meta:
        model = DeliveryCommission
        fields = [
            'id', 'agent_name', 'base_fee', 'distance_bonus', 'time_bonus',
            'rating_bonus', 'deductions', 'total_commission', 'status',
            'notes', 'created_at', 'approved_at', 'paid_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'approved_at', 'paid_at'
        ]


# ===============================================
#       DELIVERY PAYMENT SERIALIZER
# ===============================================

class DeliveryPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryPayment
        fields = [
            'id', 'payment_method', 'amount', 'from_date', 'to_date',
            'total_commissions', 'status', 'transaction_id', 'notes',
            'failed_reason', 'created_at', 'processed_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'processed_at', 'completed_at'
        ]


# ===============================================
#    DELIVERY DAILY STATS SERIALIZER
# ===============================================

class DeliveryDailyStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryDailyStats
        fields = [
            'id', 'date', 'total_deliveries_assigned', 'total_deliveries_completed',
            'total_deliveries_failed', 'total_hours_worked', 'average_delivery_time',
            'total_distance', 'average_distance_per_delivery', 'total_earnings',
            'total_bonus', 'customer_ratings_received', 'average_rating'
        ]
        read_only_fields = [
            'id', 'total_deliveries_assigned', 'total_deliveries_completed',
            'total_deliveries_failed', 'total_hours_worked', 'average_delivery_time',
            'total_distance', 'average_distance_per_delivery', 'total_earnings',
            'total_bonus', 'customer_ratings_received', 'average_rating'
        ]


# ===============================================
#    DELIVERY AGENT PROFILE SERIALIZER
# ===============================================

class DeliveryAgentProfileListSerializer(serializers.ModelSerializer):
    """Delivery agent listing serializer"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = DeliveryAgentProfile
        fields = [
            'id', 'user_name', 'user_email', 'vehicle_type', 'city',
            'approval_status', 'availability_status', 'is_blocked',
            'total_deliveries', 'completed_deliveries', 'average_rating',
            'total_earnings', 'created_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'total_deliveries', 'completed_deliveries',
            'average_rating', 'total_earnings'
        ]


class DeliveryAgentProfileDetailSerializer(serializers.ModelSerializer):
    """Detailed delivery agent profile serializer"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    pending_commission = serializers.SerializerMethodField()
    active_orders = serializers.SerializerMethodField()
    
    class Meta:
        model = DeliveryAgentProfile
        fields = [
            'id', 'user_name', 'full_name', 'user_email', 'phone_number', 'date_of_birth',
            'address', 'city', 'state', 'postal_code', 'vehicle_type',
            'vehicle_number', 'license_number', 'license_expires', 'id_type',
            'id_number', 'bank_holder_name', 'bank_account_number',
            'bank_ifsc_code', 'bank_name', 'approval_status', 'rejection_reason',
            'availability_status', 'is_active', 'is_blocked', 'blocked_reason',
            'service_cities', 'preferred_delivery_radius', 'working_hours_start',
            'working_hours_end', 'total_deliveries', 'completed_deliveries',
            'cancelled_deliveries', 'average_rating', 'total_reviews',
            'total_earnings', 'pending_commission', 'active_orders',
            'created_at', 'updated_at', 'approved_at', 'last_online'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'approved_at', 'last_online',
            'total_deliveries', 'completed_deliveries', 'cancelled_deliveries',
            'average_rating', 'total_reviews', 'total_earnings'
        ]
    
    def get_pending_commission(self, obj):
        return str(obj.get_pending_commission())
    
    def get_active_orders(self, obj):
        return obj.get_current_active_orders()


class DeliveryAgentProfileCreateSerializer(serializers.ModelSerializer):
    """Agent registration/creation serializer"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = DeliveryAgentProfile
        fields = [
            'phone_number', 'date_of_birth', 'address', 'city', 'state',
            'postal_code', 'vehicle_type', 'vehicle_number', 'license_number',
            'license_expires', 'id_type', 'id_number', 'bank_holder_name',
            'bank_account_number', 'bank_ifsc_code', 'bank_name',
            'service_cities', 'preferred_delivery_radius', 'password',
            'password_confirm'
        ]
        extra_kwargs = {
            'date_of_birth': {'required': False},
            'address': {'required': False},
            'city': {'required': False},
            'state': {'required': False},
            'postal_code': {'required': False},
            'vehicle_number': {'required': False},
            'license_expires': {'required': False},
            'id_type': {'required': False},
            'id_number': {'required': False},
            'bank_holder_name': {'required': False},
            'bank_account_number': {'required': False},
            'bank_ifsc_code': {'required': False},
            'bank_name': {'required': False},
            'vehicle_type': {'required': False},
            'license_number': {'required': False},
            'service_cities': {'required': False},
            'preferred_delivery_radius': {'required': False},
        }
    
    def validate(self, data):
        password = data.get('password')
        password_confirm = data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        
        email = self.context.get('email') or data.get('email')
        if not email:
            raise serializers.ValidationError({"email": "Email is required"})
            
        # Check if email is already registered and role
        from user.models import AuthUser
        user = AuthUser.objects.filter(email=email).first()
        if user:
            if user.role == 'delivery':
                raise serializers.ValidationError({"email": "This account is already registered as a delivery agent."})
            if user.role == 'admin':
                raise serializers.ValidationError({"email": "This email belongs to an administrator."})
            # If customer, we can upgrade them later in create()
            
        # Check phone number uniqueness if creating new user or if phone belongs to another user
        phone_number = data.get('phone_number')
        if phone_number:
            phone_user = AuthUser.objects.filter(phone=phone_number).first()
            if phone_user and (not user or phone_user != user):
                raise serializers.ValidationError({"phone_number": "This phone number is already registered to another account."})
        
        # Add email to data for use in create()
        data['email'] = email
        return data
    
    def create(self, validated_data):
        # Clean up password fields
        password_confirm = validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')
        email = validated_data.pop('email')
        phone_number = validated_data.get('phone_number')
        
        # Generator for unique dummy license if missing or empty
        import time
        import random
        timestamp = int(time.time())
        rand_suffix = random.randint(1000, 9999)
        dummy_license = f"TEMP-LIC-{timestamp}-{rand_suffix}"

        # If license_number is empty string, remove it so default dummy applies
        if 'license_number' in validated_data and not validated_data['license_number']:
            validated_data.pop('license_number')

        # Provide defaults for required model fields if missing
        defaults = {
            'date_of_birth': None,
            'address': 'Not Provided',
            'city': 'Not Provided',
            'state': 'Not Provided',
            'postal_code': '000000',
            'vehicle_type': 'motorcycle',
            'vehicle_number': 'PENDING',
            'license_number': dummy_license,
            'license_expires': '2030-01-01', # Default future date
            'id_type': 'aadhar',
            'id_number': 'PENDING',
            'bank_holder_name': 'PENDING',
            'bank_account_number': 'PENDING',
            'bank_ifsc_code': 'PENDING',
            'bank_name': 'PENDING',
            'service_cities': [],
            'preferred_delivery_radius': 5
        }
        
        # Merge defaults with validated_data (validated_data takes precedence)
        for key, value in defaults.items():
            if key not in validated_data:
                validated_data[key] = value

        from user.models import AuthUser
        from django.db import transaction

        try:
            with transaction.atomic():
                # Get or Create Auth User
                user = AuthUser.objects.filter(email=email).first()
                if user:
                    # Update existing user role
                    if user.role == 'customer':
                        user.role = 'delivery'
                        if phone_number:
                            user.phone = phone_number
                        # Optionally update password? Let's say yes for this flow
                        user.set_password(password)
                        user.save()
                    else:
                        # Should have been caught in validate, but safety first
                        raise serializers.ValidationError({"error": f"Cannot register user with role '{user.role}' as delivery agent."})
                else:
                    # Create new user
                    user = AuthUser.objects.create_user(
                        username=f"agent_{phone_number}" if phone_number else email.split('@')[0],
                        email=email,
                        password=password,
                        phone=phone_number
                    )
                    user.role = 'delivery'
                    user.save()
                
                # Check if profile exists
                if DeliveryAgentProfile.objects.filter(user=user).exists():
                    # If they are already a delivery agent, validate should have caught it,
                    # but maybe they are a customer who already tried to register?
                    # Let's just update the profile
                    profile = DeliveryAgentProfile.objects.get(user=user)
                    for attr, value in validated_data.items():
                        setattr(profile, attr, value)
                    profile.save()
                    return profile
                
                # Create Profile
                agent = DeliveryAgentProfile.objects.create(user=user, **validated_data)
                return agent
        except Exception as e:
            if "UNIQUE constraint failed: deliveryAgent_deliveryagentprofile.license_number" in str(e):
                # Retry with another dummy license if it was a collision
                validated_data['license_number'] = f"RETRY-{dummy_license}"
                return self.create(validated_data) # Be careful with recursion
            raise serializers.ValidationError({"error": str(e)})


# ===============================================
#      DELIVERY AGENT DASHBOARD SERIALIZER
# ===============================================

class DeliveryAgentDashboardSerializer(serializers.Serializer):
    """Comprehensive delivery agent dashboard data"""
    profile = serializers.SerializerMethodField()
    active_assignments = serializers.SerializerMethodField()
    today_stats = serializers.SerializerMethodField()
    recent_feedback = serializers.SerializerMethodField()
    pending_commissions = serializers.SerializerMethodField()

    def get_profile(self, obj):
        return DeliveryAgentProfileDetailSerializer(obj).data
    
    def get_pending_commissions(self, obj):
        """Get list of pending commissions"""
        pending = DeliveryCommission.objects.filter(
            agent=obj,
            status='pending'
        ).order_by('-created_at')[:10]
        return DeliveryCommissionSerializer(pending, many=True).data
    
    def get_active_assignments(self, obj):
        """Get currently active delivery assignments"""
        active = DeliveryAssignment.objects.filter(
            agent=obj,
            status__in=['accepted', 'picked_up', 'in_transit']
        ).order_by('-assigned_at')[:5]
        return DeliveryAssignmentListSerializer(active, many=True).data
    
    def get_today_stats(self, obj):
        """Get today's statistics"""
        from django.utils import timezone
        today = timezone.now().date()
        stats = DeliveryDailyStats.objects.filter(
            agent=obj,
            date=today
        ).first()
        
        if stats:
            return DeliveryDailyStatsSerializer(stats).data
        
        return {
            'total_deliveries_assigned': 0,
            'total_deliveries_completed': 0,
            'total_earnings': '0.00',
        }
    
    def get_recent_feedback(self, obj):
        """Get recent customer feedback"""
        feedback = DeliveryFeedback.objects.filter(
            agent=obj
        ).order_by('-created_at')[:5]
        return DeliveryFeedbackSerializer(feedback, many=True).data
