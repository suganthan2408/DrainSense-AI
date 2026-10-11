"""Geography reference and summary API routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CountryViewSet,
    DistrictViewSet,
    GeographicSummaryView,
    StateViewSet,
)

router = DefaultRouter()
router.register("countries", CountryViewSet, basename="country")
router.register("states", StateViewSet, basename="state")
router.register("districts", DistrictViewSet, basename="district")

urlpatterns = [
    path("summary/", GeographicSummaryView.as_view(), name="geographic-summary"),
    path("", include(router.urls)),
]
