import requests
from config import Config


def send_telegram_alert(order):
    """
    Safe Telegram sender:
    - Handles all statuses
    - Never breaks main flow
    - Adds timeout + error protection
    """

    if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
        return

    try:
        msg = format_message(order)

        url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"

        payload = {
            "chat_id": Config.TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        }

        # ✅ timeout added (important)
        response = requests.post(url, json=payload, timeout=3)

        if response.status_code != 200:
            print("Telegram API error:", response.text)

    except Exception as e:
        # ❌ never crash main system
        print("Telegram send error:", e)


# --------------------------------------------------
# 🧠 MESSAGE FORMATTER (ALL CASES HANDLED)
# --------------------------------------------------
def format_message(o):
    status = o.get("status", "UNKNOWN")

    # 🎯 Emoji mapping
    if status == "PLACED":
        emoji = "🟢"
        title = "ORDER PLACED"
    elif status == "IGNORED":
        emoji = "🟡"
        title = "ORDER IGNORED"
    elif status == "FAILED":
        emoji = "🔴"
        title = "ORDER FAILED"
    else:
        emoji = "⚪"
        title = "ORDER UPDATE"

    # ✅ Safe getters (avoid crash)
    order_id = o.get("order_id", "NA")
    trade_type = o.get("trade_type", "NA")
    symbol = o.get("symbol", "NA")
    strike = o.get("strike", "NA")
    strike_price = o.get("strike_price", "NA")
    alert_price = o.get("alert_price", "NA")
    created_at = o.get("created_at", "NA")

    # 🧾 Base message
    msg = f"""
<b>{emoji} {title}</b>

<b>ID:</b> {order_id}
<b>Type:</b> {trade_type}
<b>Symbol:</b> {symbol}

<b>Strike:</b> {strike}
<b>Price:</b> {strike_price}
<b>Alert:</b> {alert_price}

<b>Time:</b> {created_at}
"""

    # 🔴 Add failure details
    if status == "FAILED":
        msg += f"""

<b>Error:</b> {o.get('error_reason', 'NA')}
<b>Step:</b> {o.get('failed_step', 'NA')}
"""

    # 🟡 Add ignored reason (optional future use)
    if status == "IGNORED":
        msg += "\n<i>Note: Duplicate / ignored based on logic</i>"

    return msg.strip()