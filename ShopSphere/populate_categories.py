"""
Script to populate Category model from existing choices and link products
"""
import os
import django
from django.utils.text import slugify

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopSphere.settings')
django.setup()

from vendor.models import Product, Category

def populate_categories():
    print("Starting category migration...")
    
    # Get choices from Product model
    choices = Product.CATEGORY_CHOICES
    
    # Create categories
    category_map = {}
    for code, name in choices:
        slug = slugify(name)
        category, created = Category.objects.get_or_create(
            slug=slug,
            defaults={'name': name}
        )
        category_map[code] = category
        if created:
            print(f"✓ Created category: {name}")
        else:
            print(f"• Found category: {name}")
            
    # Link existing products
    products = Product.objects.all()
    count = 0
    for product in products:
        if product.category in category_map:
            product.new_category = category_map[product.category]
            product.save()
            count += 1
            
    print(f"\n✓ Linked {count} products to new categories.")

if __name__ == "__main__":
    populate_categories()
