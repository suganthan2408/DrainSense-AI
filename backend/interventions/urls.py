from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InterventionRecommendationViewSet

router = DefaultRouter()
router.register(r"", InterventionRecommendationViewSet, basename="intervention")

urlpatterns = [path("", include(router.urls))]
