print("🔥 RENDER IS RUNNING APP.PY - FINAL CONFIRM 🔥")
print("🔥 LINE BABY BOT START 🔥")

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

from db import save_record  # 你原本的資料庫函式

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))


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
# 只有這一個 Message handler（很重要）
# =========================
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id

    print("📩 收到訊息：", repr(text))

    try:
        # 🍼 喝奶
        if "喝奶" in text:
            value = text.replace("喝奶", "").strip()
            save_record(user_id, "feeding", value)
            reply = f"🍼 已記錄喝奶：{value}"

        # 😴 睡眠
        elif "睡眠" in text:
            value = text.replace("睡眠", "").strip()
            save_record(user_id, "sleep", value)
            reply = f"😴 已記錄睡眠：{value}"

        # 👶 換尿布
        elif "換尿布" in text:
            value = text.replace("換尿布", "").strip()
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
        reply = f"⚠️ 發生錯誤：{str(e)}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )


# =========================
# 本地測試用（Render 不會用到）
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)