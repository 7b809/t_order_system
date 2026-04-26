import logging
from datetime import datetime

from config import Config
from get_keys import load_valid_dhan_credentials
from dhanhq.dhanhq import dhanhq


# -----------------------------------
# SIMPLE LOGGER (NO FILE HANDLER)
# -----------------------------------
logger = logging.getLogger("dhan_service")

if not logger.handlers:
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    logger.addHandler(console)


# -----------------------------------
# SAFE PRINT (CONTROLLED BY ENV)
# -----------------------------------
def log_print(message):
    if Config.BASE_LOGS:
        print(message)


# -----------------------------------
# SAVE LOG → MONGO (MAIN STORAGE)
# -----------------------------------
def save_log(data):
    try:
        collection = Config.get_order_collection()
        collection.insert_one(data)

        log_print(f"[MONGO] Saved: {data.get('type')}")

    except Exception as e:
        logger.error(f"Mongo save error: {e}")
        log_print(f"[MONGO ERROR] {e}")


# -----------------------------------
# DHAN CLIENT
# -----------------------------------
def get_dhan_client():
    creds = load_valid_dhan_credentials()

    if not creds:
        raise Exception("No valid token")

    log_print("[DHAN] Client initialized")

    return dhanhq(
        creds["client_id"],
        creds["access_token"]
    )


# -----------------------------------
# PRODUCT TYPE RESOLVER
# -----------------------------------
def resolve_product_type(exchange_segment, mode):
    exchange_segment = exchange_segment.upper()
    mode = (mode or "INTRADAY").upper()

    if exchange_segment in ["NSE_EQ", "BSE_EQ"]:
        result = "CNC" if mode == "DELIVERY" else "INTRA"

    elif exchange_segment in ["NSE_FNO", "BSE_FNO"]:
        result = "MARGIN" if mode == "DELIVERY" else "INTRA"

    else:
        result = "INTRA"

    log_print(f"[PRODUCT] {exchange_segment} → {result}")

    return result


# -----------------------------------
# GET LAST ORDER (FIXED VERSION)
# -----------------------------------
def get_last_order():
    """
    Get last ACTIVE order (non-AMO)
    """
    try:
        from pymongo import DESCENDING

        collection = Config.get_order_collection()

        return collection.find_one(
            {
                "type": "ORDER",
                "amo": False
            },
            sort=[("time", DESCENDING)]
        )

    except Exception as e:
        logger.error(f"[GET LAST ORDER ERROR] {e}")
        return None