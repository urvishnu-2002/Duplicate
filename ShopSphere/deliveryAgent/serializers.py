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
    customer_name = serializers.CharField(source='order.customer.get_full_name', read_only=True)
    
    class Meta:
        model = DeliveryAssignment
        fields = [
            'id', 'agent_name', 'order_id', 'customer_name',
            'delivery_city', 'status', 'estimated_delivery_date',
            'pickup_time', 'delivery_time', 'delivery_fee', 'assigned_at'
        ]
        read_only_fields = ['id', 'assigned_at']


class DeliveryAssignmentDetailSerializer(serializers.ModelSerializer):
    """Detailed delivery assignment serializer"""
    agent = serializers.SerializerMethodField()
    order_details = serializers.SerializerMethodField()
    tracking_history = DeliveryTrackingSerializer(source='tracking_history', many=True, read_only=True)
    
    class Meta:
        model = DeliveryAssignment
        fields = [
            'id', 'agent', 'order_details', 'status', 'pickup_address',
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
    user_email = serializers.CharField(source='user.email', read_only=True)
    pending_commission = serializers.SerializerMethodField()
    active_orders = serializers.SerializerMethodField()
    
    class Meta:
        model = DeliveryAgentProfile
        fields = [
            'id', 'user_name', 'user_email', 'phone_number', 'date_of_birth',
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
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        from user.models import AuthUser
        
        password = validated_data.pop('password')
        user = AuthUser.objects.create_user(
            username=f"agent_{validated_data['phone_number']}",
            role='delivery_agent',
            email=self.context.get('email', ''),
            phone=validated_data['phone_number']
        )
        user.set_password(password)
        user.save()
        
        agent = DeliveryAgentProfile.objects.create(user=user, **validated_data)
        return agent


# ===============================================
#      DELIVERY AGENT DASHBOARD SERIALIZER
# ===============================================

class DeliveryAgentDashboardSerializer(serializers.Serializer):
    """Comprehensive delivery agent dashboard data"""
    profile = DeliveryAgentProfileDetailSerializer(source='*', read_only=True)
    active_assignments = serializers.SerializerMethodField()
    today_stats = serializers.SerializerMethodField()
    recent_feedback = serializers.SerializerMethodField()
    pending_commissions = DeliveryCommissionSerializer(many=True, read_only=True)
    
    def get_active_assignments(self, obj):
        """Get currently active delivery assignments"""
        active = DeliveryAssignment.objects.filter(
            agent=obj,
            status__in=['assigned', 'accepted', 'picked_up', 'in_transit']
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
