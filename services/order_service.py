from datetime import datetime, time
from config import Config
from .base_service import (
    get_dhan_client,
    save_log,
    resolve_product_type,
    logger,
    log_print,
    get_last_order
)
from .exit_service import exit_position
from utils.telegram_service import send_telegram_message   # ✅ NEW


def place_order(
    security_id,
    exchange_segment="NSE_FNO",
    transaction_type="BUY",
    quantity=1,
    product_type="MARGIN",
    price=None,
    use_market=True,
    amo=False,
    meta=None
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
        # 🧪 AMO MODE
        # -----------------------------------
        after_market_order = (
            amo
            or not is_market_hours
            or Config.TESTING_FLAG
        )

        if after_market_order:
            logger.info("[AMO MODE] Order will be placed as AMO")
            log_print("[ORDER] AMO MODE ENABLED")

        logger.info(f"Placing order {security_id} {transaction_type}")
        log_print(f"[ORDER] Request → {security_id} {transaction_type}")

        # -----------------------------------
        # 🧠 PRE-CHECK: DIRECTION CONTROL
        # -----------------------------------
        try:
            if not after_market_order and meta:
                last_order = get_last_order()

                if last_order:
                    last_option = last_order.get("meta", {}).get("option_type")
                    current_option = meta.get("option_type")

                    # ❌ SAME → IGNORE
                    if last_option == current_option:
                        logger.info("[SKIP] Same direction trade ignored")
                        log_print("[ORDER] Skipped duplicate direction")

                        save_log({
                            "type": "ORDER_IGNORED",
                            "reason": "Same direction trade",
                            "security_id": security_id,
                            "txn": transaction_type,
                            "qty": quantity,
                            "exchange_segment": exchange_segment,
                            "meta": meta,
                            "time": datetime.utcnow()
                        })

                        # ✅ TELEGRAM IGNORED
                        try:
                            send_telegram_message(
                                f"❌ <b>ORDER IGNORED</b>\n"
                                f"Reason: Same Direction\n"
                                f"Type: {current_option}\n"
                                f"Strike: {meta.get('adjusted_strike')}"
                            )
                        except Exception:
                            pass

                        return {
                            "status": "ignored",
                            "reason": "Same direction trade"
                        }

                    # 🔁 OPPOSITE → EXIT FIRST
                    else:
                        logger.info("[REVERSAL] Opposite signal detected")
                        log_print("[ORDER] Reversal triggered")

                        # ✅ TELEGRAM REVERSAL
                        try:
                            send_telegram_message(
                                f"🔁 <b>REVERSAL</b>\n"
                                f"From: {last_option} → To: {current_option}"
                            )
                        except Exception:
                            pass

                        if last_order.get("status") in ["TRADED", "TRANSIT"]:
                            exit_position(last_order)
                        else:
                            logger.info("[REVERSAL] Skipped exit due to inactive status")

        except Exception as e:
            logger.error(f"[CHECK ERROR] {e}")

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
        # 💾 SAVE LOG (WITH META)
        # -----------------------------------
        try:
            log_data = {
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
            }

            if meta:
                log_data["meta"] = meta

            save_log(log_data)

        except Exception as log_err:
            logger.error(f"Save log failed: {log_err}")
            log_print(f"[ORDER LOG ERROR] {log_err}")

        # -----------------------------------
        # 📲 TELEGRAM SUCCESS
        # -----------------------------------
        try:
            send_telegram_message(
                f"✅ <b>ORDER PLACED</b>\n"
                f"Type: {meta.get('option_type') if meta else '-'}\n"
                f"Strike: {meta.get('adjusted_strike') if meta else '-'}\n"
                f"Qty: {quantity}\n"
                f"Status: {order_status}"
            )
        except Exception:
            pass

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

        # -----------------------------------
        # 📲 TELEGRAM FAILURE
        # -----------------------------------
        try:
            send_telegram_message(
                f"❌ <b>ORDER FAILED</b>\n"
                f"Security: {security_id}\n"
                f"Error: {str(e)}"
            )
        except Exception:
            pass

        raise Exception(f"Order failed: {e}")