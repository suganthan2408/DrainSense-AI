"""DrainSense AI — Observation views."""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from .models import DataSource, RainfallObservation, RainfallForecast
from .serializers import DataSourceSerializer, RainfallObservationSerializer, RainfallForecastSerializer

logger = logging.getLogger("drainsense")


class DataSourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer


class RainfallObservationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RainfallObservation.objects.select_related("zone", "source").all()
    serializer_class = RainfallObservationSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        zone_id = self.request.query_params.get("zone")
        if zone_id:
            qs = qs.filter(zone_id=zone_id)
        return qs


class RainfallForecastViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RainfallForecast.objects.select_related("zone", "source").all()
    serializer_class = RainfallForecastSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        zone_id = self.request.query_params.get("zone")
        if zone_id:
            qs = qs.filter(zone_id=zone_id)
        return qs

    @extend_schema(
        description="Fetch fresh rainfall forecasts for all zones from Open-Meteo (free API, no key required)."
    )
    @action(detail=False, methods=["post"], url_path="fetch")
    def fetch(self, request):
        """Ingest latest forecasts from Open-Meteo for all zones."""
        try:
            from observations.ingestion import fetch_open_meteo_forecasts
            count = fetch_open_meteo_forecasts()
            return Response({"fetched": count}, status=status.HTTP_200_OK)
        except Exception as exc:
            logger.exception("Forecast fetch failed")
            return Response(
                {"error": "Forecast fetch failed.", "detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
