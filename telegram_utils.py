import requests
from config import Config

def send_telegram_alert(order):
    if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
        return

    msg = format_message(order)

    url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": Config.TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }

    requests.post(url, json=payload)


def format_message(o):
    status_emoji = "🟢" if o["status"] == "PLACED" else "🔴"

    return f"""
<b>{status_emoji} ORDER ALERT</b>

<b>ID:</b> {o['order_id']}
<b>Type:</b> {o['trade_type']}
<b>Symbol:</b> {o['symbol']}

<b>Strike:</b> {o['strike']}
<b>Price:</b> {o['strike_price']}
<b>Alert Price:</b> {o['alert_price']}

<b>Time:</b> {o['created_at']}
"""