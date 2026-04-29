from datetime import datetime, time
import pytz
import traceback

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
from services.paper_order_service import place_paper_order


# -----------------------------------
# 🧠 HELPER: EXCEPTION DETAILS
# -----------------------------------
def get_exception_info(e):
    tb = traceback.extract_tb(e.__traceback__)
    last = tb[-1] if tb else None

    return {
        "message": str(e),
        "type": type(e).__name__,
        "file": last.filename if last else None,
        "line": last.lineno if last else None,
        "function": last.name if last else None,
        "trace": traceback.format_exc()
    }


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

        # -----------------------------------
        # 🧪 PAPER TRADING (FULL OVERRIDE)
        # -----------------------------------
        if getattr(Config, "PAPER_TRADING", False):
            logger.info("[PAPER MODE - FORCE] Skipping all logic")

            response = place_paper_order(
                security_id=security_id,
                exchange_segment=exchange_segment,
                transaction_type=transaction_type,
                quantity=quantity,
                product_type=product_type,
                price=price,
                order_type="MARKET" if use_market else "LIMIT",
                amo=amo,
                meta=meta
            )

            data = response.get("data", {})
            order_id = data.get("orderId")
            order_status = data.get("orderStatus")

            logger.info(f"[PAPER RESULT] order_id={order_id}, status={order_status}")

            # ✅ SAME DB
            save_log({
                "type": "ORDER",
                "order_id": order_id,
                "security_id": security_id,
                "txn": transaction_type,
                "qty": quantity,
                "status": order_status,
                "amo": amo,
                "response": response,
                "time": datetime.utcnow(),
                "meta": meta or {},
                "mode": "paper"
            })

            try:
                send_telegram_message(
                    f"🧪 PAPER ORDER\nID:{order_id}\nStatus:{order_status}"
                )
            except Exception:
                pass

            return response

        # -----------------------------------
        # 🚀 REAL ORDER FLOW (UNCHANGED)
        # -----------------------------------

        dhan = get_dhan_client()
        logger.info("[STEP] Dhan client initialized")

        txn = dhan.BUY if transaction_type.upper() == "BUY" else dhan.SELL
        logger.info(f"[STEP] Transaction mapped → {txn}")

        resolved_product = resolve_product_type(exchange_segment, product_type)
        product = getattr(dhan, resolved_product)
        logger.info(f"[STEP] Product resolved → {resolved_product}")

        if price is not None:
            use_market = False

        order_type = dhan.MARKET if use_market else dhan.LIMIT
        logger.info(f"[STEP] Order type → {'MARKET' if use_market else 'LIMIT'} | price={price}")

        # IST TIME
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist).time()

        market_start = time(9, 15)
        market_end = time(15, 30)

        is_market_hours = market_start <= now <= market_end
        logger.info(f"[STEP] Market hours → {is_market_hours}")

        after_market_order = bool(amo)

        if not is_market_hours and not after_market_order:
            logger.warning("[AUTO AMO] Switching to AMO")
            after_market_order = True

        # PRE-CHECK
        try:
            if not after_market_order and meta:
                last_order = get_last_order()

                if last_order:
                    last_option = last_order.get("meta", {}).get("option_type")
                    current_option = meta.get("option_type")

                    if last_option == current_option:
                        save_log({
                            "type": "ORDER_IGNORED",
                            "security_id": security_id,
                            "meta": meta,
                            "time": datetime.utcnow()
                        })
                        return {"status": "ignored"}

                    else:
                        if last_order.get("status") in ["TRADED", "TRANSIT"]:
                            exit_position(last_order)

        except Exception as e:
            logger.error(f"[CHECK ERROR] {e}")

        # REAL ORDER CALL
        try:
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

        except Exception as api_err:
            error_info = get_exception_info(api_err)

            save_log({
                "type": "ORDER_API_FAILED",
                "security_id": security_id,
                "error": error_info,
                "time": datetime.utcnow(),
                "meta": meta or {},
                "mode": "real"
            })

            return {"status": "error", "reason": str(api_err)}

        # RESPONSE HANDLING
        data = response.get("data", {})

        error_msg = (
            data.get("errorMessage")
            or data.get("error_message")
            or response.get("remarks", {}).get("message")
        )

        if error_msg:
            save_log({
                "type": "ORDER_REJECTED",
                "security_id": security_id,
                "error": error_msg,
                "response": response,
                "time": datetime.utcnow(),
                "meta": meta or {}
            })

            return {"status": "rejected", "reason": error_msg}

        order_id = data.get("orderId") or response.get("orderId")
        order_status = data.get("orderStatus") or response.get("orderStatus")

        save_log({
            "type": "ORDER",
            "order_id": order_id,
            "security_id": security_id,
            "txn": transaction_type,
            "qty": quantity,
            "status": order_status,
            "amo": after_market_order,
            "response": response,
            "time": datetime.utcnow(),
            "meta": meta or {},
            "mode": "real"
        })

        try:
            send_telegram_message(
                f"✅ ORDER\nID:{order_id}\nStatus:{order_status}"
            )
        except Exception:
            pass

        return response

    except Exception as e:
        error_info = get_exception_info(e)

        save_log({
            "type": "ORDER_FAILED",
            "security_id": security_id,
            "error": error_info,
            "time": datetime.utcnow(),
            "meta": meta or {}
        })

        try:
            send_telegram_message(f"❌ FATAL ERROR\n{error_info}")
        except Exception:
            pass

        raise