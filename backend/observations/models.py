"""
DrainSense AI — Observation and Forecast models

RainfallObservation: measured rainfall at a point in time.
RainfallForecast: forecast values from Open-Meteo or similar.
DataSource: metadata about where each data record came from.
"""

from django.db import models
from zones.models import Zone


class DataSource(models.Model):
    """Tracks the origin and freshness of ingested data."""

    name = models.CharField(max_length=200, unique=True)
    url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    license_info = models.TextField(blank=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)
    is_live = models.BooleanField(
        default=False,
        help_text="True only when this source provides real-time data actually fetched live"
    )
    is_synthetic = models.BooleanField(
        default=False,
        help_text="True when this source contains synthetic demonstration data"
    )

    def __str__(self):
        return self.name


class RainfallObservation(models.Model):
    """Measured or estimated rainfall for a zone at a specific time."""

    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="rainfall_observations")
    source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)

    observed_at = models.DateTimeField(db_index=True)
    rainfall_mm = models.FloatField(help_text="Rainfall in mm for the observation period")
    period_hours = models.FloatField(default=1.0, help_text="Accumulation period in hours")

    # Derived rolling totals (populated at ingestion time)
    rainfall_1h_mm = models.FloatField(null=True, blank=True)
    rainfall_3h_mm = models.FloatField(null=True, blank=True)
    rainfall_6h_mm = models.FloatField(null=True, blank=True)
    rainfall_24h_mm = models.FloatField(null=True, blank=True)

    is_estimated = models.BooleanField(
        default=False,
        help_text="True when value is interpolated or estimated, not directly measured"
    )
    quality_flag = models.CharField(
        max_length=20,
        choices=[("OK", "OK"), ("SUSPECT", "Suspect"), ("MISSING", "Missing")],
        default="OK",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-observed_at"]
        unique_together = [("zone", "observed_at", "period_hours")]

    def __str__(self):
        return f"{self.zone.code} rainfall {self.rainfall_mm}mm @ {self.observed_at}"


class RainfallForecast(models.Model):
    """Forecast rainfall for a zone from a weather API."""

    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="rainfall_forecasts")
    source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)

    issued_at = models.DateTimeField(help_text="When the forecast was generated/fetched")
    forecast_for = models.DateTimeField(help_text="The future time this forecast applies to")
    forecast_horizon_hours = models.FloatField()

    rainfall_mm = models.FloatField(help_text="Forecast rainfall in mm")
    precipitation_probability_pct = models.FloatField(null=True, blank=True)
    temperature_c = models.FloatField(null=True, blank=True)
    humidity_pct = models.FloatField(null=True, blank=True)
    wind_speed_kmh = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-issued_at", "forecast_horizon_hours"]
        unique_together = [("zone", "issued_at", "forecast_for")]

    def __str__(self):
        return f"{self.zone.code} forecast {self.rainfall_mm}mm for {self.forecast_for}"
