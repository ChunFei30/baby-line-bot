from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FollowEvent
from datetime import datetime
import os, re

from db import *

app = Flask(__name__)

# =========================
# LINE 設定
# =========================
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# =========================
# CRON SECRET
# =========================
CRON_SECRET = os.getenv("CRON_SECRET", "123456")

# =========================
# DB 初始化
# =========================
init_db()

# =========================
# 基本頁面
# =========================
@app.route("/")
def index():
    return "LINE BABY BOT RUNNING"

# =========================
# LINE Webhook
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
# 新好友加入
# =========================
@handler.add(FollowEvent)
def handle_follow(event):
    user_id = event.source.user_id

    # ⭐ 一定要存 user_id（不然 cron 找不到人）
    upsert_user_settings(user_id)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text=(
                "👋 歡迎你，辛苦了 🤍\n\n"
                "我會每天陪你一起照顧寶寶。\n\n"
                "📅 設定生日 YYYY-MM-DD\n"
                "🤰 設定預產期 YYYY-MM-DD\n\n"
                "我會在早晚主動關心你 🌙☀️"
            )
        )
    )

# =========================
# 今日總結
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
    text += "💛 辛苦了，你真的很棒。"

    return text

def build_day_count(user_id):
    due, birth = get_user_settings(user_id)
    today = datetime.now().date()

    if birth:
        d = datetime.strptime(birth,"%Y-%m-%d").date()
        return f"📅 寶寶出生第 {(today-d).days+1} 天"

    if due:
        d = datetime.strptime(due,"%Y-%m-%d").date()
        return f"🤰 距離預產期 {(d-today).days} 天"

    return ""

# =========================
# 使用者訊息
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

    if m := re.match(r"設定生日 (\d{4}-\d{2}-\d{2})", text):
        upsert_user_settings(user_id, birth_date=m.group(1))
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="✅ 已設定生日")
        )
        return

    if m := re.match(r"設定預產期 (\d{4}-\d{2}-\d{2})", text):
        upsert_user_settings(user_id, due_date=m.group(1))
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="🤍 已設定預產期")
        )
        return

    if m := re.match(r"喝奶 (\d+)ml", text):
        save_record(user_id, "milk", f"{m.group(1)}ml")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="🍼 已記錄")
        )
        return

    if text in ["換尿布 大便", "換尿布 尿尿"]:
        save_record(user_id, "diaper", "大便" if "大便" in text else "尿尿")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="👶 已記錄")
        )
        return

    if m := re.match(r"睡眠 (\d+(\.\d+)?)小時", text):
        save_record(user_id, "sleep", f"{m.group(1)}小時")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="😴 已記錄")
        )
        return

# =========================
# ⭐ Cron 主動推播（真的會說話）
# =========================
@app.route("/cron")
def cron():
    # 🔐 驗證 cron secret
    if request.args.get("secret") != CRON_SECRET:
        return "Forbidden", 403

    user_ids = get_all_user_ids()  # ✅ 正確函式

    if not user_ids:
        return "no users"

    hour = datetime.now().hour

    # 早晚訊息
    if hour < 12:
        msg = "☀️ 早安～今天也一起慢慢來 🤍\n記得你不是一個人"
    else:
        msg = "🌙 晚安～今天辛苦你了 🤍\n寶寶有你真的很幸福"

    for uid in user_ids:
        try:
            line_bot_api.push_message(
                uid,
                TextSendMessage(text=msg)
            )
        except Exception as e:
            print("push error:", e)

    return f"pushed {len(user_ids)} users"