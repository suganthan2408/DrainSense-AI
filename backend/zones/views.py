"""DrainSense AI — Zone and RiskAssessment views."""

import logging
from django.db import models
from django.db.models import Count, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from observations.models import RainfallForecast, RainfallObservation
from interventions.models import InterventionRecommendation
from interventions.serializers import InterventionRecommendationSerializer
from .geography import (
    apply_geographic_filters,
    filter_by_zone_id,
    resolve_district,
    resolve_state,
)
from .models import Country, District, State, Zone, RiskAssessment
from .serializers import (
    CountrySerializer,
    DistrictSerializer,
    RiskAssessmentSerializer,
    RiskAssessmentCreateSerializer,
    StateSerializer,
    ZoneSerializer,
)

logger = logging.getLogger("drainsense")


class ZoneViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve drainage zones.
    """
    queryset = Zone.objects.select_related(
        "district", "district__state"
    ).prefetch_related("risk_assessments").filter(is_active=True)
    serializer_class = ZoneSerializer

    def get_queryset(self):
        queryset = apply_geographic_filters(
            super().get_queryset(), self.request.query_params
        )
        zone_id = self.request.query_params.get("zone")
        if zone_id and self.action == "list":
            queryset = filter_by_zone_id(queryset, zone_id)
        return queryset

    @extend_schema(
        request=RiskAssessmentCreateSerializer,
        responses={201: RiskAssessmentSerializer},
        description=(
            "Trigger a risk assessment for this zone. "
            "Uses the heuristic scorer (or ML model if available)."
        ),
    )
    @action(detail=True, methods=["post"], url_path="assess")
    def assess(self, request, pk=None):
        """Run a new risk assessment for the given zone."""
        zone = self.get_object()
        try:
            from ml.risk_scorer import score_zone
            assessment = score_zone(zone)
            serializer = RiskAssessmentSerializer(assessment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as exc:
            logger.exception("Risk assessment failed for zone %s", zone.code)
            return Response(
                {"error": "Risk assessment failed.", "detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RiskAssessmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve risk assessments.
    """
    queryset = RiskAssessment.objects.select_related("zone").all()
    serializer_class = RiskAssessmentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_geographic_filters(qs, self.request.query_params, "zone__")
        zone_id = self.request.query_params.get("zone")
        if zone_id:
            qs = filter_by_zone_id(qs, zone_id, "zone_id")
        return qs


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Country.objects.filter(is_active=True)
    serializer_class = CountrySerializer


class StateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StateSerializer

    def get_queryset(self):
        return (
            State.objects.filter(is_active=True)
            .select_related("country")
            .annotate(district_count=Count("districts", filter=Q(districts__is_active=True)))
        )


class DistrictViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DistrictSerializer

    def get_queryset(self):
        queryset = District.objects.filter(is_active=True).select_related("state")
        raw_state = self.request.query_params.get("state")
        if raw_state:
            queryset = queryset.filter(state=resolve_state(raw_state))
        return queryset


class GeographicSummaryView(APIView):
    """Return only coverage and risk metrics supported by existing records."""

    def get(self, request):
        state_value = request.query_params.get("state")
        district_value = request.query_params.get("district")
        state = resolve_state(state_value) if state_value else None
        district = resolve_district(district_value, state) if district_value else None
        zone_value = request.query_params.get("zone")

        zones = Zone.objects.filter(is_active=True).select_related(
            "district", "district__state"
        )
        if state:
            zones = zones.filter(district__state=state)
        if district:
            zones = zones.filter(district=district)
        if zone_value:
            zones = filter_by_zone_id(zones, zone_value)

        latest_categories = RiskAssessment.objects.filter(
            zone_id=OuterRef("pk")
        ).order_by("-assessed_at").values("risk_category")[:1]
        zone_metrics = zones.annotate(
            latest_category=Subquery(latest_categories)
        ).annotate(
            latest_category=Coalesce("latest_category", models.Value(Zone.RISK_UNKNOWN))
        )
        risk_counts = {
            category: zone_metrics.filter(latest_category=category).count()
            for category, _label in Zone.RISK_CHOICES
        }

        observations = RainfallObservation.objects.filter(zone__in=zones)
        forecasts = RainfallForecast.objects.filter(zone__in=zones)
        interventions = (
            InterventionRecommendation.objects.filter(zone__in=zones)
            .exclude(status=InterventionRecommendation.STATUS_CANCELLED)
            .select_related("zone", "zone__district", "zone__district__state")
            .order_by("priority_rank")[:5]
        )

        if district:
            scope_label = f"{district.name}, {district.state.name}"
            state_count = 1
            district_count = 1
        elif state:
            scope_label = state.name
            state_count = 1
            district_count = District.objects.filter(
                state=state, is_active=True
            ).count()
        else:
            scope_label = "India"
            state_count = State.objects.filter(is_active=True).count()
            district_count = District.objects.filter(
                is_active=True, state__is_active=True
            ).count()

        freshest_observation = observations.order_by("-observed_at").values_list(
            "observed_at", flat=True
        ).first()
        freshest_forecast = forecasts.order_by("-issued_at").values_list(
            "issued_at", flat=True
        ).first()
        return Response({
            "scope": scope_label,
            "generated_at": timezone.now(),
            "coverage": {
                "states": state_count,
                "districts": district_count,
                "zones": zones.count(),
                "zones_with_observations": observations.values("zone_id").distinct().count(),
                "zones_with_verified_observations": observations.filter(
                    is_estimated=False, quality_flag="OK"
                ).values("zone_id").distinct().count(),
                "zones_with_forecasts": forecasts.values("zone_id").distinct().count(),
                "synthetic_zones": zones.filter(is_synthetic=True).count(),
            },
            "risk_category_counts": risk_counts,
            "intervention_priorities": InterventionRecommendationSerializer(
                interventions, many=True
            ).data,
            "data_freshness": {
                "latest_observation_at": freshest_observation,
                "latest_forecast_issued_at": freshest_forecast,
                "observations_are_estimated": observations.filter(
                    is_estimated=True
                ).exists(),
            },
            "limitations": [
                "Risk scores are heuristic rankings, not calibrated probabilities.",
                "Risk categories are counted only for zones with an assessment; unassessed zones are UNKNOWN.",
                "Coverage reflects records currently present, not complete state or district coverage.",
            ],
        })
