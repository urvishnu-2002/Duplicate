import sqlite3
from sqlite3 import Error
import random
from datetime import datetime

def create_connection(db_file):
    """ 
    Create a database connection to the SQLite database specified by db_file.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def create_table(conn):
    """ 
    Create the 'vendor_product' table.
    """
    try:
        sql_create_products_table = """
            CREATE TABLE IF NOT EXISTS vendor_product (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL,
                quantity INTEGER,
                status TEXT,
                is_blocked BOOLEAN DEFAULT 0,
                blocked_reason TEXT,
                created_at TEXT,
                updated_at TEXT,
                category_id INTEGER,
                vendor_id INTEGER
            );
        """
        c = conn.cursor()
        c.execute(sql_create_products_table)
        print("Table 'vendor_product' checked/created successfully.")
    except Error as e:
        print(f"Error creating table: {e}")

def insert_sample_products(conn):
    """ 
    Insert sample products for vendors with IDs 150-159.
    """
    products = []
    
    # Based on previous script: Customers (100-149), Vendors (150-159)
    vendor_ids = range(150, 160) 
    
    product_names = [
        "Smartphone", "Laptop", "Headphones", "Smart Watch", "Tablet", 
        "Camera", "Printer", "Monitor", "Keyboard", "Mouse",
        "T-Shirt", "Jeans", "Sneakers", "Jacket", "Backpack"
    ]
    
    statuses = ['active', 'active', 'active', 'out_of_stock'] # Weighted towards active
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    for vendor_id in vendor_ids:
        # Generate 5 products per vendor
        for i in range(1, 6):
            base_name = random.choice(product_names)
            name = f"{base_name} {vendor_id}-{i}"
            description = f"High quality {base_name} sold by Vendor {vendor_id}."
            price = round(random.uniform(10.0, 1000.0), 2)
            quantity = random.randint(0, 100)
            status = random.choice(statuses)
            category_id = random.randint(1, 5) # Assuming categories 1-5 exist
            
            # Tuple matching the columns (excluding ID)
            product_tuple = (
                name, description, price, quantity, status, 
                0, None, current_time, current_time, category_id, vendor_id
            )
            products.append(product_tuple)

    sql_insert_product = ''' 
        INSERT INTO vendor_product(name, description, price, quantity, status, is_blocked, blocked_reason, created_at, updated_at, category_id, vendor_id)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) 
    '''

    try:
        cur = conn.cursor()
        cur.executemany(sql_insert_product, products)
        conn.commit()
        print(f"Success! {cur.rowcount} products inserted.")
    except Error as e:
        print(f"Error inserting data: {e}")

def main():
    database = "db.sqlite3"

    conn = create_connection(database)
    if conn is not None:
        create_table(conn)
        insert_sample_products(conn)
        conn.close()
    else:
        print("Error! Cannot create the database connection.")

if __name__ == '__main__':
    main()