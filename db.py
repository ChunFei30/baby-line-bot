import sqlite3
from datetime import datetime

DB_NAME = "baby.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            record_type TEXT,
            record_value TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_record(user_id, record_type, record_value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO records (user_id, record_type, record_value, created_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, record_type, record_value, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_today_records_with_time(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT record_type, record_value, created_at
        FROM records
        WHERE user_id = ?
        AND date(created_at) = date('now', 'localtime')
        ORDER BY created_at ASC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows