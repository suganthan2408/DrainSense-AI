"""DrainSense AI — Agent API views."""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

logger = logging.getLogger("drainsense")


class AgentExplainView(APIView):
    """
    POST /api/v1/agent/explain/{intervention_id}/
    Run the AWS Strands agent to explain an intervention's risk assessment.
    """

    @extend_schema(
        description=(
            "Run the AWS Strands agent to generate an evidence-based explanation "
            "for a specific intervention recommendation. "
            "Falls back to a deterministic structured explanation if the agent is unavailable."
        ),
        responses={200: dict},
    )
    def post(self, request, intervention_id):
        from interventions.models import InterventionRecommendation
        from agent.strands_agent import explain_intervention

        try:
            intervention = InterventionRecommendation.objects.select_related(
                "zone", "risk_assessment"
            ).get(pk=intervention_id)
        except InterventionRecommendation.DoesNotExist:
            return Response(
                {"error": f"Intervention {intervention_id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            result = explain_intervention(intervention)
            return Response(result)
        except Exception as exc:
            logger.exception("Agent view failed for intervention %s", intervention_id)
            return Response(
                {"error": "Agent call failed.", "detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AgentStatusView(APIView):
    """GET /api/v1/agent/status/ — Check agent and AWS connectivity."""

    def get(self, request):
        import os
        try:
            from agent.strands_agent import STRANDS_AVAILABLE, OllamaModel

            sdk_available = STRANDS_AVAILABLE
            ollama_available = OllamaModel is not None
            sdk_version = "strands-agents installed" if sdk_available else "not installed"
        except ImportError:
            sdk_available = False
            ollama_available = False
            sdk_version = "not installed"

        aws_configured = bool(
            os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY")
        )
        provider = os.environ.get("AGENT_MODEL_PROVIDER", "bedrock").strip().lower()

        if provider == "ollama":
            agent_mode = "ollama_local" if sdk_available and ollama_available else "fallback"
            model_id = os.environ.get("OLLAMA_MODEL_ID", "llama3.2:3b")
        elif provider == "bedrock":
            agent_mode = (
                "aws_bedrock"
                if sdk_available and aws_configured
                else "fallback"
            )
            model_id = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
        else:
            agent_mode = "fallback"
            model_id = None

        return Response({
            "strands_sdk_available": sdk_available,
            "strands_ollama_provider_available": ollama_available,
            "strands_sdk_info": sdk_version,
            "aws_credentials_configured": aws_configured,
            "aws_region": os.environ.get("AWS_DEFAULT_REGION", "not set"),
            "agent_model_provider": provider,
            "agent_model_id": model_id,
            "agent_mode": agent_mode,
            "mode_is_execution_evidence": False,
        })
