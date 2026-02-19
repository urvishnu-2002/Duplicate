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
    Create the 'vendor_productimage' table if it doesn't exist.
    """
    try:
        sql_create_images_table = """
            CREATE TABLE IF NOT EXISTS vendor_productimage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_data BLOB,
                image_name TEXT,
                image_mimetype TEXT,
                uploaded_at TEXT,
                product_id INTEGER,
                FOREIGN KEY (product_id) REFERENCES vendor_product (id)
            );
        """
        c = conn.cursor()
        c.execute(sql_create_images_table)
        print("Table 'vendor_productimage' checked/created successfully.")
    except Error as e:
        print(f"Error creating table: {e}")

def get_product_ids(conn):
    """
    Fetch all existing product IDs from the vendor_product table.
    """
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM vendor_product")
        rows = cur.fetchall()
        return [row[0] for row in rows]
    except Error as e:
        print(f"Error fetching products: {e}")
        return []

def insert_product_images(conn):
    """ 
    Insert 4 sample images for each product found in the database.
    """
    product_ids = get_product_ids(conn)
    
    if not product_ids:
        print("No products found in 'vendor_product'. Please run insert_product_data.py first.")
        return

    images = []
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    
    # Minimal valid JPEG binary (1x1 pixel)
    hex_data = "FFD8FFE000104A46494600010101004800480000FFDB004300FFFFFF00000000000000000000000000000000000000000000000000000000FFC0000B080001000101011100FFC4001F0000010501010101010100000000000000000102030405060708090A0BFFDA0008010100003F007F00"
    dummy_image_data = bytes.fromhex(hex_data)

    for product_id in product_ids:
        # Generate 4 images per product
        for i in range(1, 5):
            image_name = f"product_{product_id}_img_{i}.jpg"
            image_mimetype = "image/jpeg"
            
            image_tuple = (
                dummy_image_data,
                image_name,
                image_mimetype,
                current_time,
                product_id
            )
            images.append(image_tuple)

    sql_insert_image = ''' 
        INSERT INTO vendor_productimage(image_data, image_name, image_mimetype, uploaded_at, product_id)
        VALUES(?, ?, ?, ?, ?) 
    '''

    try:
        cur = conn.cursor()
        cur.executemany(sql_insert_image, images)
        conn.commit()
        print(f"Success! {cur.rowcount} product images inserted.")
    except Error as e:
        print(f"Error inserting data: {e}")

def main():
    database = "db.sqlite3"

    conn = create_connection(database)
    if conn is not None:
        create_table(conn)
        insert_product_images(conn)
        conn.close()
    else:
        print("Error! Cannot create the database connection.")

if __name__ == '__main__':
    main()