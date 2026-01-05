import os
import re
import logging

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from db import save_record  # 你的資料庫函式

# =========================
# Logging（一定看得到）
# =========================
logging.basicConfig(level=logging.INFO)
logging.info("🔥 RENDER IS RUNNING APP.PY - FINAL CONFIRM 🔥")
logging.info("🔥 LINE BABY BOT START 🔥")

# =========================
# Flask / LINE init
# =========================
app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# =========================
# Health check（Render 用）
# =========================
@app.route("/")
def home():
    return "LINE Baby Bot is running"

# =========================
# LINE Webhook
# =========================
@app.route("/callback", methods=["GET", "POST"])
def callback():
    if request.method == "GET":
        return "OK"

    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# =========================
# Message Handler（只有一個）
# =========================
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id

    # 🔧 文字正規化（超重要）
    raw_text = event.message.text
    text = re.sub(r"\s+", " ", raw_text).strip()

    logging.info(f"📩 RAW TEXT   : {repr(raw_text)}")
    logging.info(f"📩 CLEAN TEXT : {repr(text)}")

    try:
        # 🍼 喝奶
        if text.startswith("喝奶"):
            value = text.replace("喝奶", "", 1).strip()
            save_record(user_id, "feeding", value)
            reply = f"🍼 已記錄喝奶：{value}"

        # 😴 睡眠
        elif text.startswith("睡眠"):
            value = text.replace("睡眠", "", 1).strip()
            save_record(user_id, "sleep", value)
            reply = f"😴 已記錄睡眠：{value}"

        # 👶 換尿布
        elif text.startswith("換尿布"):
            value = text.replace("換尿布", "", 1).strip()
            save_record(user_id, "diaper", value)
            reply = f"👶 已記錄換尿布：{value}"

        # 📘 教學
        else:
            reply = (
                "請輸入以下其中一種指令：\n"
                "🍼 喝奶 120ml\n"
                "😴 睡眠 2小時\n"
                "👶 換尿布 大便 / 尿尿"
            )

    except Exception as e:
        logging.exception("❌ 發生錯誤")
        reply = f"⚠️ 系統錯誤：{str(e)}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

# =========================
# Local test（Render 不會用）
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)