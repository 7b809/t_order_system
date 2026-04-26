from datetime import datetime, timezone
from config import Config


# -----------------------------------
# 🪵 OPTIONAL DEBUG PRINT
# -----------------------------------
def log_print(msg):
    if Config.BASE_LOGS:
        print(msg)


# -----------------------------------
# 🕒 FORMAT TIME (READABLE)
# -----------------------------------
def format_time(dt):
    try:
        if isinstance(dt, datetime):
            # ensure UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            # convert to local time
            local_dt = dt.astimezone()

            return local_dt.strftime("%d %b %Y, %I:%M %p")

        return dt

    except Exception:
        return dt


# -----------------------------------
# 📊 FETCH ORDERS (CLEAN + SAFE)
# -----------------------------------
def get_orders(limit=50):
    try:
        collection = Config.get_order_collection()

        if collection is None:
            return []

        data = list(
            collection.find().sort("_id", -1).limit(limit)
        )

        formatted = []

        for d in data:
            try:
                d["_id"] = str(d.get("_id"))

                # -----------------------------------
                # 🕒 FORMAT TIME
                # -----------------------------------
                if "time" in d:
                    d["time"] = format_time(d["time"])

                # -----------------------------------
                # 🔑 SAFE STATUS EXTRACTION
                # -----------------------------------
                if "status" not in d:
                    try:
                        d["status"] = d.get("response", {}).get("data", {}).get("orderStatus")
                    except Exception:
                        d["status"] = None

                # -----------------------------------
                # 🔑 SAFE ORDER ID EXTRACTION
                # -----------------------------------
                if "order_id" not in d:
                    try:
                        d["order_id"] = d.get("response", {}).get("data", {}).get("orderId")
                    except Exception:
                        d["order_id"] = None

                formatted.append(d)

            except Exception as inner_err:
                log_print(f"[FORMAT ERROR] {inner_err}")

        log_print(f"[FETCH] Orders fetched: {len(formatted)}")

        return formatted

    except Exception as e:
        log_print(f"[FETCH ERROR] {e}")
        return []