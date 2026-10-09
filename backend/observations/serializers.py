"""DrainSense AI — Observation and Forecast serializers."""

from rest_framework import serializers
from .models import DataSource, RainfallObservation, RainfallForecast


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = "__all__"


class RainfallObservationSerializer(serializers.ModelSerializer):
    zone_code = serializers.CharField(source="zone.code", read_only=True)

    class Meta:
        model = RainfallObservation
        fields = [
            "id", "zone", "zone_code", "source",
            "observed_at", "rainfall_mm", "period_hours",
            "rainfall_1h_mm", "rainfall_3h_mm", "rainfall_6h_mm", "rainfall_24h_mm",
            "is_estimated", "quality_flag", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class RainfallForecastSerializer(serializers.ModelSerializer):
    zone_code = serializers.CharField(source="zone.code", read_only=True)

    class Meta:
        model = RainfallForecast
        fields = [
            "id", "zone", "zone_code", "source",
            "issued_at", "forecast_for", "forecast_horizon_hours",
            "rainfall_mm", "precipitation_probability_pct",
            "temperature_c", "humidity_pct", "wind_speed_kmh",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
