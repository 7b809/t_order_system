import logging
from core.db import orders_collection
from core.utils import current_ist_time
from .dhan_service import DhanService

logger = logging.getLogger(__name__)


# ✅ FIX: Lazy loader instead of global instance
def get_dhan():
    return DhanService()


# -----------------------------------------
# SAVE ORDER
# -----------------------------------------
def save_order(res, extra=None, request_payload=None):

    try:
        if not isinstance(res, dict) or not res.get("orderId"):
            return {"error": "Invalid order response", "response": res}

        order_doc = {
            "type": "DHAN",
            "order_id": res.get("orderId"),
            "status": res.get("orderStatus"),
            "response": res,
            "request": request_payload,
            "created_at": current_ist_time()
        }

        if extra:
            order_doc.update(extra)

        orders_collection.insert_one(order_doc)

        logger.info(f"✅ Order saved: {order_doc['order_id']}")

        return order_doc

    except Exception as e:
        logger.exception("❌ Failed to save order")
        return {"error": str(e)}


# -----------------------------------------
# CANCEL ORDER
# -----------------------------------------
def cancel_order(order_id):

    try:
        res = get_dhan().cancel_order(order_id)  # ✅ FIX

        if isinstance(res, dict) and "error" in res:
            return res

        status = res.get("orderStatus") if isinstance(res, dict) else None

        if not status:
            return {"error": "Invalid cancel response", "response": res}

        orders_collection.update_one(
            {"order_id": order_id},
            {
                "$set": {
                    "status": status,
                    "cancelled_at": current_ist_time()
                }
            }
        )

        logger.info(f"❌ Order cancelled: {order_id}")

        return res

    except Exception as e:
        logger.exception(f"❌ Cancel failed for {order_id}")
        return {"error": str(e)}


# -----------------------------------------
# GET ALL ORDERS (BROKER)
# -----------------------------------------
def get_all_orders():

    try:
        return get_dhan().get_orders()  # ✅ FIX
    except Exception as e:
        logger.exception("❌ Failed to fetch orders")
        return {"error": str(e)}


# -----------------------------------------
# GET SINGLE ORDER (DB)
# -----------------------------------------
def get_order_from_db(order_id):

    try:
        return orders_collection.find_one({"order_id": order_id})
    except Exception as e:
        logger.exception(f"❌ DB fetch failed for {order_id}")
        return {"error": str(e)}


# -----------------------------------------
# GET ALL SAVED ORDERS (DB)
# -----------------------------------------
def get_all_saved_orders(limit=50):

    try:
        return list(
            orders_collection
            .find()
            .sort("created_at", -1)
            .limit(limit)
        )
    except Exception as e:
        logger.exception("❌ Failed to fetch saved orders")
        return {"error": str(e)}


# -----------------------------------------
# SYNC ORDER STATUS
# -----------------------------------------
def sync_order(order_id):

    try:
        orders = get_dhan().get_orders()  # ✅ FIX

        if isinstance(orders, dict) and "error" in orders:
            return orders

        for order in orders:
            if order.get("orderId") == order_id:

                orders_collection.update_one(
                    {"order_id": order_id},
                    {
                        "$set": {
                            "status": order.get("orderStatus"),
                            "exchange_time": order.get("exchangeTime"),
                            "updated_at": current_ist_time()
                        }
                    }
                )

                logger.info(f"🔄 Synced order: {order_id}")
                return order

        return {"error": "Order not found in broker"}

    except Exception as e:
        logger.exception(f"❌ Sync failed for {order_id}")
        return {"error": str(e)}


# -----------------------------------------
# GET PORTFOLIO
# -----------------------------------------
def get_portfolio():

    try:
        positions = []
        holdings = []

        dhan = get_dhan()  # ✅ FIX

        if hasattr(dhan, "get_positions"):
            positions = dhan.get_positions()

        if hasattr(dhan, "get_holdings"):
            holdings = dhan.get_holdings()

        return {
            "positions": positions,
            "holdings": holdings
        }

    except Exception as e:
        logger.exception("❌ Portfolio fetch failed")
        return {"error": str(e)}


# -----------------------------------------
# EXIT ORDER
# -----------------------------------------
def exit_order(order_id):

    try:
        order = orders_collection.find_one({"order_id": order_id})

        if not order:
            logger.warning(f"⚠️ Order not found: {order_id}")
            return {"error": "Order not found in DB"}

        existing_exit = orders_collection.find_one({
            "parent_order_id": order_id,
            "type": "EXIT"
        })

        if existing_exit and existing_exit.get("status") in ["PENDING", "TRADED"]:
            logger.warning(f"⚠️ Exit already exists for: {order_id}")
            return {"error": "Exit already placed for this order"}

        dhan = get_dhan()  # ✅ FIX

        orders = dhan.get_orders()

        if isinstance(orders, dict) and "error" in orders:
            return orders

        live_order = None
        for o in orders:
            if o.get("orderId") == order_id:
                live_order = o
                break

        if not live_order:
            return {"error": "Order not found in broker"}

        status = live_order.get("orderStatus")

        if status not in ["TRADED", "PART_TRADED"]:
            return {"error": f"Cannot exit order with status: {status}"}

        req = order.get("request", {})

        if not isinstance(req, dict):
            return {"error": "Corrupted order data"}

        security_id = req.get("security_id")
        qty = req.get("qty")
        side = req.get("side")
        index = req.get("index", "NIFTY")

        if not security_id or not side:
            return {"error": "Invalid stored order data"}

        filled_qty = live_order.get("filledQty")
        if filled_qty:
            qty = filled_qty

        if not qty:
            qty = dhan.get_default_qty(index)

        exit_side = "SELL" if side == "BUY" else "BUY"

        res = dhan.place_order(
            security_id=security_id,
            index=index,
            side=exit_side,
            qty=qty
        )

        if isinstance(res, dict) and "error" in res:
            return res

        if not res or "orderId" not in res:
            return {"error": "Exit order failed", "response": res}

        save_order(
            res,
            {
                "type": "EXIT",
                "parent_order_id": order_id
            },
            request_payload={
                "security_id": security_id,
                "index": index,
                "side": exit_side,
                "qty": qty
            }
        )

        return res

    except Exception as e:
        logger.exception(f"❌ Exit failed for {order_id}")
        return {"error": str(e)}