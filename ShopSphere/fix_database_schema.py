"""
Comprehensive database schema fix script
Fixes both vendor and superAdmin migration issues
"""
import os
import django
import sqlite3

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopSphere.settings')
django.setup()

from django.conf import settings
from django.db import connection

def get_table_columns(table_name):
    """Get all column names for a table"""
    with connection.cursor() as cursor:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
    return columns

def fix_vendor_table():
    """Add missing columns to vendor_vendorprofile table"""
    print("\n=== Fixing vendor_vendorprofile table ===")
    
    existing_columns = get_table_columns('vendor_vendorprofile')
    print(f"Existing columns: {existing_columns}")
    
    columns_to_add = {
        'id_proof_data': 'BLOB',
        'id_proof_name': 'VARCHAR(255)',
        'id_proof_mimetype': 'VARCHAR(100)',
        'pan_card_data': 'BLOB',
        'pan_card_name': 'VARCHAR(255)',
        'pan_card_mimetype': 'VARCHAR(100)',
    }
    
    with connection.cursor() as cursor:
        for column_name, column_type in columns_to_add.items():
            if column_name not in existing_columns:
                sql = f"ALTER TABLE vendor_vendorprofile ADD COLUMN {column_name} {column_type};"
                try:
                    cursor.execute(sql)
                    print(f"✓ Added column: {column_name}")
                except Exception as e:
                    print(f"✗ Error adding {column_name}: {e}")
            else:
                print(f"⊘ Column already exists: {column_name}")

def check_superadmin_tables():
    """Check if superAdmin tables have the required columns"""
    print("\n=== Checking superAdmin tables ===")
    
    tables = ['superAdmin_vendorapprovallog', 'superAdmin_productapprovallog']
    
    for table in tables:
        try:
            columns = get_table_columns(table)
            print(f"\n{table} columns: {columns}")
            
            if 'admin_user_id' in columns:
                print(f"✓ {table} already has admin_user_id column")
            else:
                print(f"✗ {table} is missing admin_user_id column")
        except Exception as e:
            print(f"✗ Error checking {table}: {e}")

def main():
    print("=" * 60)
    print("DATABASE SCHEMA FIX SCRIPT")
    print("=" * 60)
    
    # Fix vendor table
    fix_vendor_table()
    
    # Check superAdmin tables
    check_superadmin_tables()
    
    print("\n" + "=" * 60)
    print("✓ Schema analysis completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. If superAdmin tables already have admin_user_id, run:")
    print("   python manage.py migrate superAdmin --fake")
    print("   python manage.py migrate user --fake")
    print("2. Then restart the server")

if __name__ == "__main__":
    main()
