"""
DrainSense AI — Intervention models

InterventionRecommendation: a prioritised action linked to a risk assessment.
InterventionLog: records actions taken and their outcomes.
"""

from django.db import models
from zones.models import Zone, RiskAssessment


class InterventionRecommendation(models.Model):
    """
    A recommended intervention action for a zone, derived from a risk assessment.
    Forms the Intervention Priority Queue.
    """

    STATUS_PENDING = "PENDING"
    STATUS_ASSIGNED = "ASSIGNED"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_VERIFIED = "VERIFIED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ASSIGNED, "Assigned"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_VERIFIED, "Verified"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    URGENCY_LOW = "LOW"
    URGENCY_MEDIUM = "MEDIUM"
    URGENCY_HIGH = "HIGH"
    URGENCY_CRITICAL = "CRITICAL"

    URGENCY_CHOICES = [
        (URGENCY_LOW, "Low — within 48 hours"),
        (URGENCY_MEDIUM, "Medium — within 24 hours"),
        (URGENCY_HIGH, "High — within 6 hours"),
        (URGENCY_CRITICAL, "Critical — immediate action required"),
    ]

    ACTION_INSPECT = "INSPECT_DRAIN"
    ACTION_CLEAR = "CLEAR_BLOCKAGE"
    ACTION_ALERT = "ISSUE_ALERT"
    ACTION_ESCALATE = "ESCALATE"
    ACTION_MONITOR = "MONITOR"

    ACTION_CHOICES = [
        (ACTION_INSPECT, "Inspect drainage point"),
        (ACTION_CLEAR, "Clear drain blockage"),
        (ACTION_ALERT, "Issue public alert"),
        (ACTION_ESCALATE, "Escalate to senior authority"),
        (ACTION_MONITOR, "Continue monitoring"),
    ]

    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="interventions")
    risk_assessment = models.ForeignKey(
        RiskAssessment, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="interventions"
    )

    # Priority queue fields
    priority_rank = models.IntegerField(
        help_text="Rank in current priority queue (1 = highest priority)"
    )
    priority_score = models.FloatField(
        help_text="Composite score: risk × confidence × urgency factor"
    )

    # Recommendation content
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, default=ACTION_MONITOR)
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default=URGENCY_LOW)
    reason = models.TextField(help_text="Evidence-linked explanation of why this is prioritised")
    suggested_action_detail = models.TextField(
        help_text="Specific actionable instruction for the field inspector"
    )

    # Evidence links
    supporting_evidence = models.JSONField(
        default=list,
        help_text="List of evidence items: [{type, description, value, source}]"
    )

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    assigned_to = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_by = models.DateTimeField(null=True, blank=True)

    # Agent explanation (populated when Strands agent runs)
    agent_explanation = models.TextField(blank=True)
    agent_ran_at = models.DateTimeField(null=True, blank=True)
    agent_error = models.TextField(blank=True)

    class Meta:
        ordering = ["priority_rank", "-priority_score"]

    def __str__(self):
        return f"[{self.priority_rank}] {self.zone.code} — {self.get_action_display()} ({self.get_urgency_display()})"


class InterventionLog(models.Model):
    """Audit trail of status changes and field notes for an intervention."""

    recommendation = models.ForeignKey(
        InterventionRecommendation, on_delete=models.CASCADE, related_name="logs"
    )
    logged_at = models.DateTimeField(auto_now_add=True)
    status_from = models.CharField(max_length=20, blank=True)
    status_to = models.CharField(max_length=20)
    notes = models.TextField(blank=True)
    logged_by = models.CharField(max_length=200, blank=True, default="System")

    class Meta:
        ordering = ["-logged_at"]

    def __str__(self):
        return f"{self.recommendation} → {self.status_to} @ {self.logged_at}"
