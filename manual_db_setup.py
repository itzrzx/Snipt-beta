import sqlite3
import os

db_name = 'site.db'
if os.path.exists('app'):
    db_path = os.path.join('app', db_name)
else:
    db_path = db_name

print(f"Attempting to connect to database at: {os.path.abspath(db_path)}")

def execute_sql(conn, sql_statement, description):
    try:
        cursor = conn.cursor()
        cursor.execute(sql_statement)
        conn.commit()
        print(f"Successfully executed: {description}")
    except sqlite3.Error as e:
        print(f"Error executing {description}: {e}")
        if "duplicate column name" not in str(e).lower() and "table" not in str(e).lower() and "already exists" not in str(e).lower() :
             # Only return False for errors that are not "duplicate column" or "table already exists"
            return False
    return True

def main():
    if os.path.dirname(db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        print(f"Connected to SQLite database: {os.path.abspath(db_path)}")

        # SQL for User table (essential prerequisite)
        sql_create_user_table = """
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(64) NOT NULL UNIQUE,
            email VARCHAR(120) NOT NULL UNIQUE,
            password_hash VARCHAR(128)
        );
        """
        # Create user table index (optional, but good practice)
        sql_create_user_username_index = "CREATE INDEX IF NOT EXISTS ix_user_username ON user (username);"
        sql_create_user_email_index = "CREATE INDEX IF NOT EXISTS ix_user_email ON user (email);"


        # SQL for Message table (reflecting state *after* voice messages, *before* rooms)
        sql_create_message_table = """
        CREATE TABLE IF NOT EXISTS message (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            body VARCHAR(140),
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            sender_id INTEGER,
            recipient_id INTEGER,
            message_type VARCHAR(10) DEFAULT 'text',
            file_url VARCHAR(200),
            FOREIGN KEY(sender_id) REFERENCES user(id),
            FOREIGN KEY(recipient_id) REFERENCES user(id) 
        );
        """
        # Create message table index
        sql_create_message_timestamp_index = "CREATE INDEX IF NOT EXISTS ix_message_timestamp ON message (timestamp);"


        sql_create_room_table = """
        CREATE TABLE IF NOT EXISTS room (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            creator_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(creator_id) REFERENCES user(id)
        );
        """

        sql_create_room_member_table = """
        CREATE TABLE IF NOT EXISTS room_member (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES user(id),
            FOREIGN KEY(room_id) REFERENCES room(id),
            UNIQUE(user_id, room_id)
        );
        """
        
        sql_alter_message_table_add_room_id = "ALTER TABLE message ADD COLUMN room_id INTEGER;"
        # We won't add FK for room_id via ALTER TABLE due to SQLite limitations here.
        # SQLAlchemy in models.py will manage the relationship based on the column's presence.

        # Execute SQL
        if not execute_sql(conn, sql_create_user_table, "CREATE TABLE user"): return
        if not execute_sql(conn, sql_create_user_username_index, "CREATE INDEX ix_user_username"): return
        if not execute_sql(conn, sql_create_user_email_index, "CREATE INDEX ix_user_email"): return

        if not execute_sql(conn, sql_create_message_table, "CREATE TABLE message"): return
        if not execute_sql(conn, sql_create_message_timestamp_index, "CREATE INDEX ix_message_timestamp"): return
        
        if not execute_sql(conn, sql_create_room_table, "CREATE TABLE room"): return
        if not execute_sql(conn, sql_create_room_member_table, "CREATE TABLE room_member"): return
        
        print("Attempting to add 'room_id' to 'message' table. 'Duplicate column' error is OK if run before.")
        execute_sql(conn, sql_alter_message_table_add_room_id, "ALTER TABLE message ADD COLUMN room_id")
        
        print("Manual DB setup script completed.")

    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == '__main__':
    main()
