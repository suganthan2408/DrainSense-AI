"""DrainSense AI — Outcome serializers."""

from rest_framework import serializers
from .models import WaterloggingOutcome, ModelEvaluation


class WaterloggingOutcomeSerializer(serializers.ModelSerializer):
    zone_code = serializers.CharField(source="zone.code", read_only=True)
    outcome_display = serializers.CharField(source="get_outcome_display", read_only=True)

    class Meta:
        model = WaterloggingOutcome
        fields = [
            "id", "zone", "zone_code", "risk_assessment",
            "observation_window_start", "observation_window_end",
            "outcome", "outcome_display", "severity",
            "report_source", "source_notes", "is_synthetic",
            "recorded_by", "recorded_at",
        ]
        read_only_fields = ["id", "recorded_at"]


class WaterloggingOutcomeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterloggingOutcome
        fields = [
            "zone", "risk_assessment",
            "observation_window_start", "observation_window_end",
            "outcome", "severity",
            "report_source", "source_notes", "is_synthetic",
            "recorded_by",
        ]

    def validate(self, data):
        if data["observation_window_end"] <= data["observation_window_start"]:
            raise serializers.ValidationError("Observation window end must be after start.")
        return data


class ModelEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelEvaluation
        fields = "__all__"
        read_only_fields = ["id", "evaluated_at"]
