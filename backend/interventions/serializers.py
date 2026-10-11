"""DrainSense AI — Intervention serializers."""

from rest_framework import serializers
from .models import InterventionRecommendation, InterventionLog


class InterventionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionLog
        fields = ["id", "logged_at", "status_from", "status_to", "notes", "logged_by"]
        read_only_fields = ["id", "logged_at"]


class InterventionRecommendationSerializer(serializers.ModelSerializer):
    zone_code = serializers.CharField(source="zone.code", read_only=True)
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    zone_latitude = serializers.FloatField(source="zone.latitude", read_only=True)
    zone_longitude = serializers.FloatField(source="zone.longitude", read_only=True)
    district_name = serializers.SerializerMethodField()
    state_name = serializers.SerializerMethodField()
    zone_is_synthetic = serializers.BooleanField(source="zone.is_synthetic", read_only=True)
    urgency_display = serializers.CharField(source="get_urgency_display", read_only=True)
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    logs = InterventionLogSerializer(many=True, read_only=True)

    class Meta:
        model = InterventionRecommendation
        fields = [
            "id", "zone", "zone_code", "zone_name", "zone_latitude", "zone_longitude",
            "district_name", "state_name", "zone_is_synthetic",
            "risk_assessment",
            "priority_rank", "priority_score",
            "action", "action_display",
            "urgency", "urgency_display",
            "reason", "suggested_action_detail",
            "supporting_evidence",
            "status", "status_display",
            "assigned_to", "due_by",
            "agent_explanation", "agent_ran_at", "agent_error",
            "created_at", "updated_at",
            "logs",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_district_name(self, obj):
        return obj.zone.district.name if obj.zone.district_id else None

    def get_state_name(self, obj):
        return obj.zone.district.state.name if obj.zone.district_id else None


class InterventionStatusUpdateSerializer(serializers.Serializer):
    """Used to update the status of an intervention."""
    status = serializers.ChoiceField(choices=InterventionRecommendation.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)
    assigned_to = serializers.CharField(required=False, allow_blank=True)

    def validate_status(self, value):
        valid = [s[0] for s in InterventionRecommendation.STATUS_CHOICES]
        if value not in valid:
            raise serializers.ValidationError(f"Status must be one of: {valid}")
        return value
