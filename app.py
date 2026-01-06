# ===== import =====
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import re

from db import init_db, save_record, get_today_records_with_time

# ===== app & LINE init =====
app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# ===== DB init =====
init_db()

print("🔥🔥🔥 THIS IS THE NEW APP.PY 2026-01-06 🔥🔥🔥")

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

# ===== LINE message handler =====
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    print(f"🔥 收到訊息：{text}")

    # ===== 📊 今天總結 =====
    if text == "今天":
        records = get_today_records_with_time(user_id)

        milk_count = 0
        milk_total = 0
        milk_details = []

        sleep_count = 0
        sleep_total = 0.0

        diaper_total = 0
        diaper_poop = 0
        diaper_pee = 0

        for r_type, value, created_at in records:
            time_str = created_at[11:16]

            if r_type == "milk":
                milk_count += 1
                amount = int(value.replace("ml", ""))
                milk_total += amount
                milk_details.append(f"{time_str}　{amount} ml")

            elif r_type == "sleep":
                sleep_count += 1
                sleep_total += float(value.replace("小時", ""))

            elif r_type == "diaper":
                diaper_total += 1
                if value == "大便":
                    diaper_poop += 1
                elif value == "尿尿":
                    diaper_pee += 1

        reply = (
            "📊 今日寶寶紀錄\n\n"
            f"🍼 喝奶：{milk_count} 次，共 {milk_total} ml\n"
        )

        reply += (
            "\n".join(milk_details) + "\n\n"
            if milk_details else
            "（今天尚未記錄喝奶）\n\n"
        )

        reply += (
            f"😴 睡眠：{sleep_count} 次，共 {sleep_total:.1f} 小時\n\n"
            f"👶 換尿布：{diaper_total} 次\n"
            f"• 大便 {diaper_poop} 次\n"
            f"• 尿尿 {diaper_pee} 次"
        )

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )
        return

    # ===== 🍼 喝奶 =====
    milk_match = re.match(r"喝奶\s*(\d+)\s*ml", text)

    # ===== 😴 睡眠 =====
    sleep_match = re.match(r"睡眠\s*(\d+(\.\d+)?)\s*小時", text)

    # ===== 👶 換尿布 =====
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
            "👶 換尿布 大便 / 尿尿\n"
            "📊 今天（查看今日總結）"
        )

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )