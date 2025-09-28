import sqlite3
import os

def view_database():
    db_path = 'timetable.db'
    print(f"Connecting to database: {os.path.abspath(db_path)}")
    print(f"Database exists: {os.path.exists(db_path)}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Method 1: sqlite_master
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        sqlite_master_tables = [row[0] for row in cursor.fetchall()]
        print(f"\nMethod 1 (sqlite_master): Found {len(sqlite_master_tables)} tables")
        for table in sqlite_master_tables:
            print(f"  - {table}")

        # Method 2: Direct table listing
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        user_tables = [row[0] for row in cursor.fetchall()]
        print(f"\nMethod 2 (user tables): Found {len(user_tables)} tables")
        for table in user_tables:
            print(f"  - {table}")

        # Method 3: Check each expected table
        expected_tables = ['user', 'classroom', 'faculty', 'subject', 'batch', 'shift', 'timetable', 'slot']
        print(f"\nMethod 3 (expected tables check):")
        for table_name in expected_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  - {table_name}: {count} rows")
            except sqlite3.OperationalError as e:
                print(f"  - {table_name}: ERROR - {e}")

        print("\n=== DETAILED TABLE INFO ===")
        for table_name in expected_tables:
            try:
                print(f"\n📋 Table: {table_name}")

                # Get table structure
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                print("Columns:")
                for col in columns:
                    print(f"  - {col[1]} ({col[2]})")

                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"Rows: {count}")

                # Show sample data (first 3 rows)
                if count > 0:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                    rows = cursor.fetchall()
                    print("Sample data:")
                    for row in rows:
                        print(f"  {row}")
                else:
                    print("No data in table")
            except Exception as e:
                print(f"Error reading table {table_name}: {e}")

        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    view_database()