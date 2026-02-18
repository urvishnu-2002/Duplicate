"""
Fix ProductImage table schema by adding missing columns
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
cursor.execute("PRAGMA table_info(vendor_productimage)")
existing_columns = [row[1] for row in cursor.fetchall()]
print(f"Existing columns in vendor_productimage: {existing_columns}\n")

# Columns to add
columns_to_add = [
    ('image_data', 'BLOB'),
    ('image_name', 'VARCHAR(255)'),
    ('image_mimetype', 'VARCHAR(100)'),
]

# Add missing columns
for column_name, column_type in columns_to_add:
    if column_name not in existing_columns:
        try:
            sql = f"ALTER TABLE vendor_productimage ADD COLUMN {column_name} {column_type}"
            cursor.execute(sql)
            conn.commit()
            print(f"✓ Added column: {column_name} ({column_type})")
        except sqlite3.OperationalError as e:
            print(f"✗ Error adding {column_name}: {e}")
    else:
        print(f"⊘ Column already exists: {column_name}")

# Verify columns were added
cursor.execute("PRAGMA table_info(vendor_productimage)")
final_columns = [row[1] for row in cursor.fetchall()]
print(f"\nFinal columns in vendor_productimage: {final_columns}")

conn.close()
print("\n✓ Done!")
