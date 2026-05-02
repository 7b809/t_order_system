from django.urls import path
from .views import get_orders

urlpatterns = [
    path("orders/", get_orders),
]