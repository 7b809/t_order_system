from datetime import datetime
from .base_service import (
    get_dhan_client,
    save_log,
    resolve_product_type,
    logger
)


def exit_position(
    security_id,
    exchange_segment="NSE_EQ",
    quantity=1,
    product_type="INTRA"
):
    try:
        dhan = get_dhan_client()

        txn = dhan.SELL

        resolved_product = resolve_product_type(exchange_segment, product_type)
        product = getattr(dhan, resolved_product)

        logger.info(f"Exiting position {security_id}")

        response = dhan.place_order(
            security_id=str(security_id),
            exchange_segment=exchange_segment,
            transaction_type=txn,
            quantity=int(quantity),
            order_type=dhan.MARKET,
            product_type=product,
            price=0
        )

        save_log({
            "type": "EXIT",
            "security_id": security_id,
            "qty": quantity,
            "response": response,
            "time": datetime.utcnow()
        })

        return response

    except Exception as e:
        logger.error(f"Exit failed: {e}")
        raise Exception(f"Exit failed: {e}")