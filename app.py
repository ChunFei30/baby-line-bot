from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import sqlite3
import re
from datetime import datetime

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

def save_record(user_id, record_type, value):
    conn = sqlite3.connect("baby.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO records (user_id, record_type, value) VALUES (?, ?, ?)",
        (user_id, record_type, value)
    )
    conn.commit()
    conn.close()

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id

    # 🍼 喝奶
    if text.startswith("喝奶"):
        value = text.replace("喝奶", "").strip()
        save_record(user_id, "feeding", value)
        reply = f"🍼 已紀錄喝奶：{value}"

    # 😴 睡眠
    elif text.startswith("睡眠"):
        value = text.replace("睡眠", "").strip()
        save_record(user_id, "sleep", value)
        reply = f"😴 已紀錄睡眠：{value}"

    # 🧷 換尿布
    elif text.startswith("換尿布"):
        value = text.replace("換尿布", "").strip()
        save_record(user_id, "diaper", value)
        reply = f"🧷 已紀錄換尿布：{value}"

    else:
        reply = (
            "請輸入以下格式之一：\n"
            "🍼 喝奶 120ml\n"
            "😴 睡眠 14:30-16:00\n"
            "🧷 換尿布 大便/尿尿"
        )

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    app.run()