import requests
from config import Config
from services.base_service import logger

def send_telegram_message(message: str):
    try:
        token = Config.TELEGRAM_BOT_TOKEN
        chat_id = Config.TELEGRAM_CHAT_ID

        if not token or not chat_id:
            return

        url = f"https://api.telegram.org/bot{token}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        requests.post(url, json=payload, timeout=5)

    except Exception as e:
        logger.error(f"[TELEGRAM ERROR] {e}")