"""DrainSense AI — Zone serializers."""

from rest_framework import serializers
from .models import Zone, RiskAssessment


class ZoneSerializer(serializers.ModelSerializer):
    latest_risk_score = serializers.SerializerMethodField()
    latest_risk_category = serializers.SerializerMethodField()
    latest_assessed_at = serializers.SerializerMethodField()

    class Meta:
        model = Zone
        fields = [
            "id", "name", "code", "description",
            "latitude", "longitude",
            "area_km2", "avg_elevation_m", "min_elevation_m",
            "drainage_density", "imperviousness_pct", "population_density",
            "historical_flood_count", "last_flood_date",
            "data_source", "is_synthetic",
            "latest_risk_score", "latest_risk_category", "latest_assessed_at",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_latest_risk_score(self, obj):
        assessment = obj.risk_assessments.first()
        return round(assessment.risk_score, 1) if assessment else None

    def get_latest_risk_category(self, obj):
        assessment = obj.risk_assessments.first()
        return assessment.risk_category if assessment else Zone.RISK_UNKNOWN

    def get_latest_assessed_at(self, obj):
        assessment = obj.risk_assessments.first()
        return assessment.assessed_at if assessment else None


class RiskAssessmentSerializer(serializers.ModelSerializer):
    zone_code = serializers.CharField(source="zone.code", read_only=True)
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    score_method_display = serializers.CharField(source="get_score_method_display", read_only=True)

    class Meta:
        model = RiskAssessment
        fields = [
            "id", "zone", "zone_code", "zone_name",
            "assessed_at", "valid_for_hours",
            "risk_score", "risk_category",
            "score_method", "score_method_display", "model_version", "is_ml_prediction",
            "contributing_factors", "data_warnings", "confidence_level",
            "rainfall_1h_mm", "rainfall_24h_mm", "forecast_rainfall_6h_mm",
        ]
        read_only_fields = ["id", "assessed_at"]


class RiskAssessmentCreateSerializer(serializers.Serializer):
    """Input for triggering a new risk assessment for a zone."""
    zone_id = serializers.IntegerField()

    def validate_zone_id(self, value):
        if not Zone.objects.filter(pk=value).exists():
            raise serializers.ValidationError(f"Zone {value} does not exist.")
        return value
