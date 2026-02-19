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

def insert_reviews(conn):
    """ 
    Insert sample reviews for products from users (100-149).
    """
    product_ids = get_product_ids(conn)
    
    if not product_ids:
        print("No products found in 'vendor_product'. Please run insert_product_data.py first.")
        return

    reviews = []
    # Customer IDs: 100-149 (Consistent with insert_orders.py)
    user_ids = range(100, 150) 
    
    sample_comments = [
        ("Excellent product, highly recommended!", 5),
        ("Good value for the price.", 4),
        ("Average quality, but works.", 3),
        ("Not satisfied with the purchase.", 2),
        ("Terrible, arrived damaged.", 1),
        ("Fast shipping and great item.", 5),
        ("Okay, but could be better.", 3),
        ("Loved it!", 5),
        ("Waste of money.", 1),
        ("Exactly as described.", 4)
    ]
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    # Generate 150 sample reviews
    for _ in range(150):
        user_id = random.choice(user_ids)
        product_id = random.choice(product_ids)
        
        comment_data = random.choice(sample_comments)
        comment = comment_data[0]
        rating = comment_data[1]
        
        pictures = None # Placeholder for image path/data
        
        review_tuple = (
            rating,
            comment,
            pictures,
            current_time,
            current_time,
            product_id,
            user_id
        )
        reviews.append(review_tuple)

    sql_insert_review = ''' 
        INSERT OR IGNORE INTO user_review(
            rating, comment, pictures, created_at, updated_at, product_id, user_id
        )
        VALUES(?, ?, ?, ?, ?, ?, ?) 
    '''

    try:
        cur = conn.cursor()
        cur.executemany(sql_insert_review, reviews)
        conn.commit()
        print(f"Success! {cur.rowcount} reviews inserted.")
    except Error as e:
        print(f"Error inserting data: {e}")

def main():
    database = "db.sqlite3"

    conn = create_connection(database)
    if conn is not None:
        insert_reviews(conn)
        conn.close()
    else:
        print("Error! Cannot create the database connection.")

if __name__ == '__main__':
    main()