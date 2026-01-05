from flask import Flask, request, abort
from datetime import datetime, date
import os
import re
import sqlite3

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage


# ======================
# 資料庫
# ======================
def init_db():
    conn = sqlite3.connect("baby.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            record_type TEXT,
            value TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ======================
# Flask & LINE
# ======================
app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    raise ValueError("請先設定 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


# ======================
# 首頁（測試用）
# ======================
@app.route("/")
def home():
    return "LINE Baby Bot is running"


# ======================
# LINE webhook
# ======================
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


# ======================
# 訊息處理
# ======================
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id

    # ===== 喝奶紀錄 =====
    if text.startswith("喝奶"):
        value = text.replace("喝奶", "").strip()

        if not value:
            reply = "請輸入例如：喝奶 120ml"
        else:
            conn = sqlite3.connect("baby.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO records (user_id, record_type, value) VALUES (?, ?, ?)",
                (user_id, "feeding", value)
            )
            conn.commit()
            conn.close()

            reply = f"🍼 已紀錄喝奶：{value}"

    # ===== 生日輸入 =====
    elif re.match(r"\d{4}-\d{2}-\d{2}$", text):
        try:
            d = datetime.strptime(text, "%Y-%m-%d").date()
            days = (date.today() - d).days

            conn = sqlite3.connect("baby.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO records (user_id, record_type, value) VALUES (?, ?, ?)",
                (user_id, "birthdate", text)
            )
            conn.commit()
            conn.close()

            reply = f"👶 寶寶今天出生滿 {days} 天了"

        except:
            reply = "日期格式錯誤，請輸入 YYYY-MM-DD"

    # ===== 其他 =====
    else:
        reply = (
            "請輸入以下其中一種指令：\n"
            "📅 設定生日：YYYY-MM-DD\n"
            "🍼 紀錄喝奶：喝奶 120ml"
        )

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )


# ======================
# 啟動
# ======================
if __name__ == "__main__":
    app.run(port=5000)