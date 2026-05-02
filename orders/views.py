from django.http import JsonResponse
from core.db import get_orders_collection
from core.logger import get_logger

logger = get_logger("orders_api")


def get_orders(request):
    try:
        # ✅ get collection (FIX)
        orders_collection = get_orders_collection()

        # ✅ pagination params (safe parsing)
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 10))

        if page < 1:
            page = 1
        if limit < 1:
            limit = 10

        skip = (page - 1) * limit

        # ✅ fetch paginated orders
        cursor = (
            orders_collection
            .find()
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        orders = []
        for o in cursor:
            o["_id"] = str(o["_id"])  # Mongo ObjectId → string

            # ✅ safe JSON conversion (optional but recommended)
            if "created_at" in o:
                try:
                    o["created_at"] = str(o["created_at"])
                except:
                    pass

            orders.append(o)

        # ✅ total count
        total = orders_collection.count_documents({})

        # ✅ status counts
        placed_count = orders_collection.count_documents({"status": "PLACED"})
        ignored_count = orders_collection.count_documents({"status": "IGNORED"})
        failed_count = orders_collection.count_documents({"status": "FAILED"})

        return JsonResponse({
            "page": page,
            "limit": limit,
            "total": total,
            "placed": placed_count,
            "ignored": ignored_count,
            "failed": failed_count,
            "data": orders
        })

    except Exception as e:
        logger.error(f"/api/orders error: {str(e)}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)