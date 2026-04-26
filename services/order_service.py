from datetime import datetime
from config import Config
from .base_service import (
    get_dhan_client,
    save_log,
    resolve_product_type,
    logger
)


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

        # ✅ Resolve product correctly
        resolved_product = resolve_product_type(exchange_segment, product_type)
        product = getattr(dhan, resolved_product)

        # ✅ LIMIT vs MARKET
        if price is not None:
            use_market = False

        order_type = dhan.MARKET if use_market else dhan.LIMIT

        # ✅ AMO logic
        is_testing = Config.TESTING_FLAG
        after_market_order = is_testing

        if is_testing:
            logger.info("[TEST MODE] AMO ORDER")

        logger.info(f"Placing order {security_id} {transaction_type}")

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
        # 🔑 EXTRACT ORDER ID SAFELY
        # -----------------------------------
        order_id = None
        try:
            order_id = response.get("data", {}).get("orderId")
        except Exception:
            pass

        # -----------------------------------
        # 💾 SAVE LOG (ENHANCED)
        # -----------------------------------
        save_log({
            "type": "ORDER",
            "order_id": order_id,                 # ✅ NEW
            "security_id": security_id,
            "txn": transaction_type,
            "qty": quantity,
            "product": resolved_product,          # ✅ NEW
            "order_type": "MARKET" if use_market else "LIMIT",  # ✅ NEW
            "exchange_segment": exchange_segment, # ✅ NEW (useful later)
            "amo": after_market_order,
            "response": response,
            "time": datetime.utcnow()
        })

        return response

    except Exception as e:
        logger.error(f"Order failed: {e}")
        raise Exception(f"Order failed: {e}")