import sqlite3
import os

db_path = 'test_timetable.db'
print(f"Database path: {os.path.abspath(db_path)}")
print(f"Database exists: {os.path.exists(db_path)}")
print(f"Database size: {os.path.getsize(db_path)} bytes")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check sqlite_master
cursor.execute("SELECT name, type FROM sqlite_master ORDER BY name")
all_entries = cursor.fetchall()
print(f"\nAll entries in sqlite_master: {len(all_entries)}")
for entry in all_entries:
    print(f"  {entry[1]}: {entry[0]}")

# Check just tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
print(f"\nTables: {len(tables)}")
for table in tables:
    print(f"  - {table[0]}")

conn.close()