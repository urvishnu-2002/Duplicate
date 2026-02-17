from django.contrib import admin
from .models import VendorApprovalLog, ProductApprovalLog, DeliveryAgentApprovalLog

@admin.register(VendorApprovalLog)
class VendorApprovalLogAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'action', 'admin_user', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('vendor__shop_name', 'reason')
    readonly_fields = ('timestamp',)

@admin.register(ProductApprovalLog)
class ProductApprovalLogAdmin(admin.ModelAdmin):
    list_display = ('product', 'action', 'admin_user', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('product__name', 'reason')
    readonly_fields = ('timestamp',)

@admin.register(DeliveryAgentApprovalLog)
class DeliveryAgentApprovalLogAdmin(admin.ModelAdmin):
    list_display = ('agent', 'action', 'admin_user', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('agent__name', 'reason')
    readonly_fields = ('timestamp',)