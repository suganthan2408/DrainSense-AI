"""
DrainSense AI — Zone models

A Zone represents a geographic drainage assessment unit in Coimbatore.
Risk assessments are attached to zones.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Country(models.Model):
    """Country reference record; currently India is the supported country."""

    code = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=100, unique=True)
    source_name = models.CharField(max_length=200, blank=True)
    source_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "countries"

    def __str__(self):
        return self.name


class State(models.Model):
    """State or Union Territory reference data."""

    TYPE_STATE = "STATE"
    TYPE_UT = "UT"
    TYPE_CHOICES = [(TYPE_STATE, "State"), (TYPE_UT, "Union Territory")]

    country = models.ForeignKey(
        Country, on_delete=models.PROTECT, related_name="states"
    )
    code = models.CharField(
        max_length=16,
        unique=True,
        help_text="Stable subdivision identifier, e.g. IN-TN.",
    )
    lgd_code = models.CharField(max_length=20, null=True, blank=True, unique=True)
    name = models.CharField(max_length=150)
    administrative_type = models.CharField(
        max_length=10, choices=TYPE_CHOICES, default=TYPE_STATE
    )
    latitude = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)],
    )
    longitude = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)],
    )
    boundary_geojson = models.JSONField(null=True, blank=True)
    source_name = models.CharField(max_length=200, blank=True)
    source_url = models.URLField(blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["country", "name"], name="unique_state_name_per_country"
            )
        ]
        indexes = [
            models.Index(fields=["country", "is_active"], name="state_country_active_idx")
        ]

    def __str__(self):
        return self.name


class District(models.Model):
    """District reference data, optionally enriched from an official directory."""

    state = models.ForeignKey(State, on_delete=models.PROTECT, related_name="districts")
    code = models.CharField(max_length=60, unique=True)
    lgd_code = models.CharField(max_length=20, null=True, blank=True)
    name = models.CharField(max_length=150)
    latitude = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)],
    )
    longitude = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)],
    )
    boundary_geojson = models.JSONField(null=True, blank=True)
    source_name = models.CharField(max_length=200, blank=True)
    source_url = models.URLField(blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["state", "name"], name="unique_district_name_per_state"
            ),
            models.UniqueConstraint(
                fields=["state", "lgd_code"],
                condition=models.Q(lgd_code__isnull=False),
                name="unique_district_lgd_code_per_state",
            ),
        ]
        indexes = [
            models.Index(fields=["state", "is_active"], name="district_state_active_idx")
        ]

    def __str__(self):
        return f"{self.name}, {self.state.name}"


class Zone(models.Model):
    """Geographic zone for waterlogging risk assessment."""

    # Risk category constants
    RISK_LOW = "LOW"
    RISK_MODERATE = "MODERATE"
    RISK_HIGH = "HIGH"
    RISK_CRITICAL = "CRITICAL"
    RISK_UNKNOWN = "UNKNOWN"

    RISK_CHOICES = [
        (RISK_LOW, "Low"),
        (RISK_MODERATE, "Moderate"),
        (RISK_HIGH, "High"),
        (RISK_CRITICAL, "Critical"),
        (RISK_UNKNOWN, "Unknown"),
    ]

    # Identifiers
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True, help_text="Short zone code, e.g. CBE-001")
    description = models.TextField(blank=True)

    # Geography — centroid of zone (WGS84)
    latitude = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)]
    )
    longitude = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)]
    )
    district = models.ForeignKey(
        District,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="zones",
    )
    boundary_geojson = models.JSONField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Physical characteristics
    area_km2 = models.FloatField(null=True, blank=True)
    avg_elevation_m = models.FloatField(
        null=True, blank=True,
        help_text="Average elevation in metres above sea level"
    )
    min_elevation_m = models.FloatField(null=True, blank=True)
    drainage_density = models.FloatField(
        null=True, blank=True,
        help_text="Estimated drain network density (km/km²). Null when unknown."
    )
    imperviousness_pct = models.FloatField(
        null=True, blank=True,
        help_text="Estimated impervious surface percentage (0–100)"
    )
    population_density = models.FloatField(
        null=True, blank=True,
        help_text="People per km²"
    )

    # Historical waterlogging
    historical_flood_count = models.IntegerField(
        default=0,
        help_text="Number of waterlogging events recorded in available historical data"
    )
    last_flood_date = models.DateField(null=True, blank=True)
    data_source = models.CharField(
        max_length=200,
        default="Synthetic demonstration data",
        help_text="Source of zone attributes"
    )
    is_synthetic = models.BooleanField(
        default=True,
        help_text="True when zone data is synthetic/demonstration, not from official sources"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        indexes = [
            models.Index(fields=["district", "code"], name="zone_district_code_idx")
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class RiskAssessment(models.Model):
    """
    A point-in-time waterlogging risk assessment for a zone.

    The risk_score is a heuristic score (0–100) unless is_ml_prediction=True.
    It is NOT a calibrated probability of flooding.
    """

    SCORE_METHOD_HEURISTIC = "HEURISTIC"
    SCORE_METHOD_ML = "ML_MODEL"

    SCORE_METHOD_CHOICES = [
        (SCORE_METHOD_HEURISTIC, "Heuristic rule-based score"),
        (SCORE_METHOD_ML, "Machine learning model"),
    ]

    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="risk_assessments")
    assessed_at = models.DateTimeField(auto_now_add=True)
    valid_for_hours = models.IntegerField(default=6, help_text="How many hours this assessment is valid for")

    # Score
    risk_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Risk score 0–100. NOT a probability percentage."
    )
    risk_category = models.CharField(max_length=20, choices=Zone.RISK_CHOICES, default=Zone.RISK_UNKNOWN)

    # Method
    score_method = models.CharField(max_length=20, choices=SCORE_METHOD_CHOICES, default=SCORE_METHOD_HEURISTIC)
    model_version = models.CharField(max_length=50, default="heuristic-v1")
    is_ml_prediction = models.BooleanField(default=False)

    # Evidence — stored as JSON
    contributing_factors = models.JSONField(
        default=dict,
        help_text="Dict of factor_name -> {value, weight, description}"
    )
    data_warnings = models.JSONField(
        default=list,
        help_text="List of warnings about missing or stale data"
    )
    confidence_level = models.CharField(
        max_length=20,
        choices=[("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High")],
        default="LOW",
    )

    # Rainfall features used
    rainfall_1h_mm = models.FloatField(null=True, blank=True)
    rainfall_24h_mm = models.FloatField(null=True, blank=True)
    forecast_rainfall_6h_mm = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["-assessed_at"]
        get_latest_by = "assessed_at"

    def __str__(self):
        return f"Assessment {self.zone.code} @ {self.assessed_at:%Y-%m-%d %H:%M} — {self.risk_category} ({self.risk_score:.1f})"
