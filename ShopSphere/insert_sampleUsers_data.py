import sqlite3
from sqlite3 import Error
import hashlib
import base64
import secrets

def create_connection(db_file):
    """ 
    Create a database connection to the SQLite database specified by db_file.
    If the file does not exist, it will be created.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def hash_password(password):
    """
    Hashes a password using PBKDF2-SHA256 to match Django's format.
    """
    iterations = 1200000
    salt = secrets.token_urlsafe(16)
    hash_name = 'sha256'
    dk = hashlib.pbkdf2_hmac(hash_name, password.encode(), salt.encode(), iterations)
    b64_hash = base64.b64encode(dk).decode()
    return f"pbkdf2_{hash_name}${iterations}${salt}${b64_hash}"

def create_table(conn):
    """ 
    Create a sample 'users' table for demonstration purposes.
    """
    try:
        # SQL statement to create a table
        sql_create_users_table = """
            CREATE TABLE IF NOT EXISTS user_authuser (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                password TEXT,
                last_login TEXT,
                is_superuser BOOLEAN,
                first_name TEXT,
                last_name TEXT,
                is_staff BOOLEAN,
                is_active BOOLEAN,
                date_joined TEXT,
                email TEXT UNIQUE,
                username TEXT UNIQUE,
                phone TEXT,
                profile_image TEXT,
                role TEXT,
                is_blocked BOOLEAN,
                blocked_reason TEXT,
                suspended_until TEXT
            );
        """
        c = conn.cursor()
        c.execute(sql_create_users_table)
        print("Table 'user_authuser' checked/created successfully.")
    except Error as e:
        print(f"Error creating table: {e}")

def insert_sample_data(conn):
    """ 
    Insert multiple rows of sample data into the users table.
    """
    sample_users = []
    
    # Configuration for data generation
    roles_distribution = [('customer', 50), ('vendor', 10), ('delivery_agent', 10)]
    current_id = 100  # Start IDs from 100 to avoid conflicts with existing admins

    for role, count in roles_distribution:
        for i in range(1, count + 1):
            # Create a tuple for each user
            # (id, password, last_login, is_superuser, first_name, last_name, is_staff, is_active, date_joined, email, username, phone, profile_image, role, is_blocked, blovked_reason, suspended_untill)
            user_tuple = (
                current_id,
                'password123',                  # Plaintext password (will be hashed below)
                '2026-02-18 06:26:47.151666',   # last_login
                0,                              # is_superuser
                role.capitalize(),              # first_name
                str(i),                         # last_name
                0,                              # is_staff
                1,                              # is_active
                '2026-02-18 06:26:21.145988',   # date_joined
                f'{role}_{i}@example.com',      # email
                f'{role}_{i}',                  # username
                '1234567890',                   # phone
                '',                             # profile_image
                role,                           # role
                0,                              # is_blocked
                None,                           # blovked_reason
                None                            # suspended_untill
            )
            sample_users.append(user_tuple)
            current_id += 1

    # SQL statement with placeholders (?) for security
    sql_insert_user = ''' 
        INSERT OR IGNORE INTO user_authuser(id, password, last_login, is_superuser, first_name, last_name, is_staff, is_active, date_joined, email, username, phone, profile_image, role, is_blocked, blocked_reason, suspended_until)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) 
    '''

    try:
        cur = conn.cursor()
        
        # Hash passwords before insertion
        users_to_insert = []
        for user in sample_users:
            user_list = list(user)
            user_list[1] = hash_password(user_list[1])
            users_to_insert.append(tuple(user_list))
        
        # executemany is much faster than looping through execute()
        cur.executemany(sql_insert_user, users_to_insert)
        
        # Commit the transaction to save changes
        conn.commit()
        print(f"Success! {cur.rowcount} rows inserted.")
        return cur.lastrowid
    except Error as e:
        print(f"Error inserting data: {e}")

def verify_data(conn):
    """
    Query the data back to verify insertion.
    """
    print("\n--- Verifying Data in DB ---")
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_authuser")
    
    rows = cur.fetchall()
    
    if rows:
        # Print header
        #print(f"{'ID':<5} {'Name':<20} {'Email':<25} {'Role':<10} {'Active'}")
        print("-" * 70)
        for row in rows:
            #print(f"{row[0]:<5} {row[1]:<20} {row[2]:<25} {row[3]:<10} {row[4]}")
            print(row)
        print("-" * 70)
    else:
        print("Table is empty.")

def main():
    database = "db.sqlite3"

    # 1. Create a database connection
    conn = create_connection(database)

    if conn is not None:
        # 2. Ensure the table exists
        create_table(conn)

        # 3. Insert the sample data
        insert_sample_data(conn)

        # 4. Verify the results
        verify_data(conn)

        # 5. Close the connection
        conn.close()
    else:
        print("Error! Cannot create the database connection.")

if __name__ == '__main__':
    main()
