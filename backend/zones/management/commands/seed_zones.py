"""
DrainSense AI — Management command to seed Coimbatore drainage zones.

Data notes:
- Zone boundaries and attributes are SYNTHETIC DEMONSTRATION DATA.
- Coordinates are approximate centroids of real administrative/drainage areas.
- Elevation values sourced from SRTM-30m DEM (approximate).
- Historical flood counts are illustrative, not from official records.
- All zones are marked is_synthetic=True.

Sources used to inform geographic placement:
  - Coimbatore Municipal Corporation ward map
  - SRTM DEM public data
  - NDMA flood hazard reports for Tamil Nadu
"""

from django.core.management.base import BaseCommand
from zones.models import Zone


COIMBATORE_ZONES = [
    {
        "name": "Ukkadam Lake Surroundings",
        "code": "CBE-001",
        "description": "Low-lying area around Ukkadam lake. Prone to inundation during monsoon.",
        "latitude": 10.9820,
        "longitude": 76.9870,
        "area_km2": 3.2,
        "avg_elevation_m": 278.0,
        "min_elevation_m": 271.0,
        "drainage_density": 0.8,
        "imperviousness_pct": 72.0,
        "population_density": 8500,
        "historical_flood_count": 8,
        "data_source": "Synthetic — approximate from CMC ward map and SRTM DEM",
        "is_synthetic": True,
    },
    {
        "name": "Gandhipuram Central",
        "code": "CBE-002",
        "description": "Dense commercial and residential zone. High imperviousness, old drainage.",
        "latitude": 11.0016,
        "longitude": 76.9638,
        "area_km2": 2.8,
        "avg_elevation_m": 318.0,
        "min_elevation_m": 310.0,
        "drainage_density": 1.5,
        "imperviousness_pct": 85.0,
        "population_density": 12000,
        "historical_flood_count": 5,
        "data_source": "Synthetic — approximate from CMC ward map and SRTM DEM",
        "is_synthetic": True,
    },
    {
        "name": "RS Puram Residential",
        "code": "CBE-003",
        "description": "Mixed residential area with some low-lying pockets near Noyyal river.",
        "latitude": 10.9926,
        "longitude": 76.9534,
        "area_km2": 4.1,
        "avg_elevation_m": 305.0,
        "min_elevation_m": 295.0,
        "drainage_density": 2.2,
        "imperviousness_pct": 65.0,
        "population_density": 9200,
        "historical_flood_count": 3,
        "data_source": "Synthetic — approximate from CMC ward map and SRTM DEM",
        "is_synthetic": True,
    },
    {
        "name": "Singanallur Industrial",
        "code": "CBE-004",
        "description": "Industrial zone east of Coimbatore. Stormwater channels present.",
        "latitude": 10.9999,
        "longitude": 77.0239,
        "area_km2": 6.5,
        "avg_elevation_m": 348.0,
        "min_elevation_m": 335.0,
        "drainage_density": 3.1,
        "imperviousness_pct": 78.0,
        "population_density": 3200,
        "historical_flood_count": 2,
        "data_source": "Synthetic — approximate from CMC ward map and SRTM DEM",
        "is_synthetic": True,
    },
    {
        "name": "Peelamedu Aerodrome Zone",
        "code": "CBE-005",
        "description": "Zone near airport with mixed land use. Relatively elevated.",
        "latitude": 11.0307,
        "longitude": 77.0406,
        "area_km2": 5.8,
        "avg_elevation_m": 374.0,
        "min_elevation_m": 362.0,
        "drainage_density": 2.8,
        "imperviousness_pct": 55.0,
        "population_density": 5100,
        "historical_flood_count": 1,
        "data_source": "Synthetic — approximate from CMC ward map and SRTM DEM",
        "is_synthetic": True,
    },
    {
        "name": "Noyyal River Corridor",
        "code": "CBE-006",
        "description": "Flood plain along Noyyal river. High vulnerability during peak flows.",
        "latitude": 10.9744,
        "longitude": 76.9901,
        "area_km2": 7.3,
        "avg_elevation_m": 270.0,
        "min_elevation_m": 262.0,
        "drainage_density": 0.6,
        "imperviousness_pct": 45.0,
        "population_density": 4700,
        "historical_flood_count": 11,
        "data_source": "Synthetic — approximate from CMC ward map and SRTM DEM",
        "is_synthetic": True,
    },
    {
        "name": "Saravanampatti IT Corridor",
        "code": "CBE-007",
        "description": "Newer development north-east. Drainage infrastructure still maturing.",
        "latitude": 11.0641,
        "longitude": 77.0251,
        "area_km2": 8.2,
        "avg_elevation_m": 391.0,
        "min_elevation_m": 378.0,
        "drainage_density": 1.9,
        "imperviousness_pct": 60.0,
        "population_density": 4300,
        "historical_flood_count": 2,
        "data_source": "Synthetic — approximate from CMC ward map and SRTM DEM",
        "is_synthetic": True,
    },
    {
        "name": "Kuniyamuthur South",
        "code": "CBE-008",
        "description": "Southern residential fringe. Lower elevation with seasonal waterlogging.",
        "latitude": 10.9576,
        "longitude": 76.9731,
        "area_km2": 3.9,
        "avg_elevation_m": 283.0,
        "min_elevation_m": 275.0,
        "drainage_density": 1.2,
        "imperviousness_pct": 62.0,
        "population_density": 7800,
        "historical_flood_count": 6,
        "data_source": "Synthetic — approximate from CMC ward map and SRTM DEM",
        "is_synthetic": True,
    },
]


class Command(BaseCommand):
    help = "Seed Coimbatore drainage zones with documented synthetic demonstration data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing zones before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            count = Zone.objects.count()
            Zone.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Cleared {count} existing zones."))

        created_count = 0
        updated_count = 0

        for zone_data in COIMBATORE_ZONES:
            zone, created = Zone.objects.update_or_create(
                code=zone_data["code"],
                defaults=zone_data,
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created: {zone}")
            else:
                updated_count += 1
                self.stdout.write(f"  Updated: {zone}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSeeded {created_count} new zones, updated {updated_count} existing zones.\n"
                f"NOTE: All zone attributes are SYNTHETIC DEMONSTRATION DATA.\n"
                f"They are not official Coimbatore Municipal Corporation records."
            )
        )
