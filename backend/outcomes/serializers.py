"""DrainSense AI — Outcome serializers."""

from rest_framework import serializers
from .models import WaterloggingOutcome, ModelEvaluation


class WaterloggingOutcomeSerializer(serializers.ModelSerializer):
    zone_code = serializers.CharField(source="zone.code", read_only=True)
    district_name = serializers.SerializerMethodField()
    state_name = serializers.SerializerMethodField()
    outcome_display = serializers.CharField(source="get_outcome_display", read_only=True)

    class Meta:
        model = WaterloggingOutcome
        fields = [
            "id", "zone", "zone_code", "district_name", "state_name", "risk_assessment",
            "observation_window_start", "observation_window_end",
            "outcome", "outcome_display", "severity",
            "report_source", "source_notes", "is_synthetic",
            "recorded_by", "recorded_at",
        ]
        read_only_fields = ["id", "recorded_at"]

    def get_district_name(self, obj):
        return obj.zone.district.name if obj.zone.district_id else None

    def get_state_name(self, obj):
        return obj.zone.district.state.name if obj.zone.district_id else None


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
        start = data.get(
            "observation_window_start",
            self.instance.observation_window_start if self.instance else None,
        )
        end = data.get(
            "observation_window_end",
            self.instance.observation_window_end if self.instance else None,
        )
        if start is not None and end is not None and end <= start:
            raise serializers.ValidationError("Observation window end must be after start.")

        zone = data.get("zone", self.instance.zone if self.instance else None)
        assessment = data.get(
            "risk_assessment",
            self.instance.risk_assessment if self.instance else None,
        )
        if assessment and zone and assessment.zone_id != zone.id:
            raise serializers.ValidationError({
                "risk_assessment": "The assessment must belong to the selected zone."
            })

        report_source = data.get(
            "report_source",
            self.instance.report_source if self.instance else None,
        )
        is_synthetic = data.get(
            "is_synthetic",
            self.instance.is_synthetic if self.instance else True,
        )
        if (
            report_source == WaterloggingOutcome.SOURCE_SYNTHETIC
            and not is_synthetic
        ):
            raise serializers.ValidationError({
                "is_synthetic": "Synthetic demo reports must be marked as synthetic."
            })
        return data


class ModelEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelEvaluation
        fields = "__all__"
        read_only_fields = ["id", "evaluated_at"]
