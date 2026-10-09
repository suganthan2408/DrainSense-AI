"""
DrainSense AI — API integration tests.

Tests the core REST API endpoints:
- Zones list and detail
- Risk assessment trigger
- Intervention priority queue
- Outcome recording
- Agent status
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "drainsense_backend.settings")

import django
django.setup()

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from zones.models import Zone, RiskAssessment
from interventions.models import InterventionRecommendation
from observations.models import DataSource, RainfallObservation
from outcomes.models import WaterloggingOutcome
from datetime import datetime, timezone, timedelta


def _make_zone(code="API-001", name="API Test Zone"):
    return Zone.objects.create(
        name=name, code=code,
        latitude=11.0, longitude=77.0,
        avg_elevation_m=290.0, min_elevation_m=280.0,
        drainage_density=1.0, imperviousness_pct=68.0,
        historical_flood_count=4, is_synthetic=True,
    )


def _make_observation(zone):
    src, _ = DataSource.objects.get_or_create(name="Test API Source", defaults={"is_synthetic": True})
    return RainfallObservation.objects.create(
        zone=zone, source=src,
        observed_at=datetime.now(timezone.utc),
        rainfall_mm=12.0, rainfall_1h_mm=12.0, rainfall_24h_mm=55.0,
        is_estimated=True,
    )


class ZoneAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.zone = _make_zone()

    def test_list_zones(self):
        url = "/api/v1/zones/zones/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        # paginated response has 'results'
        results = data.get("results", data)
        codes = [z["code"] for z in results]
        self.assertIn("API-001", codes)

    def test_zone_detail(self):
        url = f"/api/v1/zones/zones/{self.zone.pk}/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["code"], "API-001")

    def test_zone_detail_not_found(self):
        resp = self.client.get("/api/v1/zones/zones/99999/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class RiskAssessmentAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.zone = _make_zone(code="API-002", name="Risk API Zone")
        _make_observation(self.zone)

    def test_assess_zone(self):
        url = f"/api/v1/zones/zones/{self.zone.pk}/assess/"
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.json()
        self.assertIn("risk_score", data)
        self.assertIn("risk_category", data)
        self.assertIn("contributing_factors", data)
        self.assertGreaterEqual(data["risk_score"], 0)
        self.assertLessEqual(data["risk_score"], 100)

    def test_assessments_list(self):
        # Trigger an assessment first
        self.client.post(f"/api/v1/zones/zones/{self.zone.pk}/assess/")
        resp = self.client.get(f"/api/v1/zones/assessments/?zone={self.zone.pk}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        results = data.get("results", data)
        self.assertGreater(len(results), 0)


class InterventionAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.zone = _make_zone(code="API-003", name="Intervention API Zone")
        _make_observation(self.zone)
        # Create an assessment and intervention
        self.client.post(f"/api/v1/zones/zones/{self.zone.pk}/assess/")
        self.intervention = InterventionRecommendation.objects.filter(zone=self.zone).first()

    def test_list_interventions(self):
        resp = self.client.get("/api/v1/interventions/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_update_intervention_status(self):
        if not self.intervention:
            self.skipTest("No intervention created")
        url = f"/api/v1/interventions/{self.intervention.pk}/status/"
        resp = self.client.patch(url, {"status": "ASSIGNED", "notes": "Assigned to team A"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["status"], "ASSIGNED")

    def test_update_intervention_invalid_status(self):
        if not self.intervention:
            self.skipTest("No intervention created")
        url = f"/api/v1/interventions/{self.intervention.pk}/status/"
        resp = self.client.patch(url, {"status": "INVALID_STATUS"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class OutcomeAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.zone = _make_zone(code="API-004", name="Outcome API Zone")
        _make_observation(self.zone)
        self.client.post(f"/api/v1/zones/zones/{self.zone.pk}/assess/")
        self.assessment = RiskAssessment.objects.filter(zone=self.zone).first()

    def test_record_outcome(self):
        now = datetime.now(timezone.utc)
        payload = {
            "zone": self.zone.pk,
            "risk_assessment": self.assessment.pk if self.assessment else None,
            "observation_window_start": now.isoformat(),
            "observation_window_end": (now + timedelta(hours=6)).isoformat(),
            "outcome": "OCCURRED",
            "severity": "MODERATE",
            "report_source": "SYNTHETIC_DEMO",
            "is_synthetic": True,
            "recorded_by": "test_runner",
        }
        resp = self.client.post("/api/v1/outcomes/outcomes/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.json()
        self.assertEqual(data["outcome"], "OCCURRED")

    def test_record_outcome_invalid_window(self):
        now = datetime.now(timezone.utc)
        payload = {
            "zone": self.zone.pk,
            "observation_window_start": (now + timedelta(hours=6)).isoformat(),
            "observation_window_end": now.isoformat(),  # end before start
            "outcome": "OCCURRED",
            "report_source": "SYNTHETIC_DEMO",
            "is_synthetic": True,
        }
        resp = self.client.post("/api/v1/outcomes/outcomes/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class AgentStatusAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_agent_status(self):
        resp = self.client.get("/api/v1/agent/status/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIn("strands_sdk_available", data)
        self.assertIn("aws_credentials_configured", data)
        self.assertIn("agent_mode", data)
