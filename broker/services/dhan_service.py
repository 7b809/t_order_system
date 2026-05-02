from .dhan_http import DhanHTTP
import uuid
import json
from django.conf import settings

DHAN_ERROR_MAP = settings.DHAN_ERROR_MAP


class DhanService:

    def __init__(self):
        self.api = DhanHTTP()

    # --------------------------------
    # DEFAULT LOT SIZE HANDLER
    # --------------------------------
    def get_default_qty(self, index):
        index = index.upper()

        if index == "NIFTY":
            return 65
        elif index == "SENSEX":
            return 20
        else:
            raise ValueError(f"Unsupported index: {index}")

    # --------------------------------
    # DEFAULT SEGMENT
    # --------------------------------
    def get_exchange_segment(self, index):
        index = index.upper()

        if index == "NIFTY":
            return "NSE_FNO"
        elif index == "SENSEX":
            return "BSE_FNO"
        else:
            raise ValueError(f"Unsupported index: {index}")

    # --------------------------------
    # VALIDATION
    # --------------------------------
    def _validate_inputs(self, security_id, side, qty):
        if not security_id:
            return {"error": "security_id is required"}

        if side not in ["BUY", "SELL"]:
            return {"error": "Invalid side. Must be BUY or SELL"}

        if qty is not None and qty <= 0:
            return {"error": "qty must be greater than 0"}

        return None

    # --------------------------------
    # 🔥 BROKER ERROR PARSER
    # --------------------------------
    def _parse_broker_error(self, res):
        try:
            if isinstance(res, dict) and res.get("error") == "HTTP_ERROR":
                msg = res.get("message")

                if isinstance(msg, str):
                    try:
                        msg_json = json.loads(msg)

                        code = msg_json.get("errorCode")
                        message = msg_json.get("errorMessage")

                        return {
                            "error": "BROKER_ERROR",
                            "code": code,
                            "message": message,
                            "explanation": DHAN_ERROR_MAP.get(code, "Unknown error"),
                            "raw": res
                        }
                    except Exception:
                        return res

            if isinstance(res, dict) and "response" in res:
                inner = res.get("response")

                if isinstance(inner, dict) and "message" in inner:
                    try:
                        msg_json = json.loads(inner["message"])
                    except Exception:
                        return res

                    code = msg_json.get("errorCode")
                    message = msg_json.get("errorMessage")

                    return {
                        "error": "BROKER_ERROR",
                        "code": code,
                        "message": message,
                        "explanation": DHAN_ERROR_MAP.get(code, "Unknown error"),
                        "raw": res
                    }

            if isinstance(res, dict) and "errorCode" in res:
                return {
                    "error": "BROKER_ERROR",
                    "code": res.get("errorCode"),
                    "message": res.get("errorMessage"),
                    "explanation": DHAN_ERROR_MAP.get(res.get("errorCode"))
                }

            return res

        except Exception as e:
            return {"error": "ERROR_PARSING_FAILED", "details": str(e)}

    # --------------------------------
    # PLACE ORDER (SMART)
    # --------------------------------
    def place_order(
        self,
        security_id,
        index="NIFTY",
        side="BUY",
        qty=None,
        price=0,
        amo=False,
        amo_time=""
    ):
        try:
            # ---------- validation ----------
            error = self._validate_inputs(security_id, side, qty)
            if error:
                return error

            # ---------- qty resolution ----------
            if qty is None:
                final_qty = self.get_default_qty(index)
            else:
                final_qty = qty

            # ---------- segment ----------
            exchange_segment = self.get_exchange_segment(index)

            # ---------- payload ----------
            payload = {
                "dhanClientId": self.api.client_id,
                "correlationId": str(uuid.uuid4())[:20],
                "transactionType": side,
                "exchangeSegment": exchange_segment,
                "productType": "INTRADAY",
                "orderType": "MARKET",
                "validity": "DAY",
                "securityId": security_id,
                "quantity": int(final_qty),
                "afterMarketOrder": bool(amo),
                "amoTime": amo_time if amo else ""
            }

            # ✅ ONLY add price if valid (>0)
            if price and price > 0:
                payload["price"] = float(price)

            # ---------- DEBUG (optional but useful) ----------
            print("FINAL PAYLOAD →", payload)

            # ---------- API call ----------
            res = self.api.place_order(payload)

            # ---------- validate response ----------
            if not isinstance(res, dict):
                return {"error": "Invalid response from broker", "raw": res}

            if "orderId" not in res:
                parsed_error = self._parse_broker_error(res)

                if isinstance(parsed_error, dict):
                    code = parsed_error.get("code")

                    if code == "DH-906":
                        return {
                            "error": "ORDER_REJECTED",
                            "reason": parsed_error.get("message"),
                            "hint": "Market closed or invalid order",
                            "details": parsed_error
                        }

                    elif code == "DH-904":
                        return {
                            "error": "RATE_LIMIT",
                            "hint": "Too many requests",
                            "details": parsed_error
                        }

                    elif code == "DH-901":
                        return {
                            "error": "AUTH_ERROR",
                            "hint": "Token expired or invalid",
                            "details": parsed_error
                        }

                return {
                    "error": "ORDER_FAILED",
                    "details": parsed_error
                }

            return res

        except Exception as e:
            return {"error": str(e)}

    # --------------------------------
    # CANCEL ORDER
    # --------------------------------
    def cancel_order(self, order_id):
        try:
            if not order_id:
                return {"error": "order_id required"}

            res = self.api.cancel_order(order_id)

            if not isinstance(res, dict):
                return {"error": "Invalid response from broker"}

            return res

        except Exception as e:
            return {"error": str(e)}

    # --------------------------------
    # GET ORDERS
    # --------------------------------
    def get_orders(self):
        try:
            res = self.api.get_orders()

            if not isinstance(res, (list, dict)):
                return {"error": "Invalid response from broker"}

            return res

        except Exception as e:
            return {"error": str(e)}