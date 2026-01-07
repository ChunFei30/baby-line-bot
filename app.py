from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from datetime import datetime, timedelta
import os, re

from db import *

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
CRON_SECRET = os.getenv("CRON_SECRET", "123456")

init_db()
print("🔥 BABY BOT FINAL VERSION WITH HOSPITAL BAG REMINDER 🔥")

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
    due, birth, _, _ = get_user_settings(user_id)
    today = datetime.now().date()
    if birth:
        d = datetime.strptime(birth,"%Y-%m-%d").date()
        return f"📅 寶寶出生第 {(today-d).days+1} 天"
    if due:
        d = datetime.strptime(due,"%Y-%m-%d").date()
        return f"🤰 距離預產期 {(d-today).days} 天"
    return "尚未設定生日或預產期"

# ===== LINE 處理 =====
@handler.add(MessageEvent, message=TextMessage)
def handle(event):
    user_id = event.source.user_id
    text = event.message.text.strip()
    upsert_user_settings(user_id)

    # 今天
    if text == "今天":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=build_today_summary(user_id)))
        return

    # 天數
    if text == "天數":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=build_day_count(user_id)))
        return

    # 設定生日
    if m := re.match(r"設定生日 (\d{4}-\d{2}-\d{2})", text):
        upsert_user_settings(user_id, birth_date=m.group(1))
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 已設定生日"))
        return

    # 設定預產期（含待產包提醒）
    if m := re.match(r"設定預產期 (\d{4}-\d{2}-\d{2})", text):
        due_str = m.group(1)
        upsert_user_settings(user_id, due_date=due_str)

        due = datetime.strptime(due_str,"%Y-%m-%d")
        remind = due - timedelta(days=60)

        if remind > datetime.now():
            add_reminder(
                user_id,
                "hospital_bag",
                remind.strftime("%Y-%m-%d 09:00:00"),
                "待產包"
            )

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=(
                    f"✅ 已設定預產期：{due_str}\n\n"
                    "👜 我會在「預產期前約兩個月」提醒你準備待產包"
                )
            )
        )
        return

    # 喝奶（自動平均）
    if m := re.match(r"喝奶 (\d+)ml", text):
        amount = m.group(1)
        save_record(user_id,"milk",f"{amount}ml")

        times = get_last_milk_times(user_id,5)
        avg = None
        if len(times)>=2:
            dts = sorted(datetime.strptime(t,"%Y-%m-%d %H:%M:%S") for t in times)
            diffs = [(dts[i]-dts[i-1]).seconds/3600 for i in range(1,len(dts))]
            avg = round(sum(diffs)/len(diffs),1)

        if not avg:
            _,_,avg,_ = get_user_settings(user_id)

        due = datetime.now()+timedelta(hours=avg)
        add_reminder(user_id,"feed",due.strftime("%Y-%m-%d %H:%M:%S"),str(avg))

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"🍼 已記錄 {amount}ml\n📈 平均喝奶間隔 {avg} 小時\n⏰ 我會自動提醒你"
            )
        )
        return

    # 預設說明
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text="🍼 喝奶 120ml\n📊 今天\n📅 天數\n設定生日 YYYY-MM-DD\n設定預產期 YYYY-MM-DD"
        )
    )

# ===== Cron（提醒 + 每日推播）=====
@app.route("/cron")
def cron():
    if request.args.get("secret") != CRON_SECRET:
        return "forbidden",403

    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # 提醒處理
    for rid, uid, rtype, payload in get_due_reminders(now_str):
        if rtype == "feed":
            msg = f"⏰ 距離上次喝奶約 {payload} 小時囉"
        elif rtype == "hospital_bag":
            msg = (
                "👜 待產包提醒\n\n"
                "距離預產期剩下約 2 個月囉 🤍\n"
                "可以開始準備待產包了～\n\n"
                "👩 媽媽用品\n"
                "👶 寶寶用品\n"
                "📄 文件與證件"
            )
        else:
            msg = "⏰ 提醒時間到囉！"

        line_bot_api.push_message(uid, TextSendMessage(text=msg))
        mark_reminder_done(rid)

    # 每天 21:00 今日總結
    if now.hour==21 and now.minute==0:
        for uid in get_all_user_ids():
            summary = build_today_summary(uid) + "\n\n" + build_day_count(uid)
            line_bot_api.push_message(uid, TextSendMessage(text=summary))
            set_last_daily_push_date(uid, now.strftime("%Y-%m-%d"))

    return "OK"