"""DrainSense AI — Zone and RiskAssessment views."""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from .models import Zone, RiskAssessment
from .serializers import ZoneSerializer, RiskAssessmentSerializer, RiskAssessmentCreateSerializer

logger = logging.getLogger("drainsense")


class ZoneViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve drainage zones.
    """
    queryset = Zone.objects.prefetch_related("risk_assessments").all()
    serializer_class = ZoneSerializer

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
        zone_id = self.request.query_params.get("zone")
        if zone_id:
            qs = qs.filter(zone_id=zone_id)
        return qs
