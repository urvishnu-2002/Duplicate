import sqlite3
from sqlite3 import Error
import random
from datetime import datetime, timedelta
import uuid

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

def get_product_prices(conn):
    """
    Fetch product prices to calculate realistic order totals.
    """
    try:
        cur = conn.cursor()
        cur.execute("SELECT price FROM vendor_product")
        rows = cur.fetchall()
        return [row[0] for row in rows]
    except Error as e:
        print(f"Error fetching products: {e}")
        return []

def insert_orders(conn):
    """ 
    Insert sample orders for customers (100-149).
    """
    product_prices = get_product_prices(conn)
    if not product_prices:
        print("No products found. Using random values for totals.")
        product_prices = [100.0, 200.0, 500.0, 50.0]

    orders = []
    
    # Customer IDs: 100-149
    customer_ids = range(100, 150)
    # Delivery Agent IDs: 160-169
    delivery_agent_ids = range(160, 170)
    
    statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    payment_methods = ['credit_card', 'paypal', 'cod', 'upi']
    
    current_time = datetime.now()

    # Generate 100 sample orders
    for _ in range(100):
        user_id = random.choice(customer_ids)
        
        # Generate Order Number
        timestamp = current_time.strftime('%Y%m%d%H%M%S')
        rand_suffix = random.randint(1000, 9999)
        unique_suffix = uuid.uuid4().hex[:4].upper()
        order_number = f"ORD-{timestamp}-{rand_suffix}-{unique_suffix}"
        
        status = random.choice(statuses)
        
        # Payment details
        payment_method = random.choice(payment_methods)
        if status == 'cancelled':
            payment_status = 'failed'
        elif payment_method == 'cod' and status != 'delivered':
            payment_status = 'pending'
        else:
            payment_status = 'paid'
            
        transaction_id = str(uuid.uuid4()) if payment_status == 'paid' else None
        
        # Calculate totals based on random selection of products
        num_items = random.randint(1, 5)
        selected_prices = random.choices(product_prices, k=num_items)
        subtotal = sum(selected_prices)
        tax_amount = round(subtotal * 0.18, 2) # 18% Tax
        shipping_cost = round(random.uniform(0, 100), 2) if subtotal < 1000 else 0.0
        total_amount = round(subtotal + tax_amount + shipping_cost, 2)
        
        tracked_location = 'Order Placed'
        if status in ['shipped', 'processing']:
            tracked_location = random.choice(['Warehouse', 'In Transit', 'Distribution Center'])
        elif status == 'delivered':
            tracked_location = 'Delivered'
        elif status == 'cancelled':
            tracked_location = 'Cancelled'
            
        created_at = (current_time - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d %H:%M:%S.%f")
        updated_at = created_at
        
        delivered_at = None
        delivery_agent_id = None
        
        if status == 'delivered':
            delivered_at = (datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S.%f") + timedelta(days=random.randint(2, 5))).strftime("%Y-%m-%d %H:%M:%S.%f")
            delivery_agent_id = random.choice(delivery_agent_ids)
        elif status == 'shipped':
            delivery_agent_id = random.choice(delivery_agent_ids)
            
        # Dummy delivery address ID (Assuming IDs 1-50 exist or FKs are loose)
        delivery_address_id = random.randint(1, 50) 

        order_tuple = (
            order_number, status, payment_method, payment_status, transaction_id,
            subtotal, tax_amount, shipping_cost, total_amount,
            tracked_location, created_at, updated_at, delivered_at,
            delivery_address_id, delivery_agent_id, user_id
        )
        orders.append(order_tuple)

    sql_insert_order = ''' 
        INSERT OR IGNORE INTO user_order(
            order_number, status, payment_method, payment_status, transaction_id,
            subtotal, tax_amount, shipping_cost, total_amount,
            tracked_location, created_at, updated_at, delivered_at,
            delivery_address_id, delivery_agent_id, user_id
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) 
    '''

    try:
        cur = conn.cursor()
        cur.executemany(sql_insert_order, orders)
        conn.commit()
        print(f"Success! {cur.rowcount} orders inserted.")
    except Error as e:
        print(f"Error inserting data: {e}")

def main():
    database = "db.sqlite3"

    conn = create_connection(database)
    if conn is not None:
        insert_orders(conn)
        conn.close()
    else:
        print("Error! Cannot create the database connection.")

if __name__ == '__main__':
    main()