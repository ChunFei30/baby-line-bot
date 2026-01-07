from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FollowEvent
from datetime import datetime, timedelta
import os, re
from db import *

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
CRON_SECRET = os.getenv("CRON_SECRET", "123456")

init_db()

@app.route("/")
def index():
    return "LINE BABY BOT RUNNING"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# ===== 新好友加入 =====
@handler.add(FollowEvent)
def handle_follow(event):
    user_id = event.source.user_id
    upsert_user_settings(user_id)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text=(
                "👋 歡迎使用育兒小幫手\n\n"
                "請先告訴我：\n"
                "📅 設定生日 YYYY-MM-DD\n"
                "或\n"
                "🤰 設定預產期 YYYY-MM-DD"
            )
        )
    )

# ===== 共用文字 =====
def build_today_summary(user_id):
    records = get_today_records_with_time(user_id)
    milk, milk_ml, details = 0, 0, []
    sleep, sleep_hr = 0, 0
    diaper, poop, pee = 0, 0, 0

    for t, v, c in records:
        tm = c[11:16]
        if t == "milk":
            milk += 1
            ml = int(v.replace("ml",""))
            milk_ml += ml
            details.append(f"{tm} {ml}ml")
        elif t == "sleep":
            sleep += 1
            sleep_hr += float(v.replace("小時",""))
        elif t == "diaper":
            diaper += 1
            poop += (v=="大便")
            pee += (v=="尿尿")

    text = f"📊 今日寶寶紀錄\n\n🍼 喝奶 {milk} 次，共 {milk_ml} ml\n"
    text += "\n".join(details) + "\n\n" if details else "（尚未記錄）\n\n"
    text += f"😴 睡眠 {sleep} 次，共 {sleep_hr:.1f} 小時\n\n"
    text += f"👶 換尿布 {diaper} 次\n• 大便 {poop} 次\n• 尿尿 {pee} 次"
    return text

def build_day_count(user_id):
    due, birth, *_ = get_user_settings(user_id)
    today = datetime.now().date()
    if birth:
        d = datetime.strptime(birth,"%Y-%m-%d").date()
        return f"📅 寶寶出生第 {(today-d).days+1} 天"
    if due:
        d = datetime.strptime(due,"%Y-%m-%d").date()
        return f"🤰 距離預產期 {(d-today).days} 天"
    return "尚未設定生日或預產期"

# ===== 訊息處理 =====
@handler.add(MessageEvent, message=TextMessage)
def handle(event):
    user_id = event.source.user_id
    text = event.message.text.strip()
    upsert_user_settings(user_id)

    if text == "今天":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=build_today_summary(user_id)))
        return

    if text == "天數":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=build_day_count(user_id)))
        return

    if m := re.match(r"設定生日 (\d{4}-\d{2}-\d{2})", text):
        upsert_user_settings(user_id, birth_date=m.group(1))
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 已設定生日"))
        return

    if m := re.match(r"設定預產期 (\d{4}-\d{2}-\d{2})", text):
        due_str = m.group(1)
        upsert_user_settings(user_id, due_date=due_str)
        due = datetime.strptime(due_str,"%Y-%m-%d")
        remind = due - timedelta(days=60)
        if remind > datetime.now():
            add_reminder(user_id, "hospital_bag", remind.strftime("%Y-%m-%d 09:00:00"))
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 已設定預產期"))
        return

    if m := re.match(r"喝奶 (\d+)ml", text):
        save_record(user_id, "milk", f"{m.group(1)}ml")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🍼 已記錄喝奶"))
        return

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="🍼 喝奶 120ml\n📊 今天\n📅 天數")
    )

# ===== Cron =====
@app.route("/cron")
def cron():
    if request.args.get("secret") != CRON_SECRET:
        return "forbidden",403

    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    for rid, uid, rtype, payload in get_due_reminders(now_str):
        msg = "⏰ 提醒時間到囉！"
        if rtype == "hospital_bag":
            msg = "👜 距離預產期 2 個月，記得準備待產包"
        line_bot_api.push_message(uid, TextSendMessage(text=msg))
        mark_reminder_done(rid)

    if now.hour == 9 and now.minute == 0:
        for uid in get_all_user_ids():
            _, birth,_, _ = get_user_settings(uid)
            if birth:
                days = (datetime.now().date() - datetime.strptime(birth,"%Y-%m-%d").date()).days
                month = days // 30
                if month > 0 and not has_pushed_month(uid, month):
                    care = get_monthly_care(month)
                    if care:
                        line_bot_api.push_message(uid, TextSendMessage(text=f"📌 寶寶滿 {month} 個月提醒\n\n{care}"))
                        mark_pushed_month(uid, month)

    if now.hour == 21 and now.minute == 0:
        for uid in get_all_user_ids():
            line_bot_api.push_message(
                uid,
                TextSendMessage(text=build_today_summary(uid) + "\n\n" + build_day_count(uid))
            )

    return "OK"