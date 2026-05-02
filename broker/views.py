from django.http import JsonResponse
from .services.order_manager import (
    place_default_order,
    cancel_order,
    get_all_orders,
    get_portfolio
)


def place_order_view(request):
    res = place_default_order()
    return JsonResponse(res)


def cancel_order_view(request, order_id):
    res = cancel_order(order_id)
    return JsonResponse(res)


def orders_view(request):
    res = get_all_orders()
    return JsonResponse(res)


def portfolio_view(request):
    res = get_portfolio()
    return JsonResponse(res)