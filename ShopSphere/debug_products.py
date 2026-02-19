import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopSphere.settings')
django.setup()

from vendor.models import Product

products = Product.objects.all()
print(f"Total products: {products.count()}")
for p in products:
    print(f"ID: {p.id}, Name: {p.name}, Category: {p.category}, Status: {p.status}, Blocked: {p.is_blocked}, Images: {p.images.count()}")

active_unblocked = Product.objects.filter(is_blocked=False, status='active')
print(f"\nActive and Unblocked Products: {active_unblocked.count()}")
for p in active_unblocked:
    print(f"ID: {p.id}, Name: {p.name}, Category: {p.category}")
