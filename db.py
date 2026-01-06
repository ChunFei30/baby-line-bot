import sqlite3
from datetime import datetime

DB_NAME = "baby.db"

def get_conn():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        record_type TEXT,
        value TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()

def save_record(user_id, record_type, value):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO records (user_id, record_type, value, created_at) VALUES (?, ?, ?, ?)",
        (user_id, record_type, value, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

    conn.commit()
    conn.close()

def get_today_records_with_time(user_id):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT record_type, value, created_at
        FROM records
        WHERE user_id = ?
          AND DATE(created_at) = DATE('now', 'localtime')
        ORDER BY created_at ASC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows