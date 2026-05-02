from .dhan_http import DhanHTTP
import uuid


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
    # PLACE ORDER (SMART)
    # --------------------------------
    def place_order(
        self,
        security_id,
        index="NIFTY",
        side="BUY",
        qty=None,
        price=0
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
                "price": float(price)  # ensure float
            }

            # ---------- API call ----------
            res = self.api.place_order(payload)

            # ---------- validate response ----------
            if not isinstance(res, dict):
                return {"error": "Invalid response from broker", "raw": res}

            if "orderId" not in res:
                return {"error": "Order failed", "response": res}

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