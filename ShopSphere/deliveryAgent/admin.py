from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Agent

class AgentAdmin(UserAdmin):
    model = Agent
    
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('mobile', 'license_number', 'company_name', 'vehicle_type')}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('mobile', 'license_number', 'company_name', 'vehicle_type')}),
    )

admin.site.register(Agent, AgentAdmin)