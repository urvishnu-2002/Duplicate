import sqlite3
import os

# Path to database
db_path = 'db.sqlite3'

if not os.path.exists(db_path):
    print(f"Error: Database file {db_path} not found!")
    exit(1)

# Connect to database
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

try:
    print("Starting schema fix for vendor_productimage...")

    # Check existing (new) columns
    cursor.execute("PRAGMA table_info(vendor_productimage)")
    columns = cursor.fetchall()
    col_dict = {col['name']: col['type'] for col in columns}
    col_names = list(col_dict.keys())
    print(f"Current columns: {col_names}")

    if 'image' not in col_names:
        print("✓ 'image' column not found. Table seems correct.")
        exit(0)
    else:
        print("⚠️ 'image' column found. Proceeding to fix schema.")

    # 1. Rename old table
    cursor.execute("PRAGMA foreign_keys=OFF")
    cursor.execute("ALTER TABLE vendor_productimage RENAME TO vendor_productimage_old")

    # 2. Create new table
    # Schema based on Django model:
    # product = ForeignKey(Product)
    # image_data = BinaryField(null=True)
    # image_name = CharField(max_length=255, null=True)
    # image_mimetype = CharField(max_length=100, null=True)
    # uploaded_at = DateTimeField(auto_now_add=True)

    create_sql = """
    CREATE TABLE vendor_productimage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        image_data BLOB,
        image_name VARCHAR(255),
        image_mimetype VARCHAR(100),
        uploaded_at DATETIME NOT NULL,
        FOREIGN KEY(product_id) REFERENCES vendor_product(id) DEFERRABLE INITIALLY DEFERRED
    )
    """
    cursor.execute(create_sql)

    # 3. Copy data
    # We migrate fields that exist in both tables.
    # 'image' column is intentionally SKIPPED.
    fields_Common = ['id', 'product_id', 'uploaded_at']
    if 'image_data' in col_names:
        fields_Common.append('image_data')
    if 'image_name' in col_names:
        fields_Common.append('image_name')
    if 'image_mimetype' in col_names:
        fields_Common.append('image_mimetype')

    fields_str = ", ".join(fields_Common)
    insert_sql = f"INSERT INTO vendor_productimage ({fields_str}) SELECT {fields_str} FROM vendor_productimage_old"
    
    cursor.execute(insert_sql)
    print(f"✓ Data migrated successfully. Fields: {fields_str}")

    # 4. Drop old table
    cursor.execute("DROP TABLE vendor_productimage_old")
    print("✓ Old table dropped.")

    conn.commit()
    print("✓ Schema fix completed successfully!")

    # Verify
    cursor.execute("PRAGMA table_info(vendor_productimage)")
    new_columns = cursor.fetchall()
    new_col_names = [col['name'] for col in new_columns]
    print(f"New columns: {new_col_names}")

except Exception as e:
    conn.rollback()
    print(f"✗ Error during schema fix: {e}")
    # Restore attempt
    try:
        cursor.execute("DROP TABLE IF EXISTS vendor_productimage")
        cursor.execute("ALTER TABLE vendor_productimage_old RENAME TO vendor_productimage")
        conn.commit()
        print("⚠️ Rolled back changes.")
    except Exception as rollback_err:
        print(f"✗ Rollback failed: {rollback_err}")

finally:
    conn.close()
