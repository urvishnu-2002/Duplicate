import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopSphere.settings')
django.setup()

from user.models import Order, OrderItem
from vendor.models import VendorProfile

print("--- Orders ---")
orders = Order.objects.all()
print(f"Total Orders: {orders.count()}")
for o in orders:
    print(f"Order: {o.order_number}, User: {o.user.email}, Status: {o.status}, Total: {o.total_amount}")
    for item in o.items.all():
        print(f"  - Item: {item.product_name}, Vendor: {item.vendor}, Status: {item.vendor_status}, Subtotal: {item.subtotal}")

print("\n--- Vendor Profiles ---")
vendors = VendorProfile.objects.all()
for v in vendors:
    print(f"Vendor: {v.shop_name}, User: {v.user.email}, ID: {v.id}")
