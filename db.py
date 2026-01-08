import sqlite3
from datetime import datetime
import random

DB_NAME = "baby.db"

def get_conn():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        record_type TEXT,
        value TEXT,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id TEXT PRIMARY KEY,
        due_date TEXT,
        birth_date TEXT,
        default_feed_interval REAL DEFAULT 4,
        last_daily_push_date TEXT,
        pushed_months TEXT DEFAULT ''
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        reminder_type TEXT,
        due_at TEXT,
        payload TEXT,
        done INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS daily_tips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT
    )
    """)

    conn.commit()
    conn.close()

# ===== 紀錄 =====
def save_record(user_id, record_type, value):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO records (user_id, record_type, value, created_at) VALUES (?, ?, ?, ?)",
        (user_id, record_type, value, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

def get_today_records_with_time(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT record_type, value, created_at
        FROM records
        WHERE user_id = ?
        AND DATE(created_at) = DATE('now','localtime')
        ORDER BY created_at ASC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

# ===== 使用者 =====
def upsert_user_settings(user_id, due_date=None, birth_date=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,))
    if due_date:
        c.execute("UPDATE user_settings SET due_date=? WHERE user_id=?", (due_date, user_id))
    if birth_date:
        c.execute("UPDATE user_settings SET birth_date=? WHERE user_id=?", (birth_date, user_id))
    conn.commit()
    conn.close()

def get_user_settings(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT due_date, birth_date
        FROM user_settings WHERE user_id=?
    """, (user_id,))
    row = c.fetchone()
    conn.close()
    return row if row else (None, None)

def get_all_user_ids():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM user_settings")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows

# ===== 每日育兒知識 =====
def get_random_daily_tip():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT content FROM daily_tips ORDER BY RANDOM() LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else "今天也請記得，你已經做得很好了 🤍"