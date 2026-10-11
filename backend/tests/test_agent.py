import json
import os
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from agent import strands_agent
from interventions.models import InterventionRecommendation
from zones.models import RiskAssessment, Zone


class StrandsProviderTests(TestCase):
    def setUp(self):
        self.zone = Zone.objects.create(
            name="Agent Test Zone",
            code="AGENT-001",
            latitude=11.0,
            longitude=77.0,
            is_synthetic=True,
        )
        assessment = RiskAssessment.objects.create(
            zone=self.zone,
            risk_score=62,
            risk_category=Zone.RISK_HIGH,
        )
        self.intervention = InterventionRecommendation.objects.create(
            zone=self.zone,
            risk_assessment=assessment,
            priority_rank=1,
            priority_score=62,
            action=InterventionRecommendation.ACTION_INSPECT,
            urgency=InterventionRecommendation.URGENCY_HIGH,
            reason="Test evidence.",
            suggested_action_detail="Inspect the drainage point.",
        )

    @patch.dict(os.environ, {"AGENT_MODEL_PROVIDER": "ollama"}, clear=True)
    @patch("agent.strands_agent.OllamaModel")
    @patch("agent.strands_agent.Agent")
    def test_ollama_invokes_strands_without_aws_credentials(
        self, agent_class, model_class
    ):
        response = {
            "risk_summary": "Test explanation.",
            "contributing_factors": [],
            "data_limitations": [],
            "recommended_action": "Inspect.",
            "urgency": "HIGH",
            "human_verification_required": True,
            "confidence": "MEDIUM",
        }
        agent_class.return_value.return_value = json.dumps(response)

        result = strands_agent.explain_intervention(self.intervention)

        model_class.assert_called_once_with(
            host="http://127.0.0.1:11434",
            model_id="llama3.2:3b",
        )
        agent_class.assert_called_once()
        agent_class.return_value.assert_called_once()
        self.assertTrue(result["agent_available"])
        self.assertEqual(result["execution_status"], "success")
        self.assertEqual(result["model_provider"], "ollama")
        self.assertIn("local Ollama", result["model_used"])

    @patch.dict(
        os.environ,
        {
            "AGENT_MODEL_PROVIDER": "ollama",
            "OLLAMA_HOST": "http://127.0.0.1:11434",
            "OLLAMA_MODEL_ID": "test-model",
        },
        clear=True,
    )
    @patch("agent.strands_agent.OllamaModel")
    @patch("agent.strands_agent.Agent", side_effect=RuntimeError("provider error"))
    def test_provider_failure_returns_safe_deterministic_fallback(
        self, _agent_class, _model_class
    ):
        result = strands_agent.explain_intervention(self.intervention)

        self.assertFalse(result["agent_available"])
        self.assertEqual(result["execution_status"], "fallback")
        self.assertEqual(result["model_provider"], "ollama")
        self.assertNotIn("provider error", result["fallback_reason"])
        self.assertIn("RuntimeError", result["fallback_reason"])

    @patch.dict(os.environ, {"AGENT_MODEL_PROVIDER": "ollama"}, clear=True)
    def test_status_reports_provider_selection_not_execution(self):
        response = APIClient().get("/api/v1/agent/status/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["agent_model_provider"], "ollama")
        self.assertFalse(response.json()["mode_is_execution_evidence"])

    @patch.dict(os.environ, {}, clear=True)
    def test_explain_endpoint_returns_fallback_without_aws_credentials(self):
        response = APIClient().post(
            f"/api/v1/agent/explain/{self.intervention.pk}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["agent_available"])
        self.assertEqual(response.json()["execution_status"], "fallback")
        self.assertIn("AWS credentials not configured", response.json()["fallback_reason"])
