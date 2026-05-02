from django.urls import path
from . import views

urlpatterns = [
    path("place/", views.place_order_view),
    path("cancel/<str:order_id>/", views.cancel_order_view),
    path("orders/", views.orders_view),
    path("portfolio/", views.portfolio_view),
]