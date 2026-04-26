from datetime import datetime
from .base_service import (
    get_dhan_client,
    save_log,
    resolve_product_type,
    logger,
    log_print
)
from utils.telegram_service import send_telegram_message   # ✅ NEW


def exit_position(order):
    try:
        dhan = get_dhan_client()

        security_id = order["security_id"]
        exchange_segment = order["exchange_segment"]
        quantity = order["qty"]
        product_type = order["product"]
        txn_type = order.get("txn", "BUY")

        # -----------------------------------
        # 🔁 REVERSE TRANSACTION
        # -----------------------------------
        txn = dhan.SELL if txn_type == "BUY" else dhan.BUY

        resolved_product = resolve_product_type(exchange_segment, product_type)
        product = getattr(dhan, resolved_product)

        logger.info(f"[EXIT] Reversing order {security_id}")
        log_print(f"[EXIT] Reverse → {security_id}")

        # -----------------------------------
        # 📦 PLACE EXIT ORDER
        # -----------------------------------
        response = dhan.place_order(
            security_id=str(security_id),
            exchange_segment=exchange_segment,
            transaction_type=txn,
            quantity=int(quantity),
            order_type=dhan.MARKET,
            product_type=product,
            price=0,
            after_market_order=False
        )

        # -----------------------------------
        # 🔑 SAFE EXTRACT
        # -----------------------------------
        order_id = None
        order_status = None

        try:
            data = response.get("data", {})
            order_id = data.get("orderId")
            order_status = data.get("orderStatus")
        except Exception:
            pass

        log_print(f"[EXIT] Response → {order_status}")

        # -----------------------------------
        # 💾 SAVE LOG
        # -----------------------------------
        save_log({
            "type": "EXIT",
            "reason": "REVERSAL",
            "linked_order": order.get("order_id"),
            "security_id": security_id,
            "qty": quantity,
            "product": resolved_product,
            "exchange_segment": exchange_segment,
            "txn": "SELL" if txn == dhan.SELL else "BUY",
            "status": order_status,
            "response": response,
            "time": datetime.utcnow()
        })

        # -----------------------------------
        # 📲 TELEGRAM SUCCESS
        # -----------------------------------
        try:
            send_telegram_message(
                f"🔻 <b>EXIT ORDER</b>\n"
                f"Reason: REVERSAL\n"
                f"Security: {security_id}\n"
                f"Qty: {quantity}\n"
                f"Txn: {'SELL' if txn == dhan.SELL else 'BUY'}\n"
                f"Status: {order_status}"
            )
        except Exception:
            pass

        logger.info(f"Exit success: {security_id} -> {order_status}")

        return response

    except Exception as e:
        logger.error(f"Exit failed: {e}")
        log_print(f"[EXIT ERROR] {e}")

        # -----------------------------------
        # 💾 SAVE FAILURE LOG
        # -----------------------------------
        try:
            save_log({
                "type": "EXIT_FAILED",
                "security_id": order.get("security_id"),
                "error": str(e),
                "time": datetime.utcnow()
            })
        except Exception:
            pass

        # -----------------------------------
        # 📲 TELEGRAM FAILURE
        # -----------------------------------
        try:
            send_telegram_message(
                f"❌ <b>EXIT FAILED</b>\n"
                f"Security: {order.get('security_id')}\n"
                f"Error: {str(e)}"
            )
        except Exception:
            pass

        raise Exception(f"Exit failed: {e}")