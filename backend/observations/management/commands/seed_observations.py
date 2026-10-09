"""
DrainSense AI — Seed synthetic rainfall observations for demonstration.

All records are marked is_estimated=True and linked to a DataSource
with is_synthetic=True.
"""

import random
from datetime import datetime, timedelta, timezone
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed synthetic rainfall observations and one live forecast fetch."

    def handle(self, *args, **options):
        from zones.models import Zone
        from observations.models import DataSource, RainfallObservation

        source, _ = DataSource.objects.get_or_create(
            name="Synthetic Demonstration Data",
            defaults={
                "url": "",
                "description": "Synthetic rainfall data for hackathon demonstration. NOT real measurements.",
                "license_info": "Generated for demonstration purposes only.",
                "is_live": False,
                "is_synthetic": True,
            },
        )

        zones = Zone.objects.all()
        if not zones.exists():
            self.stdout.write(self.style.ERROR("No zones found. Run seed_zones first."))
            return

        now = datetime.now(timezone.utc)
        created = 0

        # Rainfall profiles: some zones heavy, some light
        zone_rain_profiles = {
            "CBE-001": (18.0, 82.0),   # heavy — Ukkadam lake
            "CBE-006": (22.0, 95.0),   # very heavy — Noyyal corridor
            "CBE-008": (14.0, 65.0),   # heavy — Kuniyamuthur
            "CBE-002": (8.0,  40.0),
            "CBE-003": (5.0,  25.0),
            "CBE-004": (3.0,  18.0),
            "CBE-005": (2.0,  12.0),
            "CBE-007": (4.0,  20.0),
        }

        for zone in zones:
            profile = zone_rain_profiles.get(zone.code, (5.0, 30.0))
            r1h = round(random.uniform(profile[0] * 0.7, profile[0] * 1.3), 1)
            r24h = round(random.uniform(profile[1] * 0.8, profile[1] * 1.2), 1)

            obs, created_flag = RainfallObservation.objects.get_or_create(
                zone=zone,
                observed_at=now.replace(minute=0, second=0, microsecond=0),
                period_hours=1.0,
                defaults={
                    "source": source,
                    "rainfall_mm": r1h,
                    "rainfall_1h_mm": r1h,
                    "rainfall_3h_mm": round(r1h * 2.8, 1),
                    "rainfall_6h_mm": round(r1h * 5.2, 1),
                    "rainfall_24h_mm": r24h,
                    "is_estimated": True,
                    "quality_flag": "OK",
                },
            )
            if created_flag:
                created += 1
                self.stdout.write(f"  Seeded rainfall for {zone.code}: 1h={r1h}mm, 24h={r24h}mm")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSeeded {created} rainfall observations.\n"
                f"NOTE: All values are SYNTHETIC DEMONSTRATION DATA.\n"
                f"Attempting to fetch live forecasts from Open-Meteo..."
            )
        )

        # Attempt live forecast fetch
        try:
            from observations.ingestion import fetch_open_meteo_forecasts
            count = fetch_open_meteo_forecasts()
            self.stdout.write(self.style.SUCCESS(f"Fetched {count} forecast records from Open-Meteo."))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Forecast fetch failed (non-fatal): {exc}"))
