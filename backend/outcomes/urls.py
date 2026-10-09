from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WaterloggingOutcomeViewSet, ModelEvaluationViewSet

router = DefaultRouter()
router.register(r"outcomes", WaterloggingOutcomeViewSet, basename="outcome")
router.register(r"evaluations", ModelEvaluationViewSet, basename="evaluation")

urlpatterns = [path("", include(router.urls))]
