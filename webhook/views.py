# webhook/views.py

import json
import threading

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from orders.services import process_order
from core.logger import get_logger

logger = get_logger("webhook_app")


# --------------------------------------------------
# 🚀 WEBHOOK (Django version)
# --------------------------------------------------
@csrf_exempt
def webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)

        if not data or "message" not in data:
            logger.warning("Invalid payload received")
            return JsonResponse({"error": "Invalid payload"}, status=400)

        raw_message = data["message"]

        logger.info(f"Webhook received: {raw_message}")

        # ✅ async execution (same as your Flask thread)
        threading.Thread(
            target=process_order,
            args=(raw_message,),
            daemon=True
        ).start()

        return JsonResponse({"status": "accepted"}, status=200)

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)