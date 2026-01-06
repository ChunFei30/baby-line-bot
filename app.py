# ===== import =====
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import re

from db import init_db, save_record

# ===== app & LINE init =====
app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# ===== DB init =====
init_db()

print("🔥 THIS IS THE NEW APP.PY 🔥")

# ===== basic routes =====
@app.route("/")
def index():
    return "LINE BABY BOT IS RUNNING"

@app.route("/health")
def health():
    return "OK", 200

# ===== LINE callback =====
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    print("📩 CALLBACK:", body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# ===== LINE message handler (ONLY ONE) =====
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    # 🍼 喝奶 120ml
    milk_match = re.match(r"喝奶\s*(\d+)\s*ml", text)

    # 😴 睡眠 2小時 / 1.5小時
    sleep_match = re.match(r"睡眠\s*(\d+(\.\d+)?)\s*小時", text)

    # 👶 換尿布 大便 / 尿尿
    diaper_match = re.match(r"換尿布\s*(大便|尿尿)", text)

    if milk_match:
        amount = milk_match.group(1)
        save_record(user_id, "milk", f"{amount}ml")
        reply = f"🍼 已記錄喝奶\n份量：{amount} ml"

    elif sleep_match:
        hours = sleep_match.group(1)
        save_record(user_id, "sleep", f"{hours}小時")
        reply = f"😴 已記錄睡眠\n時數：{hours} 小時"

    elif diaper_match:
        kind = diaper_match.group(1)
        save_record(user_id, "diaper", kind)
        reply = f"👶 已記錄換尿布\n類型：{kind}"

    else:
        reply = (
            "我可以幫你記錄寶寶狀況喔 👶\n\n"
            "🍼 喝奶 120ml\n"
            "😴 睡眠 2小時\n"
            "👶 換尿布 大便 / 尿尿"
        )

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)