import logging
from datetime import datetime
from pymongo import MongoClient

from config import Config
from get_keys import load_valid_dhan_credentials
from dhanhq.dhanhq import dhanhq


# LOGGER
logger = logging.getLogger("dhan_service")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

console = logging.StreamHandler()
console.setFormatter(formatter)

file = logging.FileHandler("dhan_service.log")
file.setFormatter(formatter)

logger.addHandler(console)
logger.addHandler(file)


# MONGO
try:
    client = MongoClient(Config.MONGO_URI)
    db = client[Config.DB_NAME]
    orders_collection = db[Config.ORDER_COLLECTION]
    logger.info("[INFO] MongoDB connected")
except Exception as e:
    logger.error(f"[ERROR] Mongo failed: {e}")
    orders_collection = None


# SAVE LOG
def save_log(data):
    if orders_collection is None:
        return

    try:
        orders_collection.insert_one(data)
    except Exception as e:
        logger.error(f"Mongo save error: {e}")


# DHAN CLIENT
def get_dhan_client():
    creds = load_valid_dhan_credentials()

    if not creds:
        raise Exception("No valid token")

    return dhanhq(
        creds["client_id"],
        creds["access_token"]
    )


# PRODUCT TYPE
def resolve_product_type(exchange_segment, mode):
    exchange_segment = exchange_segment.upper()
    mode = (mode or "INTRADAY").upper()

    if exchange_segment in ["NSE_EQ", "BSE_EQ"]:
        return "CNC" if mode == "DELIVERY" else "INTRA"

    elif exchange_segment in ["NSE_FNO", "BSE_FNO"]:
        return "MARGIN" if mode == "DELIVERY" else "INTRA"

    return "INTRA"