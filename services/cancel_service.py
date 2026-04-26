from datetime import datetime
from .base_service import get_dhan_client, save_log, logger


def cancel_order(order_id):
    try:
        dhan = get_dhan_client()

        logger.info(f"Cancel request for order_id: {order_id}")

        # -----------------------------------
        # ❌ CANCEL ORDER
        # -----------------------------------
        response = dhan.cancel_order(order_id)

        # -----------------------------------
        # 🔑 EXTRACT STATUS SAFELY
        # -----------------------------------
        order_status = None
        try:
            order_status = response.get("data", {}).get("orderStatus")
        except Exception:
            pass

        # -----------------------------------
        # 💾 SAVE LOG (ENHANCED)
        # -----------------------------------
        save_log({
            "type": "CANCEL",
            "order_id": order_id,
            "status": order_status,          # ✅ NEW (useful for dashboard)
            "action": "CANCELLED",           # ✅ NEW (explicit action)
            "response": response,
            "time": datetime.utcnow()
        })

        logger.info(f"Cancel success: {order_id} → {order_status}")

        return response

    except Exception as e:
        logger.error(f"Cancel failed: {e}")

        # Optional: log failure also
        save_log({
            "type": "CANCEL_FAILED",
            "order_id": order_id,
            "error": str(e),
            "time": datetime.utcnow()
        })

        raise Exception(f"Cancel failed: {e}")