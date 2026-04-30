from flask import Flask, request, jsonify, render_template
from config import Config
import threading
from utils import process_order
from db import orders_collection
from logger import get_logger
import os

logger = get_logger("flask_app")

app = Flask(__name__)

LOG_FILE = "logs/app.log"


# --------------------------------------------------
# 🚀 WEBHOOK
# --------------------------------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(silent=True)

        if not data or "message" not in data:
            logger.warning("Invalid payload received")
            return jsonify({"error": "Invalid payload"}), 400

        raw_message = data["message"]

        logger.info(f"Webhook received: {raw_message}")

        threading.Thread(
            target=process_order,
            args=(raw_message,),
            daemon=True
        ).start()

        return jsonify({"status": "accepted"}), 200

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------
# 📊 ORDERS API
# --------------------------------------------------
@app.route("/api/orders", methods=["GET"])
def get_orders():
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))

        skip = (page - 1) * limit

        cursor = orders_collection.find().sort("created_at", -1).skip(skip).limit(limit)

        orders = []
        for o in cursor:
            o["_id"] = str(o["_id"])
            orders.append(o)

        total = orders_collection.count_documents({})

        return jsonify({
            "page": page,
            "limit": limit,
            "total": total,
            "data": orders
        })

    except Exception as e:
        logger.error(f"/api/orders error: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------
# 📄 LOGS API
# --------------------------------------------------
@app.route("/logs", methods=["GET"])
def get_logs():
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 50))

        if not os.path.exists(LOG_FILE):
            return jsonify({"error": "Log file not found"}), 404

        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        lines.reverse()

        start = (page - 1) * limit
        end = start + limit

        return jsonify({
            "page": page,
            "limit": limit,
            "total": len(lines),
            "data": lines[start:end]
        })

    except Exception as e:
        logger.error(f"/logs error: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------
# 🖥 DASHBOARD
# --------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# --------------------------------------------------
# RUN
# --------------------------------------------------
if __name__ == "__main__":
    app.run(port=Config.FLASK_PORT, debug=True)