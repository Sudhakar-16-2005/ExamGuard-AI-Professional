from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(_request):
    return JsonResponse({"status": "ok", "service": "ExamGuard AI"})


urlpatterns = [
    path(
        "",
        lambda request: JsonResponse(
            {"name": "ExamGuard AI", "admin": "/admin/", "health": "/health/"}
        ),
    ),
    path("admin/", admin.site.urls),
    path("integrations/", include("leaks.urls")),
    path("health/", health, name="health"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
