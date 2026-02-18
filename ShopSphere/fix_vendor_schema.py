"""
Script to fix vendor_vendorprofile table schema by adding missing columns
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopSphere.settings')
django.setup()

from django.db import connection

def add_missing_columns():
    """Add missing columns to vendor_vendorprofile table"""
    with connection.cursor() as cursor:
        # List of columns to add
        columns_to_add = [
            "ALTER TABLE vendor_vendorprofile ADD COLUMN id_proof_data BLOB;",
            "ALTER TABLE vendor_vendorprofile ADD COLUMN id_proof_name VARCHAR(255);",
            "ALTER TABLE vendor_vendorprofile ADD COLUMN id_proof_mimetype VARCHAR(100);",
            "ALTER TABLE vendor_vendorprofile ADD COLUMN pan_card_data BLOB;",
            "ALTER TABLE vendor_vendorprofile ADD COLUMN pan_card_name VARCHAR(255);",
            "ALTER TABLE vendor_vendorprofile ADD COLUMN pan_card_mimetype VARCHAR(100);",
        ]
        
        for sql in columns_to_add:
            try:
                cursor.execute(sql)
                print(f"✓ Successfully executed: {sql}")
            except Exception as e:
                # Column might already exist
                if "duplicate column name" in str(e).lower():
                    print(f"⊘ Column already exists: {sql}")
                else:
                    print(f"✗ Error executing {sql}: {e}")
    
    print("\n✓ Schema fix completed!")

if __name__ == "__main__":
    add_missing_columns()
