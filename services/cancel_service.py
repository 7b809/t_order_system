from datetime import datetime
from .base_service import get_dhan_client, save_log, logger, log_print


def cancel_order(order_id):
    try:
        dhan = get_dhan_client()

        logger.info(f"Cancel request for order_id: {order_id}")
        log_print(f"[CANCEL] Request → {order_id}")

        # -----------------------------------
        # ❌ CANCEL ORDER
        # -----------------------------------
        response = dhan.cancel_order(order_id)

        # -----------------------------------
        # 🔑 SAFE EXTRACT
        # -----------------------------------
        order_status = None
        order_id_resp = None

        try:
            data = response.get("data", {})
            order_status = data.get("orderStatus")
            order_id_resp = data.get("orderId")
        except Exception:
            pass

        log_print(f"[CANCEL] Response → {order_status}")

        # -----------------------------------
        # 💾 SAVE LOG
        # -----------------------------------
        save_log({
            "type": "CANCEL",
            "order_id": order_id_resp or order_id,
            "status": order_status,
            "action": "CANCELLED",
            "response": response,
            "time": datetime.utcnow()
        })

        logger.info(f"Cancel success: {order_id} -> {order_status}")

        return response

    except Exception as e:
        logger.error(f"Cancel failed: {e}")
        log_print(f"[CANCEL ERROR] {e}")

        # -----------------------------------
        # 💾 SAVE FAILURE LOG
        # -----------------------------------
        try:
            save_log({
                "type": "CANCEL_FAILED",
                "order_id": order_id,
                "error": str(e),
                "time": datetime.utcnow()
            })
        except Exception:
            pass  # never break flow due to logging

        raise Exception(f"Cancel failed: {e}")