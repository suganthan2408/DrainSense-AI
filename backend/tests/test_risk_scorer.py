"""
DrainSense AI — Tests for the heuristic risk scorer.

These tests verify the scoring logic independently of the database
using unit-level tests for each component function.
"""

import sys
import os

# Ensure ml module is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "drainsense_backend.settings")
django.setup()

from django.test import TestCase
from ml.risk_scorer import (
    _rainfall_intensity_score,
    _forecast_score,
    _elevation_score,
    _drainage_score,
    _imperviousness_score,
    _historical_score,
    _score_to_category,
    WEIGHTS,
)


class RainfallIntensityScoreTest(TestCase):
    def test_no_data_returns_default(self):
        score, desc = _rainfall_intensity_score(None, None)
        self.assertEqual(score, 20.0)
        self.assertIn("No recent rainfall", desc)

    def test_extremely_heavy_1h(self):
        score, desc = _rainfall_intensity_score(70.0, None)
        self.assertGreaterEqual(score, 90)
        self.assertIn("Extremely heavy", desc)

    def test_very_heavy_24h(self):
        score, desc = _rainfall_intensity_score(None, 120.0)
        self.assertGreaterEqual(score, 75)

    def test_light_rain(self):
        score, desc = _rainfall_intensity_score(1.0, 10.0)
        self.assertLess(score, 40)


class ForecastScoreTest(TestCase):
    def test_no_forecast(self):
        score, desc = _forecast_score(None)
        self.assertEqual(score, 15.0)
        self.assertIn("No forecast", desc)

    def test_heavy_forecast(self):
        score, desc = _forecast_score(55.0)
        self.assertGreaterEqual(score, 85)

    def test_minimal_forecast(self):
        score, desc = _forecast_score(1.0)
        self.assertLessEqual(score, 10)


class ElevationScoreTest(TestCase):
    def test_no_elevation_data(self):
        score, desc = _elevation_score(None, None)
        self.assertEqual(score, 40.0)
        self.assertIn("unavailable", desc)

    def test_low_lying(self):
        score, _ = _elevation_score(270.0, 260.0)
        self.assertGreaterEqual(score, 70)

    def test_elevated(self):
        score, _ = _elevation_score(420.0, 410.0)
        self.assertLessEqual(score, 15)


class DrainageScoreTest(TestCase):
    def test_no_data(self):
        score, _ = _drainage_score(None)
        self.assertEqual(score, 50.0)

    def test_poor_drainage(self):
        score, _ = _drainage_score(0.5)
        self.assertGreaterEqual(score, 75)

    def test_good_drainage(self):
        score, _ = _drainage_score(6.0)
        self.assertLessEqual(score, 15)


class ScoreToCategoryTest(TestCase):
    def test_critical(self):
        self.assertEqual(_score_to_category(80.0), "CRITICAL")

    def test_high(self):
        self.assertEqual(_score_to_category(60.0), "HIGH")

    def test_moderate(self):
        self.assertEqual(_score_to_category(45.0), "MODERATE")

    def test_low(self):
        self.assertEqual(_score_to_category(25.0), "LOW")

    def test_boundary_high(self):
        self.assertEqual(_score_to_category(75.0), "CRITICAL")

    def test_boundary_moderate(self):
        self.assertEqual(_score_to_category(55.0), "HIGH")


class WeightSumTest(TestCase):
    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0, places=5)

    def test_all_weights_positive(self):
        for name, w in WEIGHTS.items():
            self.assertGreater(w, 0, f"Weight for {name} must be positive")


class IntegrationScoreZoneTest(TestCase):
    """Integration test: score_zone() runs end-to-end and saves an assessment."""

    def test_score_zone_creates_assessment(self):
        from zones.models import Zone, RiskAssessment
        from observations.models import RainfallObservation, DataSource
        from datetime import datetime, timezone

        zone = Zone.objects.create(
            name="Test Zone",
            code="TEST-001",
            latitude=11.0,
            longitude=77.0,
            avg_elevation_m=290.0,
            min_elevation_m=280.0,
            drainage_density=0.9,
            imperviousness_pct=70.0,
            historical_flood_count=5,
            is_synthetic=True,
        )

        src = DataSource.objects.create(name="Test Source", is_synthetic=True)
        RainfallObservation.objects.create(
            zone=zone,
            source=src,
            observed_at=datetime.now(timezone.utc),
            rainfall_mm=15.0,
            rainfall_1h_mm=15.0,
            rainfall_24h_mm=80.0,
            is_estimated=True,
        )

        from ml.risk_scorer import score_zone
        assessment = score_zone(zone)

        self.assertIsNotNone(assessment.pk)
        self.assertGreaterEqual(assessment.risk_score, 0.0)
        self.assertLessEqual(assessment.risk_score, 100.0)
        self.assertIn(assessment.risk_category, ["LOW", "MODERATE", "HIGH", "CRITICAL"])
        self.assertEqual(assessment.score_method, "HEURISTIC")
        self.assertFalse(assessment.is_ml_prediction)
        self.assertIsInstance(assessment.contributing_factors, dict)
        self.assertEqual(len(assessment.contributing_factors), 6)

    def test_score_zone_no_observations(self):
        """score_zone works when no observations exist — uses defaults with warnings."""
        from zones.models import Zone, RiskAssessment

        zone = Zone.objects.create(
            name="Empty Zone",
            code="TEST-002",
            latitude=11.0,
            longitude=77.0,
            is_synthetic=True,
        )
        from ml.risk_scorer import score_zone
        assessment = score_zone(zone)
        self.assertIsNotNone(assessment.pk)
        # Should have data warnings
        self.assertGreater(len(assessment.data_warnings), 0)
