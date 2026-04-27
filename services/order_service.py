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
from utils.telegram_service import send_telegram_message


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
        logger.info("========== 🚀 PLACE ORDER START ==========")
        logger.info(f"[INPUT] security_id={security_id}, txn={transaction_type}, qty={quantity}, amo={amo}")

        dhan = get_dhan_client()
        logger.info("[STEP] Dhan client initialized")

        txn = dhan.BUY if transaction_type.upper() == "BUY" else dhan.SELL
        logger.info(f"[STEP] Transaction mapped → {txn}")

        # -----------------------------------
        # 🔧 PRODUCT RESOLVE
        # -----------------------------------
        resolved_product = resolve_product_type(exchange_segment, product_type)
        product = getattr(dhan, resolved_product)
        logger.info(f"[STEP] Product resolved → {resolved_product}")

        # -----------------------------------
        # 🔧 MARKET / LIMIT
        # -----------------------------------
        if price is not None:
            use_market = False

        order_type = dhan.MARKET if use_market else dhan.LIMIT
        logger.info(f"[STEP] Order type → {'MARKET' if use_market else 'LIMIT'} | price={price}")

        # -----------------------------------
        # 🕒 MARKET TIME CHECK
        # -----------------------------------
        now = datetime.now().time()
        market_start = time(9, 15)
        market_end = time(15, 30)

        is_market_hours = market_start <= now <= market_end
        logger.info(f"[STEP] Market hours → {is_market_hours} | current_time={now}")

        # -----------------------------------
        # 🧪 AMO MODE (STRICT - ONLY PARAM)
        # -----------------------------------
        after_market_order = bool(amo)
        logger.info(f"[STEP] AMO flag (strict) → {after_market_order}")

        if after_market_order:
            logger.info("[AMO MODE] Order will be placed as AMO")
            log_print("[ORDER] AMO MODE ENABLED")

        logger.info(f"[ORDER] Placing order {security_id} {transaction_type}")
        log_print(f"[ORDER] Request → {security_id} {transaction_type}")

        # -----------------------------------
        # 🚫 BLOCK NON-AMO OUTSIDE MARKET
        # -----------------------------------
        if not after_market_order and not is_market_hours:
            logger.warning("[BLOCKED] Outside market hours and AMO=False")

            try:
                save_log({
                    "type": "ORDER_BLOCKED",
                    "reason": "Outside market hours with AMO disabled",
                    "security_id": security_id,
                    "txn": transaction_type,
                    "qty": quantity,
                    "exchange_segment": exchange_segment,
                    "amo": after_market_order,
                    "time": datetime.utcnow()
                })
            except Exception as e:
                logger.error(f"[LOG ERROR] {e}")

            try:
                send_telegram_message(
                    f"🚫 <b>ORDER BLOCKED</b>\n"
                    f"Reason: Non-market hours\n"
                    f"AMO: {after_market_order}\n"
                    f"Security: {security_id}"
                )
            except Exception:
                pass

            return {
                "status": "blocked",
                "reason": "Order not placed due to non-market hours",
                "amo": after_market_order
            }

        # -----------------------------------
        # 🧠 PRE-CHECK: DIRECTION CONTROL
        # -----------------------------------
        try:
            if not after_market_order and meta:
                logger.info("[STEP] Running direction control check")

                last_order = get_last_order()

                if last_order:
                    last_option = last_order.get("meta", {}).get("option_type")
                    current_option = meta.get("option_type")

                    logger.info(f"[CHECK] last={last_option}, current={current_option}")

                    if last_option == current_option:
                        logger.info("[SKIP] Same direction trade ignored")

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

                        return {"status": "ignored", "reason": "Same direction trade"}

                    else:
                        logger.info("[REVERSAL] Opposite signal detected")

                        try:
                            send_telegram_message(
                                f"🔁 <b>REVERSAL</b>\n"
                                f"From: {last_option} → To: {current_option}"
                            )
                        except Exception:
                            pass

                        if last_order.get("status") in ["TRADED", "TRANSIT"]:
                            exit_position(last_order)

        except Exception as e:
            logger.error(f"[CHECK ERROR] {e}")

        # -----------------------------------
        # 📦 PLACE ORDER
        # -----------------------------------
        logger.info("[STEP] Sending order to Dhan API")

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

        # 🔥 DEBUG FULL RESPONSE
        print("[DEBUG] Full response →", response)

        # -----------------------------------
        # 🔑 SAFE EXTRACT
        # -----------------------------------
        order_id = None
        order_status = None

        try:
            data = response.get("data") if response else None

            if data:
                order_id = data.get("orderId")
                order_status = data.get("orderStatus")
            else:
                order_id = response.get("orderId") if response else None
                order_status = response.get("orderStatus") if response else None

        except Exception as e:
            logger.error(f"[EXTRACT ERROR] {e}")

        logger.info(f"[RESULT] order_id={order_id}, status={order_status}")

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
                "time": datetime.utcnow(),
                "meta": meta if meta else {}
            })
        except Exception as e:
            logger.error(f"[SAVE ERROR] {e}")

        # -----------------------------------
        # 📲 TELEGRAM
        # -----------------------------------
        try:
            send_telegram_message(
                f"✅ <b>ORDER PLACED</b>\n"
                f"Type: {meta.get('option_type') if meta else '-'}\n"
                f"Strike: {meta.get('adjusted_strike') if meta else '-'}\n"
                f"Qty: {quantity}\n"
                f"Status: {order_status}\n"
                f"ID: {order_id}"
            )
        except Exception:
            pass

        logger.info("========== ✅ PLACE ORDER END ==========")

        return response

    except Exception as e:
        logger.error(f"[FATAL] Order failed: {e}")

        try:
            save_log({
                "type": "ORDER_FAILED",
                "security_id": security_id,
                "error": str(e),
                "time": datetime.utcnow()
            })
        except Exception:
            pass

        try:
            send_telegram_message(
                f"❌ <b>ORDER FAILED</b>\n"
                f"Security: {security_id}\n"
                f"Error: {str(e)}"
            )
        except Exception:
            pass

        raise Exception(f"Order failed: {e}")