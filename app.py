import logging
import sys
import os

from flask import Flask, request, jsonify, render_template

# SERVICES
from services.order_service import place_order
from services.cancel_service import cancel_order
from services.exit_service import exit_position
from services.order_fetch_service import get_orders

from config import Config
from utils.message_parser import parse_message
from config_file.index_map import INDEX_MAP
from utils.option_selector_by_strike import get_option_contract_by_strike, adjust_strike
import atexit
from utils.telegram_service import send_telegram_file

LOG_FILE = "app.log"



app = Flask(__name__)


# -----------------------------------
# 🪵 OPTIONAL DEBUG PRINT
# -----------------------------------
def log_print(msg):
    if Config.BASE_LOGS:
        print(msg)


# -----------------------------------
# LOGGER (NO FILE HANDLER - SAFE)
# -----------------------------------
logger = logging.getLogger("dhan_api")

if not logger.handlers:
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    logger.addHandler(console)

# -----------------------------------
# 🧾 EXIT LOG SENDER
# -----------------------------------
def send_logs_on_exit():
    try:
        logger.info("[EXIT] Sending logs to Telegram...")
        send_telegram_file(LOG_FILE)
    except Exception as e:
        logger.error(f"[EXIT ERROR] {e}")
        
# -----------------------------------
# DASHBOARD
# -----------------------------------
@app.route("/")
def dashboard():
    try:
        orders = get_orders()
        log_print(f"[DASHBOARD] Loaded {len(orders)} orders")
        return render_template("index.html", orders=orders)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return f"Error loading dashboard: {e}"


# -----------------------------------
# FIX FAVICON
# -----------------------------------
@app.route("/favicon.ico")
def favicon():
    return "", 204


# -----------------------------------
# HANDLE 404
# -----------------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "status": "error",
        "message": "Route not found"
    }), 404


# -----------------------------------
# GLOBAL ERROR HANDLER
# -----------------------------------
@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception("Unhandled Exception")
    return jsonify({
        "status": "error",
        "message": "Internal Server Error",
        "details": str(e)
    }), 500

@app.route("/webhook/tradingview/<int:security_id>/", methods=["POST"])
def tradingview_webhook(security_id):
    try:
        data = request.get_json()

        if not data or "message" not in data:
            return jsonify({"status": "error", "message": "message required"}), 400

        raw_message = data["message"]

        logger.info(f"[TV WEBHOOK] Raw → {raw_message}")

        # ✅ Step 1: Parse message
        parsed = parse_message(raw_message)

        if "error" in parsed:
            return jsonify({"status": "error", "message": parsed["error"]}), 400

        # -----------------------------------
        # 🎯 STRIKE SHIFT LOGIC (NEW)
        # -----------------------------------
        flag = parsed.get("flag", True)
        original_strike = parsed.get("strike")
        option_type = parsed.get("type")

        adjusted_strike = adjust_strike(
            base_strike=original_strike,
            option_type=option_type,
            shift_enabled=flag
        )

        logger.info(
            f"[TV WEBHOOK] Strike Adjusted → {original_strike} → {adjusted_strike} | Flag={flag}"
        )

        # -----------------------------------
        # 🎯 OPTION CONTRACT FETCH
        # -----------------------------------
        contract = get_option_contract_by_strike(
            security_id=security_id,
            option_type=option_type,
            target_strike=adjusted_strike
        )

        logger.info(f"[TV WEBHOOK] CONTRACT → {contract}")
        print("FINAL CONTRACT →", contract)

        # ❌ If contract failed → stop
        if not contract or "error" in contract:
            logger.error(f"[TV WEBHOOK] CONTRACT ERROR → {contract}")
            return jsonify({
                "status": "error",
                "message": "Contract fetch failed",
                "details": contract
            }), 400

        # -----------------------------------
        # ✅ Step 2: Map index
        # -----------------------------------
        if security_id not in INDEX_MAP:
            return jsonify({"status": "error", "message": "Invalid security_id"}), 400

        index_info = INDEX_MAP[security_id]

        logger.info(f"[TV WEBHOOK] Parsed → {parsed}")
        logger.info(f"[TV WEBHOOK] Index → {index_info['name']}")

        # -----------------------------------
        # ✅ Step 3: Build order payload
        # -----------------------------------
        order_payload = {
            "security_id": contract["security_id"],  # ✅ option contract
            "exchange_segment": index_info["exchange"],
            "transaction_type": "BUY" if "buy" in option_type.lower() else "SELL",
            "quantity": index_info["lot_size"],
            "product_type": "INTRA",
            "price": contract.get("price"),
            "use_market": True,
            # debug/meta
            "event": parsed.get("event"),
            "strike": adjusted_strike,   # 👈 important (adjusted)
            "option_type": "CE" if "CE" in option_type else "PE",
            "flag": flag
        }

        clean_payload = {
            "security_id": order_payload["security_id"],
            "exchange_segment": order_payload["exchange_segment"],
            "transaction_type": order_payload["transaction_type"],
            "quantity": order_payload["quantity"],
            "product_type": order_payload["product_type"],
            "price": order_payload["price"],
            "use_market": order_payload["use_market"]
        }



        logger.info(f"[TV WEBHOOK] Order Payload → {order_payload}")

        # -----------------------------------
        # 🚫 SAFE MODE (no real order yet)
        # -----------------------------------
        response = place_order(
            **clean_payload,
            amo=parsed.get("amo", False),
            meta={
                "event": parsed.get("event"),
                "original_strike": parsed.get("strike"),
                "adjusted_strike": adjusted_strike,
                "option_type": order_payload.get("option_type"),
                "flag": parsed.get("flag"),
                "amo": parsed.get("amo"),
                "contract_price": contract.get("price"),
                "expiry": contract.get("expiry")
            }
        ) 

        return jsonify({
            "status": "success",
            "parsed": parsed,
            "adjusted_strike": adjusted_strike,
            "contract": contract,
            "order_payload": order_payload,
            "order_response": response
        })

    except Exception as e:
        logger.exception("Webhook Error")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# -----------------------------------
# PLACE ORDER
# -----------------------------------
@app.route("/order", methods=["POST"])
def order():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400

        if "security_id" not in data:
            return jsonify({"status": "error", "message": "security_id required"}), 400

        logger.info(f"Order request: {data}")
        log_print(f"[API] ORDER → {data}")

        response = place_order(
            security_id=data["security_id"],
            exchange_segment=data.get("exchange_segment", "NSE_EQ"),
            transaction_type=data.get("transaction_type", "BUY"),
            quantity=data.get("quantity", 1),
            product_type=data.get("product_type", "INTRA"),
            price=data.get("price"),
            use_market=data.get("market", True)
        )

        return jsonify({
            "status": "success",
            "data": response
        })

    except Exception as e:
        logger.error(f"Order failed: {e}")
        log_print(f"[API ERROR] ORDER → {e}")

        return jsonify({"status": "error", "message": str(e)}), 500


# -----------------------------------
# CANCEL ORDER
# -----------------------------------
@app.route("/cancel", methods=["POST"])
def cancel():
    try:
        data = request.get_json()

        if not data or "order_id" not in data:
            return jsonify({"status": "error", "message": "order_id required"}), 400

        logger.info(f"Cancel request: {data}")
        log_print(f"[API] CANCEL → {data}")

        response = cancel_order(data["order_id"])

        return jsonify({
            "status": "success",
            "data": response
        })

    except Exception as e:
        logger.error(f"Cancel failed: {e}")
        log_print(f"[API ERROR] CANCEL → {e}")

        return jsonify({"status": "error", "message": str(e)}), 500


# -----------------------------------
# EXIT POSITION
# -----------------------------------
@app.route("/exit", methods=["POST"])
def exit_trade():
    try:
        data = request.get_json()

        if not data or "security_id" not in data:
            return jsonify({"status": "error", "message": "security_id required"}), 400

        logger.info(f"Exit request: {data}")
        log_print(f"[API] EXIT → {data}")

        response = exit_position(
            security_id=data["security_id"],
            exchange_segment=data.get("exchange_segment", "NSE_EQ"),
            quantity=data.get("quantity", 1),
            product_type=data.get("product_type", "INTRA")
        )

        return jsonify({
            "status": "success",
            "data": response
        })

    except Exception as e:
        logger.error(f"Exit failed: {e}")
        log_print(f"[API ERROR] EXIT → {e}")

        return jsonify({"status": "error", "message": str(e)}), 500

# -----------------------------------
# 📄 VIEW LOG FILE
# -----------------------------------
@app.route("/logs", methods=["GET"])
def get_logs():
    try:
        log_file_path = os.path.join(os.getcwd(), "app.log")

        if not os.path.exists(log_file_path):
            return jsonify({
                "status": "error",
                "message": "Log file not found"
            }), 404

        # Optional: limit size (last N lines)
        lines = request.args.get("lines", default=200, type=int)

        with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
            log_lines = f.readlines()

        # Get last N lines
        log_lines = log_lines[-lines:]

        return jsonify({
            "status": "success",
            "total_lines": len(log_lines),
            "logs": log_lines
        })

    except Exception as e:
        logger.exception("Error reading logs")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# -----------------------------------
# HEALTH CHECK
# -----------------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# -----------------------------------
# RUN
# -----------------------------------
if __name__ == "__main__":
    logger.info("[INFO] Starting API")
    app.run(host="0.0.0.0", port=5000, debug=True)