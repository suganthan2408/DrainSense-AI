from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from django.test import TestCase
from rest_framework.test import APIClient

from ml.evaluator import compute_and_store_metrics
from observations.ingestion import fetch_open_meteo_forecasts
from observations.models import DataSource, RainfallForecast, RainfallObservation
from outcomes.models import ModelEvaluation, WaterloggingOutcome
from outcomes.serializers import WaterloggingOutcomeCreateSerializer
from zones.models import RiskAssessment, Zone


def make_zone(code):
    return Zone.objects.create(
        name=f"Test Zone {code}",
        code=code,
        latitude=11.0,
        longitude=77.0,
        avg_elevation_m=290.0,
        drainage_density=1.2,
        imperviousness_pct=60,
        is_synthetic=False,
    )


class RiskInputFreshnessTests(TestCase):
    def setUp(self):
        self.zone = make_zone("FRESH-001")
        self.observation_source = DataSource.objects.create(
            name="Freshness test observations",
            is_synthetic=True,
        )

    def test_stale_observation_is_not_used_in_score(self):
        RainfallObservation.objects.create(
            zone=self.zone,
            source=self.observation_source,
            observed_at=datetime.now(timezone.utc) - timedelta(hours=5),
            rainfall_mm=100,
            rainfall_1h_mm=100,
            rainfall_24h_mm=200,
            is_estimated=True,
        )

        from ml.risk_scorer import score_zone

        assessment = score_zone(self.zone)

        self.assertIsNone(assessment.rainfall_1h_mm)
        self.assertIsNone(assessment.rainfall_24h_mm)
        self.assertEqual(assessment.contributing_factors["rainfall_intensity"]["value"], 20)
        self.assertTrue(any("ignored as stale" in warning for warning in assessment.data_warnings))

    def test_six_hour_forecast_uses_six_hour_accumulation(self):
        now = datetime.now(timezone.utc)
        source = DataSource.objects.create(name="Forecast test source", is_live=True)
        for hour in range(1, 7):
            RainfallForecast.objects.create(
                zone=self.zone,
                source=source,
                issued_at=now,
                forecast_for=now + timedelta(hours=hour),
                forecast_horizon_hours=hour,
                rainfall_mm=2,
            )

        from ml.risk_scorer import score_zone

        assessment = score_zone(self.zone)

        self.assertEqual(assessment.forecast_rainfall_6h_mm, 12)

    def test_incomplete_forecast_window_is_reported_and_not_misrepresented(self):
        now = datetime.now(timezone.utc)
        source = DataSource.objects.create(name="Incomplete forecast source", is_live=True)
        RainfallForecast.objects.create(
            zone=self.zone,
            source=source,
            issued_at=now,
            forecast_for=now + timedelta(hours=1),
            forecast_horizon_hours=1,
            rainfall_mm=20,
        )

        from ml.risk_scorer import score_zone

        assessment = score_zone(self.zone)

        self.assertIsNone(assessment.forecast_rainfall_6h_mm)
        self.assertTrue(any("Fewer than six" in warning for warning in assessment.data_warnings))


class ForecastIngestionFailureTests(TestCase):
    def setUp(self):
        self.zone = make_zone("FETCH-001")

    @patch("observations.ingestion.requests.get")
    def test_request_failure_does_not_mark_source_live(self, get):
        import requests

        get.side_effect = requests.ConnectionError("offline")

        with self.assertRaisesRegex(RuntimeError, "no usable forecast data"):
            fetch_open_meteo_forecasts()

        source = DataSource.objects.get(name="Open-Meteo Forecast API")
        self.assertFalse(source.is_live)
        self.assertIsNone(source.last_fetched_at)

    @patch("observations.ingestion.requests.get")
    def test_malformed_response_is_ignored_without_saving_forecasts(self, get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"hourly": None}
        get.return_value = response

        with self.assertRaisesRegex(RuntimeError, "no usable forecast data"):
            fetch_open_meteo_forecasts()

        source = DataSource.objects.get(name="Open-Meteo Forecast API")
        self.assertFalse(source.is_live)
        self.assertEqual(RainfallForecast.objects.count(), 0)

    @patch("observations.ingestion.fetch_open_meteo_forecasts")
    def test_forecast_api_surfaces_upstream_failure(self, fetch):
        fetch.side_effect = RuntimeError("Open-Meteo unavailable")

        response = APIClient().post("/api/v1/observations/forecasts/fetch/")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"], "Forecast fetch failed.")


class OutcomeValidationTests(TestCase):
    def test_assessment_must_belong_to_selected_zone(self):
        first_zone = make_zone("OUTCOME-001")
        second_zone = make_zone("OUTCOME-002")
        assessment = RiskAssessment.objects.create(
            zone=first_zone,
            risk_score=40,
            risk_category=Zone.RISK_MODERATE,
        )
        start = datetime.now(timezone.utc)
        serializer = WaterloggingOutcomeCreateSerializer(data={
            "zone": second_zone.pk,
            "risk_assessment": assessment.pk,
            "observation_window_start": start.isoformat(),
            "observation_window_end": (start + timedelta(hours=1)).isoformat(),
            "outcome": WaterloggingOutcome.OUTCOME_OCCURRED,
            "report_source": WaterloggingOutcome.SOURCE_FIELD,
            "is_synthetic": False,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("risk_assessment", serializer.errors)

    def test_synthetic_report_cannot_be_marked_as_real(self):
        zone = make_zone("OUTCOME-003")
        start = datetime.now(timezone.utc)
        serializer = WaterloggingOutcomeCreateSerializer(data={
            "zone": zone.pk,
            "observation_window_start": start.isoformat(),
            "observation_window_end": (start + timedelta(hours=1)).isoformat(),
            "outcome": WaterloggingOutcome.OUTCOME_OCCURRED,
            "report_source": WaterloggingOutcome.SOURCE_SYNTHETIC,
            "is_synthetic": False,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("is_synthetic", serializer.errors)


class EvaluationGroundTruthTests(TestCase):
    def test_synthetic_outcomes_do_not_satisfy_minimum_sample_size(self):
        zone = make_zone("EVAL-001")
        assessment = RiskAssessment.objects.create(
            zone=zone,
            risk_score=60,
            risk_category=Zone.RISK_HIGH,
        )
        now = datetime.now(timezone.utc)
        for index in range(ModelEvaluation.MIN_OBSERVATIONS):
            WaterloggingOutcome.objects.create(
                zone=zone,
                risk_assessment=assessment if index == 0 else None,
                observation_window_start=now,
                observation_window_end=now + timedelta(hours=1),
                outcome=WaterloggingOutcome.OUTCOME_OCCURRED,
                report_source=WaterloggingOutcome.SOURCE_SYNTHETIC,
                is_synthetic=True,
            )

        self.assertIsNone(compute_and_store_metrics())
        self.assertEqual(ModelEvaluation.objects.count(), 0)

    def test_zero_f1_is_stored_as_zero_not_missing(self):
        now = datetime.now(timezone.utc)
        for index in range(ModelEvaluation.MIN_OBSERVATIONS):
            zone = make_zone(f"F1-{index:03d}")
            assessment = RiskAssessment.objects.create(
                zone=zone,
                risk_score=20 if index < 5 else 80,
                risk_category=Zone.RISK_LOW if index < 5 else Zone.RISK_CRITICAL,
            )
            WaterloggingOutcome.objects.create(
                zone=zone,
                risk_assessment=assessment,
                observation_window_start=now,
                observation_window_end=now + timedelta(hours=1),
                outcome=(
                    WaterloggingOutcome.OUTCOME_OCCURRED
                    if index < 5
                    else WaterloggingOutcome.OUTCOME_NOT_OCCURRED
                ),
                report_source=WaterloggingOutcome.SOURCE_FIELD,
                is_synthetic=False,
            )

        evaluation = compute_and_store_metrics()

        self.assertIsNotNone(evaluation)
        self.assertEqual(evaluation.precision, 0)
        self.assertEqual(evaluation.recall, 0)
        self.assertEqual(evaluation.f1_score, 0)
