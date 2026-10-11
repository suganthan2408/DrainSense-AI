"""DrainSense AI — Zone serializers."""

from rest_framework import serializers
from .models import Country, District, State, Zone, RiskAssessment


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "code", "name", "source_name", "source_url", "is_active"]


class StateSerializer(serializers.ModelSerializer):
    country_code = serializers.CharField(source="country.code", read_only=True)
    country_name = serializers.CharField(source="country.name", read_only=True)
    district_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = State
        fields = [
            "id", "code", "lgd_code", "name", "administrative_type",
            "country_code", "country_name", "latitude", "longitude",
            "boundary_geojson", "source_name", "source_url", "is_verified",
            "is_active", "last_updated", "district_count",
        ]


class DistrictSerializer(serializers.ModelSerializer):
    state_code = serializers.CharField(source="state.code", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta:
        model = District
        fields = [
            "id", "code", "lgd_code", "name", "state", "state_code", "state_name",
            "latitude", "longitude", "boundary_geojson", "source_name",
            "source_url", "is_verified", "is_active", "last_updated",
        ]


class ZoneSerializer(serializers.ModelSerializer):
    latest_risk_score = serializers.SerializerMethodField()
    latest_risk_category = serializers.SerializerMethodField()
    latest_assessed_at = serializers.SerializerMethodField()
    district_code = serializers.SerializerMethodField()
    district_name = serializers.SerializerMethodField()
    state_code = serializers.SerializerMethodField()
    state_name = serializers.SerializerMethodField()
    district_is_verified = serializers.SerializerMethodField()

    class Meta:
        model = Zone
        fields = [
            "id", "name", "code", "description",
            "latitude", "longitude",
            "area_km2", "avg_elevation_m", "min_elevation_m",
            "drainage_density", "imperviousness_pct", "population_density",
            "historical_flood_count", "last_flood_date",
            "data_source", "is_synthetic",
            "district", "district_code", "district_name", "state_code", "state_name",
            "district_is_verified",
            "boundary_geojson", "is_active",
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

    def get_district_code(self, obj):
        return obj.district.code if obj.district_id else None

    def get_district_name(self, obj):
        return obj.district.name if obj.district_id else None

    def get_state_code(self, obj):
        return obj.district.state.code if obj.district_id else None

    def get_state_name(self, obj):
        return obj.district.state.name if obj.district_id else None

    def get_district_is_verified(self, obj):
        return obj.district.is_verified if obj.district_id else None


class RiskAssessmentSerializer(serializers.ModelSerializer):
    zone_code = serializers.CharField(source="zone.code", read_only=True)
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    district_name = serializers.CharField(
        source="zone.district.name", read_only=True, allow_null=True
    )
    state_name = serializers.CharField(
        source="zone.district.state.name", read_only=True, allow_null=True
    )
    score_method_display = serializers.CharField(source="get_score_method_display", read_only=True)

    class Meta:
        model = RiskAssessment
        fields = [
            "id", "zone", "zone_code", "zone_name", "district_name", "state_name",
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
