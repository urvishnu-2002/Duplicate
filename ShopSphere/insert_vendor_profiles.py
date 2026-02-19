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

def insert_vendor_profiles(conn):
    """ 
    Insert sample vendor profiles for users with IDs 150-159.
    """
    profiles = []
    
    # Vendor IDs from insert_sampleUsers_data.py (150-159)
    # Customers: 100-149, Vendors: 150-159, Delivery Agents: 160-169
    vendor_ids = range(150, 160) 
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    business_types = ['retail', 'wholesale', 'manufacturer', 'distributor']

    for user_id in vendor_ids:
        # Generate sample data
        shop_name = f"Vendor Shop {user_id}"
        shop_description = f"Quality products from Vendor {user_id}"
        address = f"{random.randint(1, 999)} Market St, City {user_id}"
        business_type = random.choice(business_types)
        id_number = f"ID-{user_id}-{random.randint(1000, 9999)}"
        gst_number = f"GST{user_id}Z{random.randint(10, 99)}"
        pan_number = f"PAN{user_id}X{random.randint(10, 99)}"
        
        # Binary data placeholders (None)
        id_proof_data = None
        id_proof_name = None
        id_proof_mimetype = None
        pan_card_data = None
        pan_card_name = None
        pan_card_mimetype = None
        
        approval_status = 'approved'
        rejection_reason = None
        created_at = current_time
        updated_at = current_time
        is_blocked = 0
        blocked_reason = None
        
        bank_holder_name = f"Vendor User {user_id}"
        bank_account_number = f"123456789{user_id}"
        bank_ifsc_code = "BANK0001234"
        shipping_fee = 50.0
        
        # Tuple matching the columns provided (excluding id which is auto-increment)
        profile_tuple = (
            shop_name,
            shop_description,
            address,
            business_type,
            id_number,
            gst_number,
            pan_number,
            id_proof_data,
            id_proof_name,
            id_proof_mimetype,
            pan_card_data,
            pan_card_name,
            pan_card_mimetype,
            approval_status,
            rejection_reason,
            created_at,
            updated_at,
            is_blocked,
            blocked_reason,
            bank_holder_name,
            bank_account_number,
            bank_ifsc_code,
            shipping_fee,
            user_id
        )
        profiles.append(profile_tuple)

    # SQL statement
    sql_insert_profile = ''' 
        INSERT OR IGNORE INTO vendor_vendorprofile(
            shop_name, shop_description, address, business_type, 
            id_number, gst_number, pan_number, 
            id_proof_data, id_proof_name, id_proof_mimetype, 
            pan_card_data, pan_card_name, pan_card_mimetype, 
            approval_status, rejection_reason, 
            created_at, updated_at, 
            is_blocked, blocked_reason, 
            bank_holder_name, bank_account_number, bank_ifsc_code, 
            shipping_fee, user_id
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) 
    '''

    try:
        cur = conn.cursor()
        cur.executemany(sql_insert_profile, profiles)
        conn.commit()
        print(f"Success! {cur.rowcount} vendor profiles inserted.")
    except Error as e:
        print(f"Error inserting data: {e}")

def main():
    database = "db.sqlite3"

    conn = create_connection(database)
    if conn is not None:
        insert_vendor_profiles(conn)
        conn.close()
    else:
        print("Error! Cannot create the database connection.")

if __name__ == '__main__':
    main()