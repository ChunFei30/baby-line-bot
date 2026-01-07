import sqlite3
from datetime import datetime

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
        last_daily_push_date TEXT
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

    conn.commit()
    conn.close()

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

def get_last_milk_times(user_id, limit=5):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT created_at
        FROM records
        WHERE user_id = ?
          AND record_type = 'milk'
        ORDER BY created_at DESC
        LIMIT ?
    """, (user_id, limit))
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows

def upsert_user_settings(user_id, due_date=None, birth_date=None, default_feed_interval=None):
    conn = get_conn()
    c = conn.cursor()

    c.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,))

    if due_date is not None:
        c.execute("UPDATE user_settings SET due_date=? WHERE user_id=?", (due_date, user_id))
    if birth_date is not None:
        c.execute("UPDATE user_settings SET birth_date=? WHERE user_id=?", (birth_date, user_id))
    if default_feed_interval is not None:
        c.execute("UPDATE user_settings SET default_feed_interval=? WHERE user_id=?", (default_feed_interval, user_id))

    conn.commit()
    conn.close()

def get_user_settings(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT due_date, birth_date, default_feed_interval, last_daily_push_date
        FROM user_settings WHERE user_id=?
    """, (user_id,))
    row = c.fetchone()
    conn.close()
    return row if row else (None, None, 4, None)

def set_last_daily_push_date(user_id, date_str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE user_settings SET last_daily_push_date=? WHERE user_id=?", (date_str, user_id))
    conn.commit()
    conn.close()

def add_reminder(user_id, reminder_type, due_at, payload=""):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO reminders (user_id, reminder_type, due_at, payload)
        VALUES (?, ?, ?, ?)
    """, (user_id, reminder_type, due_at, payload))
    conn.commit()
    conn.close()

def get_due_reminders(now_str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, user_id, reminder_type, payload
        FROM reminders
        WHERE done=0 AND due_at <= ?
    """, (now_str,))
    rows = c.fetchall()
    conn.close()
    return rows

def mark_reminder_done(rid):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE reminders SET done=1 WHERE id=?", (rid,))
    conn.commit()
    conn.close()

def get_all_user_ids():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM user_settings")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows