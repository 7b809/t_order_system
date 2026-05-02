from django.urls import path
from .views import get_logs

urlpatterns = [
    path("logs/", get_logs),
]