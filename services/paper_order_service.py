from datetime import datetime
import uuid

def place_paper_order(
    security_id,
    exchange_segment,
    transaction_type,
    quantity,
    product_type,
    price,
    order_type,
    amo,
    meta=None
):
    order_id = "PAPER_" + str(uuid.uuid4())[:8]

    return {
        "status": "success",
        "data": {
            "orderId": order_id,
            "orderStatus": "TRADED",   # assume instant fill
            "securityId": security_id,
            "transactionType": transaction_type,
            "quantity": quantity,
            "price": price if price else "MARKET",
            "timestamp": datetime.utcnow().isoformat(),
            "mode": "paper"
        }
    }