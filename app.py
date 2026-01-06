@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    # 🍼 喝奶 120ml
    milk_match = re.match(r"喝奶\s*(\d+)\s*ml", text)

    # 😴 睡眠 2小時 / 1.5小時
    sleep_match = re.match(r"睡眠\s*(\d+(\.\d+)?)\s*小時", text)

    # 💩 / 🚽 換尿布 大便 / 尿尿
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
    )