from django.apps import AppConfig
from django.utils.text import slugify

class VendorConfig(AppConfig):
    name = 'vendor'
    
    def ready(self):
        """Initialize default categories when app is ready"""
        # Commented out to avoid RuntimeWarning: Accessing the database during app initialization is discouraged.
        # Queries in ready() or when app modules are imported should be avoided.
        
        try:
            from vendor.models import Category, Product
            
            # Only create categories if they don't exist
            if Category.objects.exists():
                return
            
            print("Initializing product categories...")
            category_choices = Product.CATEGORY_CHOICES
            created_count = 0
            
            for code, name in category_choices:
                slug = slugify(name)
                category, created = Category.objects.get_or_create(
                    slug=slug,
                    defaults={'name': name}
                )
                
                if created:
                    print(f"✓ Created category: {name}")
                    created_count += 1
            
            if created_count > 0:
                print(f"✅ Categories initialized! ({created_count} new categories created)\n")
        except Exception as e:
            # Silently fail if tables don't exist yet (during migrations)
            pass
