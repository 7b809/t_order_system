import requests
import time
from core.auth.dhan_token import load_valid_dhan_credentials


class DhanHTTP:

    BASE_URL = "https://api.dhan.co/v2"
    TIMEOUT = 5
    RETRIES = 2

    def __init__(self):
        creds = load_valid_dhan_credentials()

        # ✅ FIX: don't crash if token missing/expired
        if not creds:
            self.client_id = None
            self.access_token = None
            self.headers = {}
            return

        self.client_id = creds["client_id"]
        self.access_token = creds["access_token"]

        self.headers = {
            "Content-Type": "application/json",
            "access-token": self.access_token
        }

    # --------------------------------
    # INTERNAL: SAFE REQUEST HANDLER
    # --------------------------------
    def _request(self, method, url, **kwargs):
        last_error = None

        # ✅ FIX: block request if no valid token
        if not self.access_token:
            return {
                "error": "NO_VALID_TOKEN",
                "message": "Token expired or missing"
            }

        for attempt in range(self.RETRIES + 1):
            try:
                response = requests.request(
                    method,
                    url,
                    headers=self.headers,
                    timeout=self.TIMEOUT,
                    **kwargs
                )

                # ---- status validation ----
                if response.status_code not in [200, 202]:
                    return {
                        "error": "HTTP_ERROR",
                        "status_code": response.status_code,
                        "message": response.text
                    }

                # ---- safe JSON parsing ----
                try:
                    return response.json()
                except Exception:
                    return {
                        "error": "INVALID_JSON",
                        "raw": response.text
                    }

            except requests.exceptions.Timeout:
                last_error = {"error": "TIMEOUT"}
            except requests.exceptions.ConnectionError:
                last_error = {"error": "CONNECTION_ERROR"}
            except Exception as e:
                last_error = {"error": str(e)}

            time.sleep(0.5 * (attempt + 1))

        return last_error or {"error": "UNKNOWN_ERROR"}

    # --------------------------------
    # PLACE ORDER (RAW)
    # --------------------------------
    def place_order(self, payload):
        url = f"{self.BASE_URL}/orders"
        return self._request("POST", url, json=payload)

    # --------------------------------
    # CANCEL ORDER
    # --------------------------------
    def cancel_order(self, order_id):
        url = f"{self.BASE_URL}/orders/{order_id}"

        res = self._request("DELETE", url)

        if isinstance(res, dict) and "error" in res:
            return res

        if not isinstance(res, dict) or "orderId" not in res:
            return {
                "error": "INVALID_CANCEL_RESPONSE",
                "response": res
            }

        return res

    # --------------------------------
    # GET ORDERS
    # --------------------------------
    def get_orders(self):
        url = f"{self.BASE_URL}/orders"

        res = self._request("GET", url)

        if isinstance(res, dict) and "error" in res:
            return res

        if not isinstance(res, list):
            return {
                "error": "INVALID_ORDERS_RESPONSE",
                "response": res
            }

        return res