"""DrainSense AI — root URL configuration."""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # API v1
    path("api/v1/zones/", include("zones.urls")),
    path("api/v1/observations/", include("observations.urls")),
    path("api/v1/interventions/", include("interventions.urls")),
    path("api/v1/outcomes/", include("outcomes.urls")),
    path("api/v1/agent/", include("agent.urls")),

    # OpenAPI docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
