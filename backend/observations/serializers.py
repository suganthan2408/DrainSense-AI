"""DrainSense AI — Observation and Forecast serializers."""

from rest_framework import serializers
from .models import DataSource, RainfallObservation, RainfallForecast


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = "__all__"


class RainfallObservationSerializer(serializers.ModelSerializer):
    zone_code = serializers.CharField(source="zone.code", read_only=True)
    district_name = serializers.SerializerMethodField()
    state_name = serializers.SerializerMethodField()
    source_name = serializers.CharField(source="source.name", read_only=True, allow_null=True)
    source_is_synthetic = serializers.BooleanField(
        source="source.is_synthetic", read_only=True, allow_null=True
    )
    source_last_fetched_at = serializers.DateTimeField(
        source="source.last_fetched_at", read_only=True, allow_null=True
    )

    class Meta:
        model = RainfallObservation
        fields = [
            "id", "zone", "zone_code", "district_name", "state_name",
            "source", "source_name", "source_is_synthetic", "source_last_fetched_at",
            "observed_at", "rainfall_mm", "period_hours",
            "rainfall_1h_mm", "rainfall_3h_mm", "rainfall_6h_mm", "rainfall_24h_mm",
            "is_estimated", "quality_flag", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_district_name(self, obj):
        return obj.zone.district.name if obj.zone.district_id else None

    def get_state_name(self, obj):
        return obj.zone.district.state.name if obj.zone.district_id else None


class RainfallForecastSerializer(serializers.ModelSerializer):
    zone_code = serializers.CharField(source="zone.code", read_only=True)
    district_name = serializers.SerializerMethodField()
    state_name = serializers.SerializerMethodField()
    source_name = serializers.CharField(source="source.name", read_only=True, allow_null=True)
    source_is_synthetic = serializers.BooleanField(
        source="source.is_synthetic", read_only=True, allow_null=True
    )
    source_last_fetched_at = serializers.DateTimeField(
        source="source.last_fetched_at", read_only=True, allow_null=True
    )

    class Meta:
        model = RainfallForecast
        fields = [
            "id", "zone", "zone_code", "district_name", "state_name",
            "source", "source_name", "source_is_synthetic", "source_last_fetched_at",
            "issued_at", "forecast_for", "forecast_horizon_hours",
            "rainfall_mm", "precipitation_probability_pct",
            "temperature_c", "humidity_pct", "wind_speed_kmh",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_district_name(self, obj):
        return obj.zone.district.name if obj.zone.district_id else None

    def get_state_name(self, obj):
        return obj.zone.district.state.name if obj.zone.district_id else None
