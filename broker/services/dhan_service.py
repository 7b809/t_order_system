from dhanhq import dhanhq
from core.auth.dhan_token import load_valid_dhan_credentials


class DhanService:

    def __init__(self):
        creds = load_valid_dhan_credentials()

        if not creds:
            raise Exception("❌ No valid Dhan token found")

        self.client = dhanhq(
            client_id=creds["client_id"],
            access_token=creds["access_token"]
        )

    # ✅ PLACE ORDER
    def place_order(self, security_id, qty, price, side="BUY"):
        return self.client.place_order(
            security_id=security_id,
            exchange_segment=self.client.NSE_FNO,
            transaction_type=side,
            quantity=qty,
            order_type=self.client.MARKET,
            product_type=self.client.INTRA,
            price=price
        )

    # ✅ CANCEL
    def cancel_order(self, order_id):
        return self.client.cancel_order(order_id)

    # ✅ ORDER LIST
    def get_orders(self):
        return self.client.get_order_list()

    # ✅ POSITIONS
    def get_positions(self):
        return self.client.get_positions()

    # ✅ HOLDINGS
    def get_holdings(self):
        return self.client.get_holdings()