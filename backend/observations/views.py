"""DrainSense AI — Observation views."""

import logging
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from zones.geography import apply_geographic_filters, filter_by_zone_id
from zones.models import Zone

from .models import DataSource, RainfallObservation, RainfallForecast
from .serializers import DataSourceSerializer, RainfallObservationSerializer, RainfallForecastSerializer

logger = logging.getLogger("drainsense")


class DataSourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DataSource.objects.all().order_by("name")
    serializer_class = DataSourceSerializer


class RainfallObservationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RainfallObservation.objects.select_related(
        "zone", "zone__district", "zone__district__state", "source"
    ).all()
    serializer_class = RainfallObservationSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_geographic_filters(qs, self.request.query_params, "zone__")
        zone_id = self.request.query_params.get("zone")
        if zone_id:
            qs = filter_by_zone_id(qs, zone_id, "zone_id")
        return qs


class RainfallForecastViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RainfallForecast.objects.select_related(
        "zone", "zone__district", "zone__district__state", "source"
    ).all()
    serializer_class = RainfallForecastSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_geographic_filters(qs, self.request.query_params, "zone__")
        zone_id = self.request.query_params.get("zone")
        if zone_id:
            qs = filter_by_zone_id(qs, zone_id, "zone_id")
        return qs

    @extend_schema(
        description="Fetch fresh rainfall forecasts for all zones from Open-Meteo (free API, no key required)."
    )
    @action(detail=False, methods=["post"], url_path="fetch")
    def fetch(self, request):
        """Ingest forecasts only for geocoded zones in the requested scope."""
        try:
            from observations.ingestion import fetch_open_meteo_forecasts
            zones = apply_geographic_filters(
                Zone.objects.all(), request.query_params
            )
            zone_value = request.query_params.get("zone")
            if zone_value:
                zones = filter_by_zone_id(zones, zone_value)
            count = fetch_open_meteo_forecasts(zones=zones)
            return Response({"fetched": count}, status=status.HTTP_200_OK)
        except ValidationError:
            raise
        except Exception as exc:
            logger.exception("Forecast fetch failed")
            return Response(
                {"error": "Forecast fetch failed.", "detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
