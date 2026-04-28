import requests, os
from config import Config
from services.base_service import logger
from datetime import datetime, timedelta


MAX_FILE_SIZE = 45 * 1024 * 1024  # 45 MB


def _get_ist_timestamp():
    ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    return ist.strftime("%Y-%m-%d_%H-%M-%S")

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



def send_telegram_file(file_path: str):
    try:
        token = Config.TELEGRAM_BOT_TOKEN
        chat_id = Config.TELEGRAM_CHAT_ID

        if not token or not chat_id:
            return

        if not os.path.exists(file_path):
            logger.error(f"[TELEGRAM FILE] File not found: {file_path}")
            return

        file_size = os.path.getsize(file_path)
        base_name = os.path.basename(file_path)
        timestamp = _get_ist_timestamp()

        url = f"https://api.telegram.org/bot{token}/sendDocument"

        # -----------------------------------
        # ✅ CASE 1: File within limit
        # -----------------------------------
        if file_size <= MAX_FILE_SIZE:
            new_name = f"{base_name}_{timestamp}.log"

            with open(file_path, "rb") as f:
                files = {"document": (new_name, f)}

                data = {
                    "chat_id": chat_id,
                    "caption": f"📄 Log file: {new_name}"
                }

                requests.post(url, data=data, files=files, timeout=30)

            return

        # -----------------------------------
        # ✅ CASE 2: Split into chunks
        # -----------------------------------
        logger.info("[TELEGRAM FILE] Large file → splitting...")

        part = 1
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(MAX_FILE_SIZE)
                if not chunk:
                    break

                part_name = f"{base_name}_{timestamp}_part{part}.log"

                files = {
                    "document": (part_name, chunk)
                }

                data = {
                    "chat_id": chat_id,
                    "caption": f"📄 Log chunk {part}: {part_name}"
                }

                requests.post(url, data=data, files=files, timeout=60)

                part += 1

    except Exception as e:
        logger.error(f"[TELEGRAM FILE ERROR] {e}")        