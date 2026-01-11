from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FollowEvent
from datetime import datetime, timedelta
import os, re

from db import *

# ===== OpenAI =====
from openai import OpenAI
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
                "我可以幫你記錄喝奶、換尿布、睡眠，並每天早晚提醒與總結。\n\n"
                "📅 設定生日 YYYY-MM-DD\n"
                "🤰 設定預產期 YYYY-MM-DD\n\n"
                "🍼 喝奶 120ml\n"
                "👶 換尿布 大便 / 尿尿 / 大便+尿尿\n"
                "😴 睡眠 1.5小時\n\n"
                "輸入 help 也可以看指令喔！\n\n"
                "☀️ 早上 9 點我會提醒你\n"
                "🌙 晚上 9 點我會幫你做今日總結"
            )
        )
    )

# =========================
# 今日總結
# =========================
def build_today_summary(user_id):
    records = get_today_records_with_time(user_id) or []

    milk, milk_ml = 0, 0
    sleep, sleep_hr = 0, 0.0
    diaper, poop, pee = 0, 0, 0
    milk_details = []

    # records 可能是 (record_type, value, created_at) 或 (t, v, c)
    for row in records:
        if len(row) >= 3:
            t, v, c = row[0], row[1], row[2]
        else:
            continue

        tm = str(c)[11:16] if c else ""

        if t == "milk":
            milk += 1
            # v 可能是 "120ml" / "120 ml"
            m = re.search(r"(\d+)", str(v))
            ml = int(m.group(1)) if m else 0
            milk_ml += ml
            milk_details.append(f"{tm} · {ml} ml")

        elif t == "sleep":
            sleep += 1
            # v 可能是 "1.5小時" / "2"
            m = re.search(r"(\d+(\.\d+)?)", str(v))
            hrs = float(m.group(1)) if m else 0.0
            sleep_hr += hrs

        elif t == "diaper":
            diaper += 1
            val = str(v)
            if "大便" in val:
                poop += 1
            if "尿" in val:
                pee += 1

    text = "🌙 今日寶寶小日記\n\n"
    text += f"🍼 喝奶 {milk} 次，共 {milk_ml} ml\n"
    if milk_details:
        text += "\n".join(milk_details) + "\n\n"
    else:
        text += "\n"

    text += f"😴 睡眠 {sleep} 次，約 {sleep_hr:.1f} 小時\n\n"
    text += f"👶 換尿布 {diaper} 次（大便 {poop} / 尿尿 {pee}）\n\n"
    text += "💛 今天你已經做得很好了，晚安。"

    return text

# =========================
# 天數
# =========================
def build_day_count(user_id):
    due, birth = get_user_settings(user_id)
    today = datetime.now().date()

    if birth:
        d = datetime.strptime(birth, "%Y-%m-%d").date()
        return f"📅 寶寶出生第 {(today - d).days + 1} 天"

    if due:
        d = datetime.strptime(due, "%Y-%m-%d").date()
        return f"🤰 距離預產期 {(d - today).days} 天"

    return "📅 今天也是值得被溫柔對待的一天"

# =========================
# ChatGPT 回覆
# =========================
def chatgpt_reply(user_text):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一位溫柔、專業的育兒安撫師，"
                        "用簡單、支持性的語氣回應家長的問題，"
                        "避免醫療診斷，給予情緒支持與實用建議。"
                    )
                },
                {"role": "user", "content": user_text}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("ChatGPT error:", e)
        return "我在這裡陪你 🤍 你已經很努力了。"

# =========================
# 指令說明
# =========================
def build_help():
    return (
        "🧸 可用指令\n\n"
        "📅 設定生日 YYYY-MM-DD\n"
        "🤰 設定預產期 YYYY-MM-DD\n\n"
        "🍼 喝奶 120ml（也可：奶 120ml）\n"
        "👶 換尿布 大便 / 尿尿 / 大便+尿尿\n"
        "😴 睡眠 1.5小時（也可：睡 2小時）\n\n"
        "📌 今天：今日總結\n"
        "📌 天數：預產期倒數/出生天數\n"
    )

# =========================
# 使用者訊息
# =========================
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    upsert_user_settings(user_id)
    reply = None

    # help
    if text.lower() in ["help", "h", "指令", "功能", "說明"]:
        reply = build_help()

    # 設定生日
    if reply is None:
        m_birth = re.match(r"設定生日\s*(\d{4}-\d{2}-\d{2})", text)
        if m_birth:
            birth = m_birth.group(1)
            set_birth_date(user_id, birth)
            reply = (
                f"🎂 已幫你設定寶寶生日為 {birth}\n\n"
                "之後我會依月齡提醒你重要發展與照顧重點 💛"
            )

    # 設定預產期
    if reply is None:
        m_due = re.match(r"設定預產期\s*(\d{4}-\d{2}-\d{2})", text)
        if m_due:
            due = m_due.group(1)
            set_due_date(user_id, due)
            reply = (
                f"🤰 已幫你設定預產期為 {due}\n\n"
                "我會在孕期一路陪你準備迎接寶寶 🌙"
            )

    # 快捷指令
    if reply is None and text == "今天":
        reply = build_today_summary(user_id)

    if reply is None and text == "天數":
        reply = build_day_count(user_id)

    # =========================
    # ✅ 記錄功能（你缺的就是這段）
    # =========================

    # 1) 喝奶：喝奶 120ml / 奶 120ml
    if reply is None:
        m_milk = re.match(r"^(喝奶|奶)\s*(\d+)\s*(ml|ML)?$", text)
        if m_milk:
            ml = m_milk.group(2)
            save_record(user_id, "milk", f"{ml}ml")
            reply = f"🍼 已記錄：{datetime.now().strftime('%H:%M')} 喝奶 {ml} ml"

    # 2) 換尿布：換尿布 大便 / 尿尿 / 大便+尿尿
    if reply is None:
        m_diaper = re.match(r"^換尿布\s*(大便\+尿尿|尿尿\+大便|大便|尿尿)$", text)
        if m_diaper:
            diaper_type = m_diaper.group(1)
            # 統一格式
            if diaper_type in ["尿尿+大便", "大便+尿尿"]:
                diaper_type = "大便+尿尿"
            save_record(user_id, "diaper", diaper_type)
            reply = f"👶 已記錄：{datetime.now().strftime('%H:%M')} 換尿布（{diaper_type}）"

    # 3) 睡眠：睡眠 1.5小時 / 睡 2小時
    if reply is None:
        m_sleep = re.match(r"^(睡眠|睡)\s*(\d+(\.\d+)?)\s*(小時|hr|hrs)?$", text)
        if m_sleep:
            hrs = m_sleep.group(2)
            save_record(user_id, "sleep", f"{hrs}小時")
            reply = f"😴 已記錄：{datetime.now().strftime('%H:%M')} 睡眠 {hrs} 小時"

    # ⭐ ChatGPT 接手（放最後，避免吃掉記錄指令）
    if reply is None:
        reply = chatgpt_reply(text)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

# =========================
# CRON
# =========================
@app.route("/cron")
def cron():
    if request.args.get("secret") != CRON_SECRET:
        return "Forbidden", 403

    users = get_all_user_ids()
    if not users:
        return "no users"

    now = datetime.utcnow() + timedelta(hours=8)
    now_hour = now.hour

    for user_id in users:
        try:
            if now_hour == 9:
                msg = (
                    "☀️ 早安，辛苦的你 🤍\n\n"
                    f"{build_day_count(user_id)}\n\n"
                    f"📚 今日育兒小提醒：\n{get_random_daily_tip()}"
                )
                line_bot_api.push_message(user_id, TextSendMessage(text=msg))

            elif now_hour == 21:
                msg = build_today_summary(user_id)
                line_bot_api.push_message(user_id, TextSendMessage(text=msg))

        except Exception as e:
            print("push error:", e)

    return "cron ok"