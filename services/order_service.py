from datetime import datetime, time
from config import Config
from .base_service import (
    get_dhan_client,
    save_log,
    resolve_product_type,
    logger,
    log_print
)


def place_order(
    security_id,
    exchange_segment="NSE_FNO",
    transaction_type="BUY",
    quantity=1,
    product_type="MARGIN",
    price=None,
    use_market=True,
    amo=False   # 👈 NEW (from webhook)
):
    try:
        dhan = get_dhan_client()

        txn = dhan.BUY if transaction_type.upper() == "BUY" else dhan.SELL

        # -----------------------------------
        # 🔧 PRODUCT RESOLVE
        # -----------------------------------
        resolved_product = resolve_product_type(exchange_segment, product_type)
        product = getattr(dhan, resolved_product)

        # -----------------------------------
        # 🔧 MARKET / LIMIT
        # -----------------------------------
        if price is not None:
            use_market = False

        order_type = dhan.MARKET if use_market else dhan.LIMIT

        # -----------------------------------
        # 🕒 MARKET TIME CHECK
        # -----------------------------------
        now = datetime.now().time()

        market_start = time(9, 15)
        market_end = time(15, 30)

        is_market_hours = market_start <= now <= market_end

        # -----------------------------------
        # 🧪 AMO MODE (UPDATED LOGIC)
        # -----------------------------------
        # Priority:
        # 1. Webhook flag (amo=True)
        # 2. Outside market hours
        # 3. Testing mode fallback

        after_market_order = (
            amo                     # 👈 from webhook
            or not is_market_hours  # 👈 time-based
            or Config.TESTING_FLAG  # 👈 fallback safety
        )

        if after_market_order:
            logger.info("[AMO MODE] Order will be placed as AMO")
            log_print("[ORDER] AMO MODE ENABLED")

        logger.info(f"Placing order {security_id} {transaction_type}")
        log_print(f"[ORDER] Request → {security_id} {transaction_type}")

        # -----------------------------------
        # 📦 PLACE ORDER
        # -----------------------------------
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

        log_print(f"[ORDER] Response → {order_status}")

        # -----------------------------------
        # 💾 SAVE LOG
        # -----------------------------------
        try:
            save_log({
                "type": "ORDER",
                "order_id": order_id,
                "security_id": security_id,
                "txn": transaction_type,
                "qty": quantity,
                "product": resolved_product,
                "order_type": "MARKET" if use_market else "LIMIT",
                "exchange_segment": exchange_segment,
                "status": order_status,
                "amo": after_market_order,
                "response": response,
                "time": datetime.utcnow()
            })
        except Exception as log_err:
            logger.error(f"Save log failed: {log_err}")
            log_print(f"[ORDER LOG ERROR] {log_err}")

        logger.info(f"Order success: {order_id} -> {order_status}")

        return response

    except Exception as e:
        logger.error(f"Order failed: {e}")
        log_print(f"[ORDER ERROR] {e}")

        try:
            save_log({
                "type": "ORDER_FAILED",
                "security_id": security_id,
                "error": str(e),
                "time": datetime.utcnow()
            })
        except Exception:
            pass

        raise Exception(f"Order failed: {e}")