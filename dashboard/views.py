from django.shortcuts import render

def index(request):
    return render(request, "dashboard/index.html")


def logs_view(request):
    return render(request, "dashboard/logs.html")