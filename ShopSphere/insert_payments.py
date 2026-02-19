import sqlite3
from sqlite3 import Error
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

def create_table(conn):
    """
    Create the 'user_payment' table if it doesn't exist.
    """
    try:
        sql_create_payment_table = """
            CREATE TABLE IF NOT EXISTS user_payment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                method TEXT,
                amount REAL,
                transaction_id TEXT,
                status TEXT,
                created_at TEXT,
                completed_at TEXT,
                order_id INTEGER,
                user_id INTEGER,
                FOREIGN KEY (order_id) REFERENCES user_order (id)
            );
        """
        c = conn.cursor()
        c.execute(sql_create_payment_table)
        print("Table 'user_payment' checked/created successfully.")
    except Error as e:
        print(f"Error creating table: {e}")

def insert_payments(conn):
    """ 
    Insert payment data for existing orders.
    """
    try:
        cur = conn.cursor()
        # Fetch necessary fields from user_order
        cur.execute("SELECT id, payment_method, total_amount, transaction_id, payment_status, created_at, user_id FROM user_order")
        orders = cur.fetchall()
    except Error as e:
        print(f"Error fetching orders: {e}")
        return

    if not orders:
        print("No orders found in 'user_order'. Please run insert_orders.py first.")
        return

    payments = []
    for order in orders:
        order_id = order[0]
        method = order[1]
        amount = order[2]
        transaction_id = order[3]
        status = order[4]
        created_at = order[5]
        user_id = order[6]
        
        # Fix for NOT NULL constraint: Generate a placeholder if transaction_id is None
        if transaction_id is None:
            # Generate a dummy transaction ID for pending/failed/COD payments
            transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"

        # Determine completed_at based on status
        completed_at = created_at if status == 'paid' else None
        
        payment_tuple = (
            method, amount, transaction_id, status, 
            created_at, completed_at, order_id, user_id
        )
        payments.append(payment_tuple)

    sql_insert_payment = ''' 
        INSERT INTO user_payment(method, amount, transaction_id, status, created_at, completed_at, order_id, user_id)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?) 
    '''

    try:
        cur = conn.cursor()
        cur.executemany(sql_insert_payment, payments)
        conn.commit()
        print(f"Success! {cur.rowcount} payments inserted.")
    except Error as e:
        print(f"Error inserting data: {e}")

def main():
    database = "db.sqlite3"
    conn = create_connection(database)
    if conn is not None:
        create_table(conn)
        insert_payments(conn)
        conn.close()
    else:
        print("Error! Cannot create the database connection.")

if __name__ == '__main__':
    main()