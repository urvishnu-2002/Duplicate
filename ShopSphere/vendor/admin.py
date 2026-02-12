from django.contrib import admin
from .models import VendorProfile, Product


@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    list_display = ('shop_name', 'user', 'approval_status', 'gst_number', 'pan_number', 'bank_account_number', 'created_at')
    list_filter = ('approval_status', 'is_blocked', 'created_at', 'business_type')
    search_fields = ('shop_name', 'user__username', 'user__email', 'gst_number', 'pan_number')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'shop_name', 'shop_description', 'business_type', 'address', 'approval_status', 'rejection_reason')
        }),
        ('Identification', {
            'fields': ('gst_number', 'pan_number', 'pan_name', 'pan_card_file', 'id_type', 'id_number', 'id_proof_file')
        }),
        ('Financial Details', {
            'fields': ('bank_holder_name', 'bank_account_number', 'bank_ifsc_code', 'shipping_fee')
        }),
        ('Status', {
            'fields': ('is_blocked', 'blocked_reason', 'created_at', 'updated_at')
        }),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor', 'price', 'quantity', 'status', 'is_blocked', 'created_at')
    list_filter = ('status', 'is_blocked', 'created_at', 'vendor')
    search_fields = ('name', 'description', 'vendor__shop_name')
    readonly_fields = ('created_at', 'updated_at')