from core.db import get_orders_collection
from core.utils import current_ist_time
from core.logger import get_logger
from .dhan_service import DhanService

logger = get_logger("broker_service")


def place_default_order():
    """
    Example: place default NIFTY CE order
    """

    orders_collection = get_orders_collection()   # ✅ FIX

    try:
        dhan = DhanService()   # ✅ create fresh instance (better for token handling)

        security_id = "49081"  # example
        qty = 50
        price = 0  # MARKET

        res = dhan.place_order(security_id, qty, price, "BUY")

        order_doc = {
            "type": "DHAN",
            "status": res.get("status", "UNKNOWN"),
            "response": res,
            "security_id": security_id,
            "qty": qty,
            "side": "BUY",
            "created_at": current_ist_time()
        }

        orders_collection.insert_one(order_doc)

        logger.info(f"Dhan order placed → {res}")

        return res

    except Exception as e:
        logger.error(f"Dhan order error: {str(e)}", exc_info=True)
        return {"error": str(e)}


# -----------------------------------
# ❌ CANCEL ORDER
# -----------------------------------
def cancel_order(order_id):
    try:
        dhan = DhanService()

        res = dhan.cancel_order(order_id)

        logger.info(f"Order cancelled → {order_id}")

        return res

    except Exception as e:
        logger.error(f"Cancel error: {str(e)}", exc_info=True)
        return {"error": str(e)}


# -----------------------------------
# 📊 GET ALL ORDERS (FROM DHAN)
# -----------------------------------
def get_all_orders():
    try:
        dhan = DhanService()

        return dhan.get_orders()

    except Exception as e:
        logger.error(f"Get orders error: {str(e)}", exc_info=True)
        return {"error": str(e)}


# -----------------------------------
# 📊 PORTFOLIO
# -----------------------------------
def get_portfolio():
    try:
        dhan = DhanService()

        return {
            "positions": dhan.get_positions(),
            "holdings": dhan.get_holdings()
        }

    except Exception as e:
        logger.error(f"Portfolio error: {str(e)}", exc_info=True)
        return {"error": str(e)}