from config import Config
from pymongo import MongoClient
from datetime import datetime, timezone

client = MongoClient(Config.MONGO_URI)
db = client[Config.DB_NAME]
orders_collection = db[Config.ORDER_COLLECTION]


# -----------------------------------
# 🕒 FORMAT TIME (READABLE)
# -----------------------------------
def format_time(dt):
    try:
        if isinstance(dt, datetime):
            # ensure UTC → local (optional)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            # convert to local time (India style if server UTC)
            local_dt = dt.astimezone()

            return local_dt.strftime("%d %b %Y, %I:%M %p")
        return dt
    except Exception:
        return dt


# -----------------------------------
# 📊 FETCH ORDERS
# -----------------------------------
def get_orders(limit=50):
    try:
        if orders_collection is None:
            return []

        data = list(
            orders_collection.find().sort("_id", -1).limit(limit)
        )

        for d in data:
            d["_id"] = str(d["_id"])

            # ✅ format main timestamp
            if "time" in d:
                d["time"] = format_time(d["time"])

            # ✅ optional: format nested response time if exists
            if "response" in d and isinstance(d["response"], dict):
                inner = d["response"].get("data", {})
                if isinstance(inner, dict):
                    # (future-safe if timestamp added later)
                    if "timestamp" in inner:
                        inner["timestamp"] = format_time(inner["timestamp"])

        return data

    except Exception as e:
        print(f"Fetch error: {e}")
        return []