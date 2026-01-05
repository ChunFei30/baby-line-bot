import sqlite3

DB_PATH = "baby.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 使用者資料（寶寶狀態）
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        line_user_id TEXT PRIMARY KEY,
        stage TEXT,          -- born / pregnant
        birth_date TEXT,
        due_date TEXT
    )
    """)

    # 紀錄表（喝奶、睡眠、尿布）
    cur.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        line_user_id TEXT,
        record_type TEXT,    -- feeding / sleep / diaper
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


def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT line_user_id, stage, due_date, birth_date FROM users")
    rows = cur.fetchall()
    conn.close()
    return rows