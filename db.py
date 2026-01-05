import sqlite3

DB_PATH = "baby.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        line_user_id TEXT,
        record_type TEXT,
        value TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def save_record(line_user_id, record_type, value):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO records (line_user_id, record_type, value) VALUES (?, ?, ?)",
        (line_user_id, record_type, value)
    )
    conn.commit()
    conn.close()