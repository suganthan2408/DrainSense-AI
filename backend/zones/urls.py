"""DrainSense AI — Zone URL routing."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ZoneViewSet, RiskAssessmentViewSet

router = DefaultRouter()
router.register(r"zones", ZoneViewSet, basename="zone")
router.register(r"assessments", RiskAssessmentViewSet, basename="assessment")

urlpatterns = [
    path("", include(router.urls)),
]
