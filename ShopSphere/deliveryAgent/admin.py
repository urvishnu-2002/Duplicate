from django.contrib import admin
from .models import (
    DeliveryAgentProfile, DeliveryAssignment, DeliveryTracking,
    DeliveryCommission, DeliveryPayment, DeliveryDailyStats, DeliveryFeedback
)

@admin.register(DeliveryAgentProfile)
class DeliveryAgentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'vehicle_type', 'city', 'approval_status', 'is_blocked', 'total_deliveries']
    list_filter = ['approval_status', 'is_blocked', 'vehicle_type', 'city']
    search_fields = ['user__username', 'user__email', 'phone_number']
    readonly_fields = ['created_at', 'updated_at', 'total_earnings', 'average_rating']
    fieldsets = (
        ('User Information', {'fields': ('user',)}),
        ('Personal Info', {'fields': ('phone_number', 'date_of_birth', 'address', 'city', 'state', 'postal_code')}),
        ('Vehicle Info', {'fields': ('vehicle_type', 'vehicle_number')}),
        ('Documents', {'fields': ('license_number', 'license_expires', 'id_type', 'id_number')}),
        ('Bank Details', {'fields': ('bank_holder_name', 'bank_account_number', 'bank_ifsc_code', 'bank_name')}),
        ('Approval & Status', {'fields': ('approval_status', 'rejection_reason', 'availability_status', 'is_active', 'is_blocked', 'blocked_reason')}),
        ('Service Settings', {'fields': ('service_cities', 'preferred_delivery_radius', 'working_hours_start', 'working_hours_end')}),
        ('Statistics', {'fields': ('total_deliveries', 'completed_deliveries', 'cancelled_deliveries', 'average_rating', 'total_reviews', 'total_earnings'), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at', 'approved_at', 'last_online'), 'classes': ('collapse',)}),
    )

@admin.register(DeliveryAssignment)
class DeliveryAssignmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'agent', 'order', 'status', 'estimated_delivery_date', 'assigned_at']
    list_filter = ['status', 'assigned_at', 'estimated_delivery_date']
    search_fields = ['agent__user__username', 'order__id']
    readonly_fields = ['assigned_at', 'accepted_at', 'started_at', 'completed_at']

@admin.register(DeliveryTracking)
class DeliveryTrackingAdmin(admin.ModelAdmin):
    list_display = ['delivery_assignment', 'latitude', 'longitude', 'status', 'tracked_at']
    list_filter = ['status', 'tracked_at']
    search_fields = ['delivery_assignment__order__id']

@admin.register(DeliveryCommission)
class DeliveryCommissionAdmin(admin.ModelAdmin):
    list_display = ['agent', 'total_commission', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['agent__user__username']

@admin.register(DeliveryPayment)
class DeliveryPaymentAdmin(admin.ModelAdmin):
    list_display = ['agent', 'amount', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['agent__user__username', 'transaction_id']

@admin.register(DeliveryDailyStats)
class DeliveryDailyStatsAdmin(admin.ModelAdmin):
    list_display = ['agent', 'date', 'total_deliveries_completed', 'total_earnings']
    list_filter = ['date', 'agent']
    search_fields = ['agent__user__username']

@admin.register(DeliveryFeedback)
class DeliveryFeedbackAdmin(admin.ModelAdmin):
    list_display = ['agent', 'customer', 'overall_rating', 'is_complaint', 'created_at']
    list_filter = ['overall_rating', 'is_complaint', 'created_at']
    search_fields = ['agent__user__username', 'customer__username']
