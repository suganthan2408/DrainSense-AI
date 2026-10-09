from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DataSourceViewSet, RainfallObservationViewSet, RainfallForecastViewSet

router = DefaultRouter()
router.register(r"sources", DataSourceViewSet, basename="datasource")
router.register(r"rainfall", RainfallObservationViewSet, basename="rainfall")
router.register(r"forecasts", RainfallForecastViewSet, basename="forecast")

urlpatterns = [path("", include(router.urls))]
