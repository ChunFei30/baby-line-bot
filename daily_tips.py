import sqlite3
import pandas as pd
import os

DB_NAME = "baby.db"
EXCEL_FILE = "daily_tips.xlsx"

# 確認 DB 檔真的存在
if not os.path.exists(DB_NAME):
    raise Exception("❌ 找不到 baby.db，請確認檔案在同一個資料夾")

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# ✅ 強制建立資料表（關鍵）
cursor.execute("""
CREATE TABLE IF NOT EXISTS daily_tips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT
)
""")

# 讀 Excel（避免中文編碼問題）
df = pd.read_excel(EXCEL_FILE)

count = 0
for _, row in df.iterrows():
    content = str(row[0]).strip()
    if content:
        cursor.execute(
            "INSERT INTO daily_tips (content) VALUES (?)",
            (content,)
        )
        count += 1

conn.commit()
conn.close()

print(f"✅ 成功匯入 {count} 則育兒知識")