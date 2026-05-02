import logging
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .services.dhan_service import DhanService
from .services.order_manager import (
    save_order,
    cancel_order,
    get_all_orders,
    get_portfolio,
    get_all_saved_orders,
    get_order_from_db,
    sync_order,
    exit_order
)

logger = logging.getLogger(__name__)

dhan = DhanService()


# -----------------------------------------
# HELPER: serialize Mongo ObjectId
# -----------------------------------------
def serialize(doc):
    if not doc:
        return doc

    doc["_id"] = str(doc.get("_id"))
    return doc


def serialize_list(docs):
    return [serialize(d) for d in docs]


# -----------------------------------------
# PLACE ORDER (POST)
# -----------------------------------------
@csrf_exempt
def place_order_view(request):

    if request.method != "POST":
        logger.warning("⚠️ Invalid method for place_order")
        return JsonResponse({"error": "POST method required"}, status=400)

    try:
        try:
            body = json.loads(request.body)
        except Exception:
            logger.warning("⚠️ Invalid JSON received")
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        security_id = body.get("security_id")
        index = body.get("index", "NIFTY")
        side = body.get("side", "BUY")
        qty = body.get("qty")
        price = body.get("price", 0)

        # ✅ NEW (only addition — no logic change)
        amo = body.get("amo", False)
        amo_time = body.get("amo_time", "")

        if not security_id:
            logger.warning("⚠️ security_id missing")
            return JsonResponse({"error": "security_id required"}, status=400)

        # resolve qty properly (IMPORTANT FIX)
        final_qty = qty if qty else dhan.get_default_qty(index)

        # ✅ include AMO in debug payload (safe addition)
        request_payload = {
            "security_id": security_id,
            "index": index,
            "side": side,
            "qty": final_qty,
            "price": price,
            "amo": amo,
            "amo_time": amo_time
        }

        logger.info(f"📤 Placing order: {request_payload}")

        # ✅ ONLY CHANGE: pass amo + amo_time
        res = dhan.place_order(
            security_id=security_id,
            index=index,
            side=side,
            qty=final_qty,
            price=price,
            amo=amo,
            amo_time=amo_time
        )

        if not res or "orderId" not in res:
            logger.error(f"❌ Order placement failed: {res}")
            return JsonResponse(
                {"error": "Order placement failed", "response": res},
                status=500
            )

        save_order(res, {"index": index}, request_payload=request_payload)

        logger.info(f"✅ Order placed: {res.get('orderId')}")

        return JsonResponse(res)

    except Exception as e:
        logger.exception("❌ Exception in place_order_view")
        return JsonResponse({"error": str(e)}, status=500)
    

# -----------------------------------------
# EXIT ORDER
# -----------------------------------------
def exit_order_view(request, order_id):

    try:
        logger.info(f"🚪 Exit request for order: {order_id}")

        res = exit_order(order_id)

        if "error" in res:
            logger.warning(f"⚠️ Exit failed: {res}")
            return JsonResponse(res, status=400)

        return JsonResponse(res)

    except Exception as e:
        logger.exception(f"❌ Exception in exit_order_view for {order_id}")
        return JsonResponse({"error": str(e)}, status=500)


# -----------------------------------------
# CANCEL ORDER
# -----------------------------------------
def cancel_order_view(request, order_id):

    try:
        logger.info(f"❌ Cancel request for order: {order_id}")

        res = cancel_order(order_id)

        if "error" in res:
            logger.warning(f"⚠️ Cancel failed: {res}")
            return JsonResponse(res, status=400)

        return JsonResponse(res)

    except Exception as e:
        logger.exception(f"❌ Exception in cancel_order_view for {order_id}")
        return JsonResponse({"error": str(e)}, status=500)


# -----------------------------------------
# GET ALL ORDERS (BROKER)
# -----------------------------------------
def orders_view(request):

    try:
        logger.info("📥 Fetching broker orders")

        res = get_all_orders()

        return JsonResponse(res, safe=False)

    except Exception as e:
        logger.exception("❌ Exception in orders_view")
        return JsonResponse({"error": str(e)}, status=500)


# -----------------------------------------
# GET SAVED ORDERS (DB)
# -----------------------------------------
def saved_orders_view(request):

    try:
        logger.info("📥 Fetching saved orders")

        res = get_all_saved_orders()
        res = serialize_list(res)

        return JsonResponse(res, safe=False)

    except Exception as e:
        logger.exception("❌ Exception in saved_orders_view")
        return JsonResponse({"error": str(e)}, status=500)


# -----------------------------------------
# GET SINGLE ORDER (DB)
# -----------------------------------------
def order_detail_view(request, order_id):

    try:
        logger.info(f"📥 Fetching order from DB: {order_id}")

        res = get_order_from_db(order_id)
        res = serialize(res)

        if not res:
            return JsonResponse({"error": "Order not found"}, status=404)

        return JsonResponse(res, safe=False)

    except Exception as e:
        logger.exception(f"❌ Exception in order_detail_view for {order_id}")
        return JsonResponse({"error": str(e)}, status=500)


# -----------------------------------------
# SYNC ORDER
# -----------------------------------------
def sync_order_view(request, order_id):

    try:
        logger.info(f"🔄 Sync request for order: {order_id}")

        res = sync_order(order_id)

        if "error" in res:
            logger.warning(f"⚠️ Sync failed: {res}")
            return JsonResponse(res, status=400)

        return JsonResponse(res)

    except Exception as e:
        logger.exception(f"❌ Exception in sync_order_view for {order_id}")
        return JsonResponse({"error": str(e)}, status=500)


# -----------------------------------------
# PORTFOLIO
# -----------------------------------------
def portfolio_view(request):

    try:
        logger.info("📊 Fetching portfolio")

        res = get_portfolio()

        return JsonResponse(res)

    except Exception as e:
        logger.exception("❌ Exception in portfolio_view")
        return JsonResponse({"error": str(e)}, status=500)