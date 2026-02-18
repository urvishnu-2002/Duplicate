from django.contrib import admin
from .models import DeliveryProfile, Order

class DeliveryProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'vehicle_type', 'approval_status')
    list_filter = ('vehicle_type', 'approval_status')
    search_fields = ('user__username', 'vehicle_number')

admin.site.register(DeliveryProfile, DeliveryProfileAdmin)
admin.site.register(Order)