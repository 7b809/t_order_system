from datetime import datetime
from .base_service import (
    get_dhan_client,
    save_log,
    resolve_product_type,
    logger,
    log_print
)


def exit_position(
    security_id,
    exchange_segment="NSE_EQ",
    quantity=1,
    product_type="INTRA"
):
    try:
        dhan = get_dhan_client()

        # EXIT = SELL (current logic)
        txn = dhan.SELL

        resolved_product = resolve_product_type(exchange_segment, product_type)
        product = getattr(dhan, resolved_product)

        logger.info(f"Exit request for {security_id}")
        log_print(f"[EXIT] Request → {security_id}")

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
            price=0
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
            "order_id": order_id,
            "security_id": security_id,
            "qty": quantity,
            "product": resolved_product,
            "exchange_segment": exchange_segment,
            "txn": "SELL",
            "status": order_status,
            "response": response,
            "time": datetime.utcnow()
        })

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
                "security_id": security_id,
                "error": str(e),
                "time": datetime.utcnow()
            })
        except Exception:
            pass

        raise Exception(f"Exit failed: {e}")