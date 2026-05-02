from django.http import JsonResponse
import os
from core.logger import get_logger

logger = get_logger("logs_api")

LOG_FILE = "logs/app.log"


def get_logs(request):
    try:
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 50))

        if not os.path.exists(LOG_FILE):
            return JsonResponse({"error": "Log file not found"}, status=404)

        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        lines.reverse()

        start = (page - 1) * limit
        end = start + limit

        return JsonResponse({
            "page": page,
            "limit": limit,
            "total": len(lines),
            "data": lines[start:end]
        })

    except Exception as e:
        logger.error(f"/logs error: {str(e)}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)