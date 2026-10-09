"""
DrainSense AI — Prediction outcome tracking and model evaluation

WaterloggingOutcome: records observed ground-truth after a prediction.
ModelEvaluation: stores evaluation metrics when enough observations exist.
"""

from django.db import models
from zones.models import Zone, RiskAssessment


class WaterloggingOutcome(models.Model):
    """
    Records whether waterlogging actually occurred for a zone in a time window.
    Used to evaluate the accuracy of risk assessments.
    """

    OUTCOME_OCCURRED = "OCCURRED"
    OUTCOME_NOT_OCCURRED = "NOT_OCCURRED"
    OUTCOME_UNKNOWN = "UNKNOWN"

    OUTCOME_CHOICES = [
        (OUTCOME_OCCURRED, "Waterlogging occurred"),
        (OUTCOME_NOT_OCCURRED, "No waterlogging"),
        (OUTCOME_UNKNOWN, "Not yet verified"),
    ]

    SOURCE_FIELD = "FIELD_REPORT"
    SOURCE_NEWS = "NEWS_REPORT"
    SOURCE_CITIZEN = "CITIZEN_REPORT"
    SOURCE_SENSOR = "SENSOR"
    SOURCE_SYNTHETIC = "SYNTHETIC_DEMO"

    SOURCE_CHOICES = [
        (SOURCE_FIELD, "Field inspector report"),
        (SOURCE_NEWS, "News/media report"),
        (SOURCE_CITIZEN, "Citizen report"),
        (SOURCE_SENSOR, "Sensor reading"),
        (SOURCE_SYNTHETIC, "Synthetic demonstration data"),
    ]

    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="outcomes")
    risk_assessment = models.OneToOneField(
        RiskAssessment, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="outcome"
    )

    observation_window_start = models.DateTimeField()
    observation_window_end = models.DateTimeField()
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, default=OUTCOME_UNKNOWN)
    severity = models.CharField(
        max_length=20,
        choices=[
            ("NONE", "None"), ("MINOR", "Minor"), ("MODERATE", "Moderate"), ("SEVERE", "Severe")
        ],
        default="NONE",
        blank=True,
    )

    # Source of ground-truth
    report_source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default=SOURCE_SYNTHETIC)
    source_notes = models.TextField(blank=True)
    is_synthetic = models.BooleanField(
        default=True,
        help_text="True when this outcome record is synthetic/demonstration data"
    )

    recorded_by = models.CharField(max_length=200, blank=True, default="System")
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-observation_window_start"]

    def __str__(self):
        return f"{self.zone.code} outcome: {self.outcome} ({self.observation_window_start:%Y-%m-%d})"


class ModelEvaluation(models.Model):
    """
    Stores computed evaluation metrics for the risk model over a time period.
    Only created when at least MIN_OBSERVATIONS verified outcomes are available.
    """

    MIN_OBSERVATIONS = 10  # do not report metrics below this threshold

    model_version = models.CharField(max_length=50)
    evaluated_at = models.DateTimeField(auto_now_add=True)
    evaluation_period_start = models.DateTimeField()
    evaluation_period_end = models.DateTimeField()

    n_observations = models.IntegerField()
    n_positive = models.IntegerField(help_text="Waterlogging events")
    n_negative = models.IntegerField(help_text="Non-events")

    # Classification metrics (null when not computable)
    precision = models.FloatField(null=True, blank=True)
    recall = models.FloatField(null=True, blank=True)
    f1_score = models.FloatField(null=True, blank=True)
    accuracy = models.FloatField(null=True, blank=True)

    # Confusion matrix
    true_positives = models.IntegerField(null=True, blank=True)
    true_negatives = models.IntegerField(null=True, blank=True)
    false_positives = models.IntegerField(null=True, blank=True)
    false_negatives = models.IntegerField(null=True, blank=True)

    # Threshold used to convert score to binary prediction
    classification_threshold = models.FloatField(
        default=50.0,
        help_text="Risk score threshold above which a HIGH/CRITICAL is predicted positive"
    )

    limitations_notes = models.TextField(
        blank=True,
        help_text="Honest notes about what these metrics mean and their limitations"
    )

    class Meta:
        ordering = ["-evaluated_at"]

    def __str__(self):
        return f"Eval {self.model_version} @ {self.evaluated_at:%Y-%m-%d} n={self.n_observations}"
