from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FollowEvent
)
from datetime import datetime, timedelta
import os, re
from db import *

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
CRON_SECRET = os.getenv("CRON_SECRET", "123456")

init_db()

# ===== 基本 =====
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
                "👋 歡迎你，辛苦了 🤍\n\n"
                "我會陪你一起記錄寶寶的每一天。\n\n"
                "請先告訴我：\n"
                "📅 設定生日 YYYY-MM-DD\n"
                "或\n"
                "🤰 設定預產期 YYYY-MM-DD"
            )
        )
    )

# ===== 今日溫柔總回顧 =====
def build_today_summary(user_id):
    records = get_today_records_with_time(user_id)

    milk, milk_ml, milk_details = 0, 0, []
    sleep, sleep_hr = 0, 0
    diaper, poop, pee = 0, 0, 0

    for t, v, c in records:
        tm = c[11:16]
        if t == "milk":
            milk += 1
            ml = int(v.replace("ml", ""))
            milk_ml += ml
            milk_details.append(f"{tm} · {ml} ml")
        elif t == "sleep":
            sleep += 1
            sleep_hr += float(v.replace("小時", ""))
        elif t == "diaper":
            diaper += 1
            if v == "大便":
                poop += 1
            elif v == "尿尿":
                pee += 1

    text = "🌙 今日寶寶小日記\n\n"

    if milk > 0:
        text += f"🍼 今天喝奶 {milk} 次，共 {milk_ml} ml\n"
        text += "\n".join(milk_details) + "\n\n"
    else:
        text += "🍼 今天還沒有記錄喝奶\n\n"

    if sleep > 0:
        text += f"😴 睡眠 {sleep} 次，累積約 {sleep_hr:.1f} 小時\n\n"
    else:
        text += "😴 今天還沒有記錄睡眠\n\n"

    if diaper > 0:
        text += (
            f"👶 換尿布 {diaper} 次\n"
            f"・大便 {poop} 次\n"
            f"・尿尿 {pee} 次\n\n"
        )
    else:
        text += "👶 今天還沒有記錄換尿布\n\n"

    text += "💛 辛苦了，謝謝你溫柔地照顧寶寶的一天。"

    return text

def build_day_count(user_id):
    due, birth, *_ = get_user_settings(user_id)
    today = datetime.now().date()

    if birth:
        d = datetime.strptime(birth, "%Y-%m-%d").date()
        return f"📅 寶寶出生第 {(today - d).days + 1} 天"

    if due:
        d = datetime.strptime(due, "%Y-%m-%d").date()
        return f"🤰 距離預產期 {(d - today).days} 天"

    return "尚未設定生日或預產期"

# ===== 訊息處理 =====
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
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
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 已設定寶寶生日"))
        return

    if m := re.match(r"設定預產期 (\d{4}-\d{2}-\d{2})", text):
        due_str = m.group(1)
        upsert_user_settings(user_id, due_date=due_str)

        due = datetime.strptime(due_str, "%Y-%m-%d")
        remind = due - timedelta(days=60)
        if remind > datetime.now():
            add_reminder(user_id, "hospital_bag", remind.strftime("%Y-%m-%d 09:00:00"))

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="🤍 已設定預產期，我會在兩個月前提醒你準備待產包")
        )
        return

    if m := re.match(r"喝奶 (\d+)ml", text):
        save_record(user_id, "milk", f"{m.group(1)}ml")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🍼 已記錄喝奶"))
        return

    if text in ["換尿布 大便", "換尿布 尿尿"]:
        value = "大便" if "大便" in text else "尿尿"
        save_record(user_id, "diaper", value)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"👶 已記錄換尿布（{value}）"))
        return

    if m := re.match(r"睡眠 (\d+(\.\d+)?)小時", text):
        save_record(user_id, "sleep", f"{m.group(1)}小時")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="😴 已記錄睡眠"))
        return

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text=(
                "你可以這樣跟我說 🤍\n\n"
                "🍼 喝奶 120ml\n"
                "👶 換尿布 大便 / 尿尿\n"
                "😴 睡眠 2小時\n\n"
                "📊 今天\n📅 天數"
            )
        )
    )

# ===== Cron =====
@app.route("/cron")
def cron():
    if request.args.get("secret") != CRON_SECRET:
        return "forbidden", 403

    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    today_str = now.strftime("%Y-%m-%d")

    # ⏰ 提醒
    for rid, uid, rtype, payload in get_due_reminders(now_str):
        if rtype == "hospital_bag":
            msg = (
                "👜 溫柔提醒\n\n"
                "距離預產期大約剩下兩個月了 🤍\n"
                "可以慢慢開始準備待產包囉。"
            )
        else:
            msg = "⏰ 提醒時間到了唷"

        line_bot_api.push_message(uid, TextSendMessage(text=msg))
        mark_reminder_done(rid)

    # 🌞 09:00 育兒知識 + 天數
    if now.hour == 9 and now.minute == 0:
        for uid in get_all_user_ids():
            _, _, _, last_push, _ = get_user_settings(uid)
            if last_push == today_str:
                continue

            conn = get_conn()
            c = conn.cursor()
            c.execute("SELECT content FROM daily_tips ORDER BY RANDOM() LIMIT 1")
            row = c.fetchone()
            conn.close()

            msg = "🌞 早安，今天也一起溫柔地照顧寶寶 🤍\n\n"
            msg += build_day_count(uid)

            if row:
                msg += "\n\n👶 今日育兒小提醒\n" + row[0]

            line_bot_api.push_message(uid, TextSendMessage(text=msg))
            set_last_daily_push_date(uid, today_str)

    # 🌙 22:15 今日總回顧
    if now.hour == 22 and now.minute == 15:
        for uid in get_all_user_ids():
            line_bot_api.push_message(
                uid,
                TextSendMessage(text=build_today_summary(uid) + "\n\n" + build_day_count(uid))
            )

    return "OK"