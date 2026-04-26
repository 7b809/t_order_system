import logging
import sys

from flask import Flask, request, jsonify, render_template

# SERVICES
from services.order_service import place_order
from services.cancel_service import cancel_order
from services.exit_service import exit_position
from services.order_fetch_service import get_orders

app = Flask(__name__)

# Fix Windows encoding
sys.stdout.reconfigure(encoding='utf-8')


# -----------------------------------
# LOGGER (SAFE INIT - NO DUPLICATES)
# -----------------------------------
logger = logging.getLogger("dhan_api")

if not logger.handlers:
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file = logging.FileHandler("dhan_api.log")
    file.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file)


# -----------------------------------
# DASHBOARD
# -----------------------------------
@app.route("/")
def dashboard():
    try:
        orders = get_orders()
        return render_template("index.html", orders=orders)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return f"Error loading dashboard: {e}"


# -----------------------------------
# FIX FAVICON (PREVENT 404 ERROR)
# -----------------------------------
@app.route("/favicon.ico")
def favicon():
    return "", 204


# -----------------------------------
# HANDLE 404 SEPARATELY
# -----------------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "status": "error",
        "message": "Route not found"
    }), 404


# -----------------------------------
# GLOBAL ERROR HANDLER (ONLY REAL ERRORS)
# -----------------------------------
@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception("Unhandled Exception")
    return jsonify({
        "status": "error",
        "message": "Internal Server Error",
        "details": str(e)
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

        response = cancel_order(data["order_id"])

        return jsonify({
            "status": "success",
            "data": response
        })

    except Exception as e:
        logger.error(f"Cancel failed: {e}")
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
        return jsonify({"status": "error", "message": str(e)}), 500


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
    app.run(debug=True, port=5000)