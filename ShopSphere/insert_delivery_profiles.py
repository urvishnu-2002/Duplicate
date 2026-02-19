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

def insert_delivery_profiles(conn):
    """ 
    Insert sample delivery profiles for users with IDs 160-169.
    """
    profiles = []
    
    # Delivery Agent IDs from insert_sampleUsers_data.py (160-169)
    delivery_ids = range(160, 170) 
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    vehicle_types = ['bike', 'scooter', 'van', 'truck']

    for user_id in delivery_ids:
        # Generate sample data
        address = f"{random.randint(1, 999)} Delivery Lane, City {user_id}"
        vehicle_type = random.choice(vehicle_types)
        vehicle_number = f"MH-{random.randint(10, 99)}-{random.choice(['AB', 'XY', 'ZZ'])}-{random.randint(1000, 9999)}"
        driving_license_number = f"DL-{user_id}-{random.randint(10000, 99999)}"
        
        # Placeholder for image (None)
        dl_image = None 
        
        bank_holder_name = f"Delivery Agent {user_id}"
        bank_account_number = f"987654321{user_id}"
        bank_ifsc_code = "BANK0005678"
        
        approval_status = 'approved'
        is_blocked = 0
        blocked_reason = None
        created_at = current_time
        updated_at = current_time
        
        # Tuple matching the columns provided (excluding id which is auto-increment)
        profile_tuple = (
            address,
            vehicle_type,
            vehicle_number,
            driving_license_number,
            dl_image,
            bank_holder_name,
            bank_account_number,
            bank_ifsc_code,
            approval_status,
            is_blocked,
            blocked_reason,
            created_at,
            updated_at,
            user_id
        )
        profiles.append(profile_tuple)

    # SQL statement
    sql_insert_profile = ''' 
        INSERT OR IGNORE INTO deliveryAgent_deliveryprofile(
            address, vehicle_type, vehicle_number, driving_license_number, 
            dl_image, bank_holder_name, bank_account_number, bank_ifsc_code, 
            approval_status, is_blocked, blocked_reason, 
            created_at, updated_at, user_id
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) 
    '''

    try:
        cur = conn.cursor()
        cur.executemany(sql_insert_profile, profiles)
        conn.commit()
        print(f"Success! {cur.rowcount} delivery profiles inserted.")
    except Error as e:
        print(f"Error inserting data: {e}")

def main():
    database = "db.sqlite3"

    conn = create_connection(database)
    if conn is not None:
        insert_delivery_profiles(conn)
        conn.close()
    else:
        print("Error! Cannot create the database connection.")

if __name__ == '__main__':
    main()