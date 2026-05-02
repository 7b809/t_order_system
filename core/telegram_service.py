import requests
import os

from django.conf import settings
from django.utils import timezone

from core.logger import logger


MAX_FILE_SIZE = 45 * 1024 * 1024  # 45 MB


def _get_ist_timestamp():
    """
    Returns current time in IST using Django timezone settings
    """
    return timezone.localtime().strftime("%Y-%m-%d_%H-%M-%S")


def send_telegram_message(message: str):
    try:
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        chat_id = getattr(settings, "TELEGRAM_CHAT_ID", None)

        if not token or not chat_id:
            logger.warning("[TELEGRAM] Missing token or chat_id")
            return

        url = f"https://api.telegram.org/bot{token}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        response = requests.post(url, json=payload, timeout=5)

        if response.status_code != 200:
            logger.error(f"[TELEGRAM ERROR] {response.text}")

    except Exception as e:
        logger.error(f"[TELEGRAM ERROR] {e}")


def send_telegram_file(file_path: str, caption: str = None):
    try:
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        chat_id = getattr(settings, "TELEGRAM_CHAT_ID", None)

        if not token or not chat_id:
            logger.warning("[TELEGRAM FILE] Missing token or chat_id")
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
                    "caption": caption or f"📄 Log file: {new_name}"
                }

                response = requests.post(url, data=data, files=files, timeout=30)

                if response.status_code != 200:
                    logger.error(f"[TELEGRAM FILE ERROR] {response.text}")

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
                    "caption": caption or f"📄 Log chunk {part}: {part_name}"
                }

                response = requests.post(url, data=data, files=files, timeout=60)

                if response.status_code != 200:
                    logger.error(f"[TELEGRAM FILE ERROR] {response.text}")

                part += 1

    except Exception as e:
        logger.error(f"[TELEGRAM FILE ERROR] {e}")