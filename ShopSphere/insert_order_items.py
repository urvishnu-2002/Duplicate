import sqlite3
from sqlite3 import Error
import random

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

def get_orders(conn):
    """
    Fetch all existing order IDs and their status from the user_order table.
    """
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, status FROM user_order")
        rows = cur.fetchall()
        return rows
    except Error as e:
        print(f"Error fetching orders: {e}")
        return []

def get_products(conn):
    """
    Fetch all existing products with details from vendor_product table.
    """
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, price, vendor_id FROM vendor_product")
        rows = cur.fetchall()
        return rows
    except Error as e:
        print(f"Error fetching products: {e}")
        return []

def insert_order_items(conn):
    """ 
    Insert sample order items for existing orders.
    """
    orders = get_orders(conn)
    products = get_products(conn)
    
    if not orders:
        print("No orders found in 'user_order'. Please run insert_orders.py first.")
        return

    if not products:
        print("No products found in 'vendor_product'. Please run insert_product_data.py first.")
        return

    order_items = []

    for order in orders:
        order_id = order[0]
        order_status = order[1]
        
        # Randomly assign 1 to 5 items per order
        num_items = random.randint(1, 5)
        # Ensure we don't try to sample more than available products
        sample_size = min(num_items, len(products))
        selected_products = random.sample(products, sample_size)

        for prod in selected_products:
            product_id = prod[0]
            product_name = prod[1]
            product_price = prod[2]
            vendor_id = prod[3]
            
            quantity = random.randint(1, 3)
            subtotal = round(product_price * quantity, 2)
            
            # Set vendor_status based on order status
            vendor_status = order_status
            
            # Tuple matching the columns provided (excluding id which is auto-increment)
            item_tuple = (
                product_name,
                product_price,
                quantity,
                subtotal,
                vendor_status,
                order_id,
                product_id,
                vendor_id
            )
            order_items.append(item_tuple)

    sql_insert_item = ''' 
        INSERT INTO user_orderitem(
            product_name, product_price, quantity, subtotal, 
            vendor_status, order_id, product_id, vendor_id
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?) 
    '''

    try:
        cur = conn.cursor()
        cur.executemany(sql_insert_item, order_items)
        conn.commit()
        print(f"Success! {cur.rowcount} order items inserted.")
    except Error as e:
        print(f"Error inserting data: {e}")

def main():
    database = "db.sqlite3"

    conn = create_connection(database)
    if conn is not None:
        insert_order_items(conn)
        conn.close()
    else:
        print("Error! Cannot create the database connection.")

if __name__ == '__main__':
    main()