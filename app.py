from flask import Flask

app = Flask(__name__)

print("🔥🔥 THIS IS THE NEW APP.PY 🔥🔥")

@app.route("/health")
def health():
    return "NEW APP IS RUNNING", 200

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@app.route("/")
def home():
    return "LINE BOT HOME OK"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    handler.handle(body, signature)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    print("🔥 收到訊息：", text)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"你剛剛說的是：{text}")
    )

if __name__ == "__main__":
    app.run()