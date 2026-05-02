from django.urls import path
from . import views

urlpatterns = [
    # LIVE trading (REAL MONEY)
    path("live/place/", views.place_order_view),
    path("live/exit/<str:order_id>/", views.exit_order_view),
    path("live/cancel/<str:order_id>/", views.cancel_order_view),

    # Order data
    path("live/orders/", views.orders_view),
    path("live/orders/saved/", views.saved_orders_view),
    path("live/orders/<str:order_id>/", views.order_detail_view),
    path("live/orders/sync/<str:order_id>/", views.sync_order_view),

    # Portfolio
    path("live/portfolio/", views.portfolio_view),
]