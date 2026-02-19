import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopSphere.settings')
django.setup()

from vendor.models import Product, VendorProfile

print("--- Products ---")
for p in Product.objects.all():
    print(f"ID: {p.id}, Name: {p.name}, VendorID: {p.vendor_id}, Vendor: {p.vendor.shop_name}")

print("\n--- Vendors ---")
for v in VendorProfile.objects.all():
    print(f"ID: {v.id}, Shop: {v.shop_name}, UserEmail: {v.user.email}")
