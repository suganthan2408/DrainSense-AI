"""DrainSense AI — Outcome and evaluation views."""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from zones.geography import apply_geographic_filters, filter_by_zone_id

from .models import WaterloggingOutcome, ModelEvaluation
from .serializers import (
    WaterloggingOutcomeSerializer,
    WaterloggingOutcomeCreateSerializer,
    ModelEvaluationSerializer,
)

logger = logging.getLogger("drainsense")


class WaterloggingOutcomeViewSet(viewsets.ModelViewSet):
    """Record and retrieve observed waterlogging outcomes."""

    queryset = WaterloggingOutcome.objects.select_related(
        "zone", "zone__district", "zone__district__state", "risk_assessment"
    ).all()

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return WaterloggingOutcomeCreateSerializer
        return WaterloggingOutcomeSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_geographic_filters(qs, self.request.query_params, "zone__")
        zone_id = self.request.query_params.get("zone")
        outcome = self.request.query_params.get("outcome")
        if zone_id:
            qs = filter_by_zone_id(qs, zone_id, "zone_id")
        if outcome:
            qs = qs.filter(outcome=outcome)
        return qs


class ModelEvaluationViewSet(viewsets.ReadOnlyModelViewSet):
    """Retrieve stored model evaluation metrics."""

    queryset = ModelEvaluation.objects.all()
    serializer_class = ModelEvaluationSerializer

    @extend_schema(
        description=(
            "Trigger computation of evaluation metrics from verified outcomes. "
            "Returns an error if fewer than the minimum required observations exist."
        )
    )
    @action(detail=False, methods=["post"], url_path="compute")
    def compute(self, request):
        """Compute and store evaluation metrics from verified outcomes."""
        try:
            from ml.evaluator import compute_and_store_metrics
            evaluation = compute_and_store_metrics()
            if evaluation is None:
                n = WaterloggingOutcome.objects.exclude(
                    outcome=WaterloggingOutcome.OUTCOME_UNKNOWN
                ).count()
                return Response(
                    {
                        "detail": (
                            f"Not enough verified observations ({n}) to compute metrics. "
                            f"Need at least {ModelEvaluation.MIN_OBSERVATIONS}."
                        )
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(ModelEvaluationSerializer(evaluation).data, status=status.HTTP_201_CREATED)
        except Exception as exc:
            logger.exception("Metric computation failed")
            return Response(
                {"error": "Metric computation failed.", "detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
