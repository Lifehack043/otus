"""
URL configuration for config project.
"""

from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt


def health_check(request):
    """Простая проверка здоровья сервиса."""
    return HttpResponse("OK", content_type="text/plain")


urlpatterns = [
    path("", health_check, name="health"),
    path("polls/", include("polls.urls")),
    path("admin/", admin.site.urls),
]

admin.site.site_header = "Панель управления опросами"
admin.site.site_title = "Admin Polls"
admin.site.index_title = "Управление опросами"
