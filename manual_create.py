import sqlite3

def create_tables_manually():
    conn = sqlite3.connect('manual_timetable.db')
    cursor = conn.cursor()

    # Create tables manually
    tables = {
        'user': '''
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                password_hash VARCHAR(128) NOT NULL,
                role VARCHAR(50) NOT NULL DEFAULT 'faculty',
                department VARCHAR(100),
                approval_points INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        'classroom': '''
            CREATE TABLE IF NOT EXISTS classroom (
                id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                capacity INTEGER NOT NULL,
                room_type VARCHAR(50) NOT NULL,
                department VARCHAR(100),
                is_available BOOLEAN DEFAULT 1
            )
        ''',
        'faculty': '''
            CREATE TABLE IF NOT EXISTS faculty (
                id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                subjects TEXT NOT NULL,
                leaves_per_month INTEGER DEFAULT 1,
                unavailable_slots TEXT,
                department VARCHAR(100),
                max_classes_per_day INTEGER DEFAULT 4,
                email VARCHAR(120)
            )
        ''',
        'subject': '''
            CREATE TABLE IF NOT EXISTS subject (
                id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                teacher_id VARCHAR(50) NOT NULL,
                batches TEXT NOT NULL,
                per_week INTEGER NOT NULL,
                needs_lab BOOLEAN DEFAULT 0,
                fixed_slots TEXT,
                department VARCHAR(100),
                credits INTEGER DEFAULT 1
            )
        ''',
        'batch': '''
            CREATE TABLE IF NOT EXISTS batch (
                id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                size INTEGER NOT NULL,
                department VARCHAR(100),
                shift VARCHAR(50) DEFAULT 'morning',
                electives TEXT
            )
        ''',
        'shift': '''
            CREATE TABLE IF NOT EXISTS shift (
                id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                start_time VARCHAR(20) NOT NULL,
                end_time VARCHAR(20) NOT NULL,
                department VARCHAR(100)
            )
        ''',
        'timetable': '''
            CREATE TABLE IF NOT EXISTS timetable (
                id INTEGER PRIMARY KEY,
                version INTEGER NOT NULL DEFAULT 1,
                status VARCHAR(50) DEFAULT 'pending_approval',
                department VARCHAR(100),
                shift VARCHAR(50),
                created_by_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                approved_at DATETIME,
                FOREIGN KEY (created_by_id) REFERENCES user (id)
            )
        ''',
        'slot': '''
            CREATE TABLE IF NOT EXISTS slot (
                id INTEGER PRIMARY KEY,
                timetable_id INTEGER NOT NULL,
                subject_id VARCHAR(50) NOT NULL,
                subject_name VARCHAR(100) NOT NULL,
                teacher_id VARCHAR(50) NOT NULL,
                teacher_name VARCHAR(100) NOT NULL,
                batch_id VARCHAR(50) NOT NULL,
                batch_name VARCHAR(100) NOT NULL,
                room_id VARCHAR(50) NOT NULL,
                day VARCHAR(20) NOT NULL,
                slot_index INTEGER NOT NULL,
                approval_status VARCHAR(50) DEFAULT 'pending',
                approved_by_id INTEGER,
                change_reason TEXT,
                approved_at DATETIME,
                FOREIGN KEY (timetable_id) REFERENCES timetable (id),
                FOREIGN KEY (approved_by_id) REFERENCES user (id)
            )
        '''
    }

    for table_name, sql in tables.items():
        print(f"Creating table: {table_name}")
        cursor.execute(sql)

    conn.commit()

    # Verify tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    created_tables = cursor.fetchall()
    print(f"\nCreated {len(created_tables)} tables:")
    for table in created_tables:
        print(f"  - {table[0]}")

    conn.close()
    print("Manual table creation completed!")

if __name__ == "__main__":
    create_tables_manually()