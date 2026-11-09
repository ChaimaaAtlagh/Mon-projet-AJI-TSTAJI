from django.urls import include, path
from core.health import health_check


urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("api/v1/", include("core.urls")),
]

