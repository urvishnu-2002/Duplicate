"""
Check and fix ProductImage table schema completely
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

# Get existing columns with full details
cursor.execute("PRAGMA table_info(vendor_productimage)")
columns = cursor.fetchall()

print("Current vendor_productimage table structure:")
print("=" * 70)
for col in columns:
    col_id, name, col_type, not_null, default, pk = col
    print(f"  {name:20} {col_type:15} NOT NULL: {bool(not_null):5} PK: {bool(pk):5}")
print("=" * 70)

# Check if old 'image' column exists
has_old_image = any(col[1] == 'image' for col in columns)
has_image_data = any(col[1] == 'image_data' for col in columns)

print(f"\nHas old 'image' column: {has_old_image}")
print(f"Has new 'image_data' column: {has_image_data}")

if has_old_image:
    print("\n⚠️  Old 'image' column exists and is causing conflicts!")
    print("    The table needs to be recreated with the correct schema.")
    
    # Check if there's any data
    cursor.execute("SELECT COUNT(*) FROM vendor_productimage")
    count = cursor.fetchone()[0]
    print(f"    Current rows in table: {count}")
    
    if count == 0:
        print("\n✓ Table is empty, safe to recreate")
        print("\nRecreating table with correct schema...")
        
        # Drop the old table
        cursor.execute("DROP TABLE vendor_productimage")
        
        # Create new table with correct schema
        cursor.execute("""
            CREATE TABLE vendor_productimage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                image_data BLOB,
                image_name VARCHAR(255),
                image_mimetype VARCHAR(100),
                uploaded_at DATETIME NOT NULL,
                FOREIGN KEY (product_id) REFERENCES vendor_product(id)
            )
        """)
        
        conn.commit()
        print("✓ Table recreated successfully!")
        
        # Verify new structure
        cursor.execute("PRAGMA table_info(vendor_productimage)")
        new_columns = cursor.fetchall()
        print("\nNew table structure:")
        print("=" * 70)
        for col in new_columns:
            col_id, name, col_type, not_null, default, pk = col
            print(f"  {name:20} {col_type:15} NOT NULL: {bool(not_null):5} PK: {bool(pk):5}")
        print("=" * 70)
    else:
        print("\n⚠️  Table has data! Manual migration needed.")
        print("    Please backup your data before proceeding.")

conn.close()
print("\n✓ Done!")
