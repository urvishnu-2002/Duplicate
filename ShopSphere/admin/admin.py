from django.contrib import admin

# The default admin app doesn't need to register models
# VendorProfile and Product are registered in vendor/admin.py
# VendorApprovalLog and ProductApprovalLog are registered in superAdmin/admin.py
#
# This admin app is for general system administration views
# Model admin configuration is handled in the individual app admin.py files
