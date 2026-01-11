from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FollowEvent
from datetime import datetime, timedelta
import os, re

from db import *

app = Flask(__name__)

# ===== LINE =====
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# ===== CRON SECRET =====
CRON_SECRET = os.getenv("CRON_SECRET", "123456")

# ===== DB INIT =====
init_db()

# =========================
# 基本頁面
# =========================
@app.route("/")
def index():
    return "LINE BABY BOT RUNNING"

# =========================
# LINE webhook
# =========================
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# =========================
# 新好友
# =========================
@handler.add(FollowEvent)
def handle_follow(event):
    user_id = event.source.user_id
    upsert_user_settings(user_id)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text=(
                "👋 歡迎你，辛苦了 🤍\n\n"
                "我會每天早晚陪你一起照顧寶寶。\n\n"
                "📅 設定生日 YYYY-MM-DD\n"
                "🤰 設定預產期 YYYY-MM-DD\n\n"
                "☀️ 早上 9 點我會提醒你\n"
                "🌙 晚上 9 點我會幫你做今日總結"
            )
        )
    )

# =========================
# 今日總結（晚上用）
# =========================
def build_today_summary(user_id):
    records = get_today_records_with_time(user_id)

    milk, milk_ml = 0, 0
    sleep, sleep_hr = 0, 0
    diaper, poop, pee = 0, 0, 0
    details = []

    for t, v, c in records:
        tm = c[11:16]
        if t == "milk":
            milk += 1
            ml = int(v.replace("ml",""))
            milk_ml += ml
            details.append(f"{tm} · {ml} ml")
        elif t == "sleep":
            sleep += 1
            sleep_hr += float(v.replace("小時",""))
        elif t == "diaper":
            diaper += 1
            if v == "大便": poop += 1
            if v == "尿尿": pee += 1

    text = "🌙 今日寶寶小日記\n\n"
    text += f"🍼 喝奶 {milk} 次，共 {milk_ml} ml\n"
    if details:
        text += "\n".join(details) + "\n\n"
    text += f"😴 睡眠 {sleep} 次，約 {sleep_hr:.1f} 小時\n\n"
    text += f"👶 換尿布 {diaper} 次（大便 {poop} / 尿尿 {pee}）\n\n"
    text += "💛 今天你已經做得很好了，晚安。"

    return text

# =========================
# 出生 / 倒數天數（早上用）
# =========================
def build_day_count(user_id):
    due, birth = get_user_settings(user_id)
    today = datetime.now().date()

    if birth:
        d = datetime.strptime(birth,"%Y-%m-%d").date()
        return f"📅 寶寶出生第 {(today-d).days+1} 天"

    if due:
        d = datetime.strptime(due,"%Y-%m-%d").date()
        return f"🤰 距離預產期 {(d-today).days} 天"

    return "📅 今天也是值得被溫柔對待的一天"

# =========================
# 使用者手動訊息
# =========================
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    upsert_user_settings(user_id)

    if text == "今天":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=build_today_summary(user_id))
        )
        return

    if text == "天數":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=build_day_count(user_id))
        )
        return

# =========================
# ⭐ CRON 主動推播（台灣時間）
# =========================
@app.route("/cron")
def cron():
    if request.args.get("secret") != CRON_SECRET:
        return "Forbidden", 403

    users = get_all_user_ids()
    if not users:
        return "no users"

    # ⏰ Render 是 UTC，要轉成台灣時間
    now = datetime.utcnow() + timedelta(hours=8)
    now_hour = now.hour

    pushed = 0

    for user_id in users:
        try:
            # ☀️ 早上 9 點
            if now_hour == 9:
                msg = (
                    "☀️ 早安，辛苦的你 🤍\n\n"
                    f"{build_day_count(user_id)}\n\n"
                    f"📚 今日育兒小提醒：\n{get_random_daily_tip()}"
                )
                line_bot_api.push_message(user_id, TextSendMessage(text=msg))
                pushed += 1

            # 🌙 晚上 9 點
            elif now_hour == 21:
                msg = build_today_summary(user_id)
                line_bot_api.push_message(user_id, TextSendMessage(text=msg))
                pushed += 1

        except Exception as e:
            print("push error:", e)

    return f"cron ok {now_hour}, pushed {pushed}"