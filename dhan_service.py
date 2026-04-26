import logging
from datetime import datetime
from pymongo import MongoClient

from config import Config
from get_keys import load_valid_dhan_credentials
from dhanhq.dhanhq import dhanhq


# -----------------------------------
# 🪵 LOGGER
# -----------------------------------
logger = logging.getLogger("dhan_service")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

console = logging.StreamHandler()
console.setFormatter(formatter)

file = logging.FileHandler("dhan_service.log")
file.setFormatter(formatter)

logger.addHandler(console)
logger.addHandler(file)


# -----------------------------------
# 🔌 MONGO
# -----------------------------------
try:
    client = MongoClient(Config.MONGO_URI)
    db = client[Config.DB_NAME]
    orders_collection = db[Config.ORDER_COLLECTION]
    logger.info("[INFO] MongoDB connected")
except Exception as e:
    logger.error(f"[ERROR] Mongo failed: {e}")
    orders_collection = None


# -----------------------------------
# 💾 SAVE LOG
# -----------------------------------
def save_log(data):
    if orders_collection is None:
        return

    try:
        orders_collection.insert_one(data)
    except Exception as e:
        logger.error(f"Mongo save error: {e}")


# -----------------------------------
# 🔐 DHAN CLIENT
# -----------------------------------
def get_dhan_client():
    creds = load_valid_dhan_credentials()

    if not creds:
        raise Exception("No valid token")

    return dhanhq(
        creds["client_id"],
        creds["access_token"]
    )


# -----------------------------------
#  NEW: PRODUCT TYPE RESOLVER (ADDED ONLY)
# -----------------------------------
def resolve_product_type(exchange_segment, mode):
    exchange_segment = exchange_segment.upper()
    mode = (mode or "INTRADAY").upper()

    if exchange_segment in ["NSE_EQ", "BSE_EQ"]:
        return "CNC" if mode == "DELIVERY" else "INTRA"

    elif exchange_segment in ["NSE_FNO", "BSE_FNO"]:
        return "MARGIN" if mode == "DELIVERY" else "INTRA"

    return "INTRA"


# -----------------------------------
#  PLACE ORDER
# -----------------------------------
def place_order(
    security_id,
    exchange_segment="NSE_FNO",
    transaction_type="BUY",
    quantity=1,
    product_type="MARGIN",
    price=None,
    use_market=True
):
    try:
        dhan = get_dhan_client()

        txn = dhan.BUY if transaction_type.upper() == "BUY" else dhan.SELL

        #  FIXED PRODUCT LOGIC (ONLY CHANGE)
        resolved_product = resolve_product_type(exchange_segment, product_type)
        product = getattr(dhan, resolved_product)

        # LIMIT vs MARKET
        if price is not None:
            use_market = False

        order_type = dhan.MARKET if use_market else dhan.LIMIT

        # TEST MODE  AMO
        is_testing = Config.TESTING_FLAG
        after_market_order = is_testing

        if is_testing:
            logger.info(" TEST MODE  AMO ORDER")

        logger.info(f" Placing order {security_id} {transaction_type}")

        response = dhan.place_order(
            security_id=str(security_id),
            exchange_segment=exchange_segment,
            transaction_type=txn,
            quantity=int(quantity),
            order_type=order_type,
            product_type=product,
            price=price if price else 0,
            after_market_order=after_market_order,
            amo_time="OPEN"
        )

        save_log({
            "type": "ORDER",
            "security_id": security_id,
            "txn": transaction_type,
            "qty": quantity,
            "amo": after_market_order,
            "response": response,
            "time": datetime.utcnow()
        })

        return response

    except Exception as e:
        logger.error(f" Order failed: {e}")
        raise Exception(f"Order failed: {e}")


# -----------------------------------
#  CANCEL ORDER
# -----------------------------------
def cancel_order(order_id):
    try:
        dhan = get_dhan_client()

        response = dhan.cancel_order(order_id)

        save_log({
            "type": "CANCEL",
            "order_id": order_id,
            "response": response,
            "time": datetime.utcnow()
        })

        return response

    except Exception as e:
        logger.error(f" Cancel failed: {e}")
        raise Exception(f"Cancel failed: {e}")


# -----------------------------------
# 🔄 EXIT POSITION (IMPORTANT)
# -----------------------------------
def exit_position(
    security_id,
    exchange_segment="NSE_EQ",
    quantity=1,
    product_type="INTRA"
):
    """
    Exit = reverse order (BUY  SELL or SELL  BUY)
    """

    try:
        dhan = get_dhan_client()

        txn = dhan.SELL

        #  FIXED PRODUCT LOGIC (ONLY CHANGE)
        resolved_product = resolve_product_type(exchange_segment, product_type)
        product = getattr(dhan, resolved_product)

        logger.info(f"🔄 Exiting position {security_id}")

        response = dhan.place_order(
            security_id=str(security_id),
            exchange_segment=exchange_segment,
            transaction_type=txn,
            quantity=int(quantity),
            order_type=dhan.MARKET,
            product_type=product,
            price=0
        )

        save_log({
            "type": "EXIT",
            "security_id": security_id,
            "qty": quantity,
            "response": response,
            "time": datetime.utcnow()
        })

        return response

    except Exception as e:
        logger.error(f" Exit failed: {e}")
        raise Exception(f"Exit failed: {e}")