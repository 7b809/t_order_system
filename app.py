from flask import Flask, request, jsonify, render_template
from db import orders_collection
from order_logic import parse_message, generate_order_id, current_ist_time, should_ignore
from config import Config
from telegram_utils import send_telegram_alert
import traceback


app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        raw_message = data.get("message")
        if not raw_message:
            return jsonify({"error": "Missing message"}), 400

        metadata = parse_message(raw_message)
        trade_type = metadata.get("Type")

        if not trade_type:
            return jsonify({"error": "Type missing"}), 400

        last_order = orders_collection.find_one(
            {"status": "PLACED"},
            sort=[("created_at", -1)]
        )

        ignored = should_ignore(last_order, trade_type)
        order_id = generate_order_id("IG" if ignored else "ORD")

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

        orders_collection.insert_one(order_doc)

        # 🔔 Telegram notify only for PLACED
        if order_doc["status"] == "PLACED":
            try:
                send_telegram_alert(order_doc)
            except Exception as tg_err:
                print("Telegram error:", tg_err)

        return jsonify({"status": "success", "data": order_doc}), 200

    except Exception as e:
        print("ERROR:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    
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
        return jsonify({"error": str(e)}), 500
    
@app.route("/")
def index():
    return render_template("index.html")    

if __name__=='__main__':
    app.run(port=Config.FLASK_PORT, debug=True)
