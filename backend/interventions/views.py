"""DrainSense AI — Intervention views."""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from zones.geography import apply_geographic_filters, filter_by_zone_id

from .models import InterventionRecommendation, InterventionLog
from .serializers import (
    InterventionRecommendationSerializer,
    InterventionStatusUpdateSerializer,
)

logger = logging.getLogger("drainsense")


class InterventionRecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    The Intervention Priority Queue — ranked list of drainage interventions.
    """
    queryset = (
        InterventionRecommendation.objects
        .select_related("zone", "risk_assessment")
        .prefetch_related("logs")
        .filter(status__in=[
            InterventionRecommendation.STATUS_PENDING,
            InterventionRecommendation.STATUS_ASSIGNED,
        ])
        .order_by("priority_rank")
    )
    serializer_class = InterventionRecommendationSerializer

    def get_queryset(self):
        qs =         InterventionRecommendation.objects.select_related(
            "zone", "zone__district", "zone__district__state", "risk_assessment"
        ).prefetch_related("logs")
        qs = apply_geographic_filters(qs, self.request.query_params, "zone__")
        status_filter = self.request.query_params.get("status")
        zone_id = self.request.query_params.get("zone")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if zone_id:
            qs = filter_by_zone_id(qs, zone_id, "zone_id")
        return qs.order_by("priority_rank")

    @extend_schema(
        request=InterventionStatusUpdateSerializer,
        responses={200: InterventionRecommendationSerializer},
        description="Update the status of an intervention (e.g. PENDING → ASSIGNED → COMPLETED).",
    )
    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        """Update intervention status and log the change."""
        intervention = self.get_object()
        serializer = InterventionStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = intervention.status
        new_status = serializer.validated_data["status"]
        notes = serializer.validated_data.get("notes", "")
        assigned_to = serializer.validated_data.get("assigned_to", "")

        intervention.status = new_status
        if assigned_to:
            intervention.assigned_to = assigned_to
        intervention.save(update_fields=["status", "assigned_to", "updated_at"])

        InterventionLog.objects.create(
            recommendation=intervention,
            status_from=old_status,
            status_to=new_status,
            notes=notes,
            logged_by=request.user.username if request.user.is_authenticated else "anonymous",
        )
        return Response(InterventionRecommendationSerializer(intervention).data)

    @extend_schema(
        description="Re-run the AWS Strands agent explanation for this intervention.",
    )
    @action(detail=True, methods=["post"], url_path="explain")
    def explain(self, request, pk=None):
        """Run the Strands agent to generate an explanation for this intervention."""
        intervention = self.get_object()
        try:
            from agent.strands_agent import explain_intervention
            result = explain_intervention(intervention)
            return Response(result)
        except Exception as exc:
            logger.exception("Agent explanation failed for intervention %s", pk)
            return Response(
                {"error": "Agent explanation failed.", "detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
