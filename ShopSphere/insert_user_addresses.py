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

def insert_user_addresses(conn):
    """ 
    Insert sample addresses for users (100-149).
    """
    addresses = []
    # Customer IDs: 100-149
    user_ids = range(100, 150)
    
    cities_in = ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Ahmedabad", "Chennai", "Kolkata", "Surat", "Pune", "Jaipur"]
    states_in = ["Maharashtra", "Delhi", "Karnataka", "Telangana", "Gujarat", "Tamil Nadu", "West Bengal", "Gujarat", "Maharashtra", "Rajasthan"]
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    for user_id in user_ids:
        # Generate 1 to 3 addresses per user
        num_addresses = random.randint(1, 3)
        
        for i in range(num_addresses):
            idx = random.randint(0, len(cities_in)-1)
            
            name = f"User {user_id} Address"
            phone = f"9876543{random.randint(100, 999)}"
            email = f"customer{user_id}@example.com"
            address_line1 = f"{random.randint(1, 999)}, Sample Street"
            address_line2 = f"Near Landmark {random.randint(1, 50)}"
            city = cities_in[idx]
            state = states_in[idx]
            pincode = f"{random.randint(110000, 990000)}"
            country = "India"
            
            # First address is default
            is_default = 1 if i == 0 else 0
            
            address_tuple = (
                name, phone, email, address_line1, address_line2,
                city, state, pincode, country, is_default,
                current_time, user_id
            )
            addresses.append(address_tuple)

    sql_insert = ''' 
        INSERT INTO user_address(
            name, phone, email, address_line1, address_line2, 
            city, state, pincode, country, is_default, 
            created_at, user_id
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) 
    '''

    try:
        cur = conn.cursor()
        cur.executemany(sql_insert, addresses)
        conn.commit()
        print(f"Success! {cur.rowcount} addresses inserted.")
    except Error as e:
        print(f"Error inserting data: {e}")

def main():
    database = "db.sqlite3"

    conn = create_connection(database)
    if conn is not None:
        insert_user_addresses(conn)
        conn.close()
    else:
        print("Error! Cannot create the database connection.")

if __name__ == '__main__':
    main()