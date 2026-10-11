import csv
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from interventions.models import InterventionRecommendation
from observations.models import DataSource, RainfallObservation
from outcomes.models import WaterloggingOutcome
from zones.models import Country, District, State, Zone


class GeographyAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tamil_nadu = State.objects.get(code="IN-TN")
        self.kerala = State.objects.get(code="IN-KL")
        self.coimbatore = District.objects.get(code="IN-TN-D-COIMBATORE")
        for index in range(1, 9):
            Zone.objects.create(
                name=f"Existing Coimbatore zone {index}",
                code=f"CBE-{index:03d}",
                latitude=10.98,
                longitude=76.98,
                district=self.coimbatore,
                is_synthetic=True,
            )

    def make_zone(self, code, district=None):
        return Zone.objects.create(
            name=f"Zone {code}",
            code=code,
            latitude=10.98,
            longitude=76.98,
            district=district,
            is_synthetic=True,
        )

    def test_seeded_states_and_coimbatore_relationship_exist(self):
        self.assertEqual(Country.objects.get(code="IN").name, "India")
        self.assertEqual(State.objects.filter(country__code="IN").count(), 9)
        zones = Zone.objects.filter(code__startswith="CBE-")
        self.assertEqual(zones.count(), 8)
        self.assertEqual(zones.filter(district=self.coimbatore).count(), 8)
        self.assertFalse(self.coimbatore.is_verified)
        self.assertIsNone(self.coimbatore.lgd_code)

    def test_district_list_filters_by_state(self):
        response = self.client.get("/api/v1/geography/districts/", {"state": "IN-TN"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.data["results"]], ["Coimbatore"])

        response = self.client.get("/api/v1/geography/districts/", {"state": "IN-KL"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [])

    def test_zone_endpoint_filters_by_state_and_district(self):
        first = self.make_zone("GEO-TN-001", self.coimbatore)
        other_district = District.objects.create(
            state=self.kerala,
            code="IN-KL-D-IMPORT-PENDING",
            name="Unverified fixture district",
            source_name="Test fixture",
        )
        second = self.make_zone("GEO-KL-001", other_district)

        response = self.client.get("/api/v1/zones/zones/", {"state": "IN-TN"})
        self.assertEqual(response.status_code, 200)
        codes = [zone["code"] for zone in response.data["results"]]
        self.assertIn(first.code, codes)
        self.assertNotIn(second.code, codes)

        response = self.client.get(
            "/api/v1/zones/zones/",
            {"state": "IN-KL", "district": other_district.code},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [zone["code"] for zone in response.data["results"]], [second.code]
        )

    def test_invalid_location_identifiers_return_validation_error(self):
        coimbatore_zone_id = Zone.objects.get(code="CBE-001").pk
        for url in (
            "/api/v1/geography/districts/?state=NOT-A-STATE",
            "/api/v1/zones/zones/?district=NOT-A-DISTRICT",
            "/api/v1/zones/zones/?zone=not-a-zone",
            f"/api/v1/zones/zones/?state=IN-KL&zone={coimbatore_zone_id}",
            "/api/v1/observations/rainfall/?zone=999999",
            "/api/v1/interventions/?zone=999999",
            "/api/v1/outcomes/outcomes/?zone=999999",
            "/api/v1/geography/summary/?state=NOT-A-STATE",
            "/api/v1/geography/summary/?state=IN-TN&district=IN-KL-D-NOPE",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 400)

    def test_summary_marks_absence_as_empty_coverage(self):
        response = self.client.get("/api/v1/geography/summary/?state=IN-KL")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["coverage"]["zones"], 0)
        self.assertEqual(response.data["coverage"]["zones_with_observations"], 0)
        self.assertTrue(all(value == 0 for value in response.data["risk_category_counts"].values()))
        self.assertIsNone(response.data["data_freshness"]["latest_observation_at"])

    def test_summary_can_scope_to_one_zone_and_reports_unassessed_as_unknown(self):
        zone = Zone.objects.get(code="CBE-001")
        response = self.client.get(
            "/api/v1/geography/summary/",
            {
                "state": "IN-TN",
                "district": self.coimbatore.code,
                "zone": str(zone.pk),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["coverage"]["zones"], 1)
        self.assertEqual(response.data["risk_category_counts"]["UNKNOWN"], 1)

    def test_location_filters_apply_to_interventions_and_rainfall(self):
        zone = self.make_zone("GEO-TN-002", self.coimbatore)
        assessment = zone.risk_assessments.create(
            risk_score=60,
            risk_category=Zone.RISK_HIGH,
        )
        InterventionRecommendation.objects.create(
            zone=zone,
            risk_assessment=assessment,
            priority_rank=1,
            priority_score=60,
            action=InterventionRecommendation.ACTION_INSPECT,
            urgency=InterventionRecommendation.URGENCY_HIGH,
            reason="Fixture",
            suggested_action_detail="Fixture",
        )
        source = DataSource.objects.create(name="Geography fixture")
        RainfallObservation.objects.create(
            zone=zone,
            source=source,
            observed_at="2026-10-10T00:00:00Z",
            rainfall_mm=1,
        )

        self.assertEqual(
            self.client.get("/api/v1/interventions/?state=IN-TN").status_code, 200
        )
        intervention_response = self.client.get(
            "/api/v1/interventions/?state=IN-KL"
        )
        self.assertEqual(intervention_response.status_code, 200)
        self.assertEqual(intervention_response.data["results"], [])

        rainfall_response = self.client.get(
            "/api/v1/observations/rainfall/?district=IN-TN-D-COIMBATORE"
        )
        self.assertEqual(rainfall_response.status_code, 200)
        self.assertTrue(all(
            record["district_name"] == "Coimbatore"
            for record in rainfall_response.data["results"]
        ))

    def test_outcomes_are_filtered_to_selected_state(self):
        kerala_district = District.objects.create(
            state=self.kerala,
            code="IN-KL-D-OUTCOME-FIXTURE",
            name="Kerala outcome fixture district",
            source_name="Test fixture",
        )
        tn_zone = self.make_zone("GEO-TN-OUTCOME", self.coimbatore)
        kl_zone = self.make_zone("GEO-KL-OUTCOME", kerala_district)
        now = timezone.now()
        for zone in (tn_zone, kl_zone):
            WaterloggingOutcome.objects.create(
                zone=zone,
                observation_window_start=now - timedelta(hours=2),
                observation_window_end=now - timedelta(hours=1),
                outcome=WaterloggingOutcome.OUTCOME_OCCURRED,
                report_source=WaterloggingOutcome.SOURCE_FIELD,
                is_synthetic=False,
            )

        response = self.client.get(
            "/api/v1/outcomes/outcomes/", {"state": "IN-TN"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["zone_code"] for item in response.data["results"]],
            [tn_zone.code],
        )

    def test_forecast_fetch_passes_only_the_requested_zone(self):
        zone = self.make_zone("GEO-TN-FORECAST", self.coimbatore)
        with patch(
            "observations.ingestion.fetch_open_meteo_forecasts", return_value=1
        ) as fetch:
            response = self.client.post(
                "/api/v1/observations/forecasts/fetch/"
                f"?state=IN-TN&district={self.coimbatore.code}&zone={zone.pk}"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["fetched"], 1)
        self.assertEqual(
            list(fetch.call_args.kwargs["zones"].values_list("pk", flat=True)),
            [zone.pk],
        )


class LGDImportCommandTests(TestCase):
    def setUp(self):
        self.district = District.objects.get(code="IN-TN-D-COIMBATORE")
        self.original_code = self.district.code
        for index in range(1, 9):
            Zone.objects.create(
                name=f"Existing Coimbatore zone {index}",
                code=f"CBE-{index:03d}",
                latitude=10.98,
                longitude=76.98,
                district=self.district,
                is_synthetic=True,
            )

    def make_csv(self, directory, rows):
        path = Path(directory) / "lgd-normalized.csv"
        fieldnames = [
            "state_code",
            "state_name",
            "state_type",
            "state_lgd_code",
            "district_name",
            "district_lgd_code",
            "latitude",
            "longitude",
        ]
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_import_is_idempotent_and_enriches_existing_district_without_relinking_zones(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_csv(directory, [{
                "state_code": "IN-TN",
                "state_name": "Tamil Nadu",
                "state_type": "STATE",
                "state_lgd_code": "901",
                "district_name": "Coimbatore",
                "district_lgd_code": "902",
            }])
            source = "https://lgdirectory.gov.in/"
            before_count = District.objects.count()
            call_command("import_lgd_districts", str(path), source_url=source, stdout=None)
            call_command("import_lgd_districts", str(path), source_url=source, stdout=None)

        self.assertEqual(District.objects.count(), before_count)
        self.district.refresh_from_db()
        self.assertNotEqual(self.district.code, self.original_code)
        self.assertEqual(self.district.lgd_code, "902")
        self.assertTrue(self.district.is_verified)
        self.assertEqual(
            Zone.objects.filter(code__startswith="CBE-", district=self.district).count(),
            8,
        )

    def test_import_rejects_non_lgd_source_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_csv(directory, [{
                "state_code": "IN-TN",
                "state_name": "Tamil Nadu",
                "state_type": "STATE",
                "district_name": "Test district",
                "district_lgd_code": "123",
            }])
            with self.assertRaises(CommandError):
                call_command(
                    "import_lgd_districts",
                    str(path),
                    source_url="https://example.org/",
                    stdout=None,
                )
        self.assertEqual(District.objects.count(), 1)
