"""
Simple script to add missing columns to vendor_vendorprofile
"""
import sqlite3
import os

# Path to database
db_path = 'db.sqlite3'

if not os.path.exists(db_path):
    print(f"Error: Database file {db_path} not found!")
    exit(1)

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get existing columns
cursor.execute("PRAGMA table_info(vendor_vendorprofile)")
existing_columns = [row[1] for row in cursor.fetchall()]
print(f"Existing columns in vendor_vendorprofile: {existing_columns}\n")

# Columns to add
columns_to_add = [
    ('id_proof_data', 'BLOB'),
    ('id_proof_name', 'VARCHAR(255)'),
    ('id_proof_mimetype', 'VARCHAR(100)'),
    ('pan_card_data', 'BLOB'),
    ('pan_card_name', 'VARCHAR(255)'),
    ('pan_card_mimetype', 'VARCHAR(100)'),
]

# Add missing columns
for column_name, column_type in columns_to_add:
    if column_name not in existing_columns:
        try:
            sql = f"ALTER TABLE vendor_vendorprofile ADD COLUMN {column_name} {column_type}"
            cursor.execute(sql)
            conn.commit()
            print(f"✓ Added column: {column_name} ({column_type})")
        except sqlite3.OperationalError as e:
            print(f"✗ Error adding {column_name}: {e}")
    else:
        print(f"⊘ Column already exists: {column_name}")

# Verify columns were added
cursor.execute("PRAGMA table_info(vendor_vendorprofile)")
final_columns = [row[1] for row in cursor.fetchall()]
print(f"\nFinal columns in vendor_vendorprofile: {final_columns}")

# Check superAdmin tables
print("\n" + "="*60)
print("Checking superAdmin tables...")
print("="*60)

for table in ['superAdmin_vendorapprovallog', 'superAdmin_productapprovallog']:
    try:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        has_admin_user = 'admin_user_id' in columns
        print(f"\n{table}:")
        print(f"  Columns: {columns}")
        print(f"  Has admin_user_id: {'✓ YES' if has_admin_user else '✗ NO'}")
    except sqlite3.OperationalError as e:
        print(f"\n{table}: ✗ Table not found or error: {e}")

conn.close()
print("\n✓ Done!")
