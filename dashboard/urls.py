from django.urls import path
from .views import index, logs_view

urlpatterns = [
    path("", index),
    path("logs/", logs_view),  # ✅ NEW

]

