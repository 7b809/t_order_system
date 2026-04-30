from order_logic import parse_message, generate_order_id, current_ist_time, should_ignore
from db import orders_collection
from telegram_utils import send_telegram_alert
from logger import get_logger

logger = get_logger("order_processor")


def process_order(raw_message):
    order_id = generate_order_id("ORD")

    metadata = {}
    failed_step = "init"

    try:
        logger.info(f"Received alert: {raw_message}")

        # STEP 1
        failed_step = "parse_message"
        metadata = parse_message(raw_message)

        trade_type = metadata.get("Type")
        if not trade_type:
            raise ValueError("Missing Type in alert")

        # STEP 2
        failed_step = "fetch_last_order"
        last_order = orders_collection.find_one(
            {"status": "PLACED"},
            sort=[("created_at", -1)]
        )

        # STEP 3
        failed_step = "should_ignore"
        ignored = should_ignore(last_order, trade_type)

        order_id = generate_order_id("IG" if ignored else "ORD")

        # STEP 4
        failed_step = "prepare_doc"
        order_doc = {
            "order_id": order_id,
            "status": "IGNORED" if ignored else "PLACED",
            "trade_type": trade_type,
            "strike": metadata.get("Strike"),
            "strike_price": metadata.get("StrikeLivePrice"),
            "symbol": metadata.get("Symbol"),
            "alert_price": metadata.get("Price"),
            "created_at": current_ist_time(),
            "metadata": metadata
        }

        # STEP 5
        failed_step = "db_insert"
        orders_collection.insert_one(order_doc)

        logger.info(f"Order stored: {order_id} | Status: {order_doc['status']}")

        # ✅ SEND TELEGRAM FOR ALL CASES
        try:
            send_telegram_alert({
                "order_id": order_doc["order_id"],
                "status": order_doc["status"],  # PLACED / IGNORED
                "trade_type": order_doc["trade_type"],
                "symbol": order_doc["symbol"],
                "strike": order_doc["strike"],
                "strike_price": order_doc["strike_price"],
                "alert_price": order_doc["alert_price"],
                "created_at": order_doc["created_at"]
            })

            logger.info(f"Telegram sent for {order_id} ({order_doc['status']})")

        except Exception as tg_err:
            logger.error(f"Telegram error: {tg_err}")

    except Exception as e:
        logger.error(f"Error at step [{failed_step}] → {str(e)}", exc_info=True)

        failed_order = {
            "order_id": generate_order_id("FAIL"),
            "status": "FAILED",
            "error_reason": str(e),
            "error_type": type(e).__name__,
            "failed_step": failed_step,
            "raw_message": raw_message,
            "metadata": metadata,
            "created_at": current_ist_time()
        }

        try:
            orders_collection.insert_one(failed_order)
            logger.warning(f"FAILED order stored: {failed_order['order_id']}")

            # 🔴 TELEGRAM FOR FAILED
            try:
                send_telegram_alert({
                    "order_id": failed_order["order_id"],
                    "status": "FAILED",
                    "trade_type": metadata.get("Type", "NA"),
                    "symbol": metadata.get("Symbol", "NA"),
                    "strike": metadata.get("Strike", "NA"),
                    "strike_price": "NA",
                    "alert_price": metadata.get("Price", "NA"),
                    "created_at": failed_order["created_at"],
                    "error": failed_order["error_reason"],
                    "failed_step": failed_order["failed_step"]
                })

                logger.info(f"Telegram sent for FAILED {failed_order['order_id']}")

            except Exception as tg_err:
                logger.error(f"Telegram FAIL alert error: {tg_err}")

        except Exception as db_err:
            logger.critical(f"DB ERROR while saving failed order: {db_err}", exc_info=True)