"""Idempotently import district records from a normalized official LGD CSV."""

import csv
import re
from pathlib import Path
from urllib.parse import urlparse

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from zones.models import Country, District, State


REQUIRED_COLUMNS = {
    "state_name",
    "state_code",
    "state_type",
    "state_lgd_code",
    "district_name",
    "district_lgd_code",
}


def _clean(value):
    return (value or "").strip()


def _coordinate(value, field, row_number, minimum, maximum):
    value = _clean(value)
    if not value:
        return None
    try:
        result = float(value)
    except ValueError as exc:
        raise ValueError(f"row {row_number}: {field} must be numeric") from exc
    if not minimum <= result <= maximum:
        raise ValueError(f"row {row_number}: {field} is out of range")
    return result


class Command(BaseCommand):
    help = (
        "Import district reference rows from a normalized CSV exported from "
        "the Government of India's Local Government Directory (LGD)."
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=Path)
        parser.add_argument(
            "--source-url",
            required=True,
            help="URL of the official LGD export/source page used for this file.",
        )
        parser.add_argument(
            "--source-name",
            default="Local Government Directory, Ministry of Panchayati Raj",
        )

    def handle(self, *args, **options):
        path = options["csv_path"]
        source_url = options["source_url"].strip()
        parsed_url = urlparse(source_url)
        if parsed_url.scheme != "https" or not (
            parsed_url.hostname == "lgdirectory.gov.in"
            or (parsed_url.hostname or "").endswith(".lgdirectory.gov.in")
        ):
            raise CommandError("--source-url must be an HTTPS LGD portal URL.")
        if not path.is_file():
            raise CommandError(f"CSV file not found: {path}")

        try:
            with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
                if missing:
                    raise CommandError(
                        "CSV is missing required columns: "
                        + ", ".join(sorted(missing))
                    )
                rows = self._validate_rows(reader)
        except UnicodeDecodeError as exc:
            raise CommandError("CSV must be UTF-8 encoded.") from exc

        if not rows:
            raise CommandError("CSV contains no district rows.")

        self._import_rows(rows, options["source_name"], source_url)
        self.stdout.write(self.style.SUCCESS(
            f"Imported or updated {len(rows)} district rows from {options['source_name']}."
        ))

    def _validate_rows(self, reader):
        rows = []
        errors = []
        seen_codes = set()
        for row_number, raw in enumerate(reader, start=2):
            row = {key: _clean(value) for key, value in raw.items()}
            if not row.get("state_name") or not row.get("district_name"):
                errors.append(f"row {row_number}: state_name and district_name are required")
                continue
            if not re.fullmatch(r"IN-[A-Z0-9]{2,4}", row.get("state_code", "")):
                errors.append(f"row {row_number}: state_code must be an ISO-style IN-XX code")
                continue
            if row.get("state_type") not in ("STATE", "UT"):
                errors.append(f"row {row_number}: state_type must be STATE or UT")
                continue
            if not row.get("district_lgd_code").isdigit():
                errors.append(f"row {row_number}: district_lgd_code must be numeric")
                continue
            if row.get("state_lgd_code") and not row["state_lgd_code"].isdigit():
                errors.append(f"row {row_number}: state_lgd_code must be numeric")
                continue

            row_key = (row["state_code"], row["district_lgd_code"])
            if row_key in seen_codes:
                errors.append(f"row {row_number}: duplicate state/district LGD code")
                continue
            seen_codes.add(row_key)
            try:
                row["latitude"] = _coordinate(
                    row.get("latitude"), "latitude", row_number, -90, 90
                )
                row["longitude"] = _coordinate(
                    row.get("longitude"), "longitude", row_number, -180, 180
                )
            except ValueError as exc:
                errors.append(str(exc))
                continue
            rows.append(row)

        if errors:
            raise CommandError("CSV validation failed:\n- " + "\n- ".join(errors))
        return rows

    @transaction.atomic
    def _import_rows(self, rows, source_name, source_url):
        country, _ = Country.objects.get_or_create(
            code="IN",
            defaults={
                "name": "India",
                "source_name": source_name,
                "source_url": source_url,
            },
        )
        now = timezone.now()
        for row in rows:
            state, created = State.objects.get_or_create(
                code=row["state_code"],
                defaults={
                    "country": country,
                    "name": row["state_name"],
                    "administrative_type": row["state_type"],
                },
            )
            if not created:
                if state.country_id != country.id:
                    raise CommandError(
                        f"State {state.code} is linked to a different country."
                    )
                state.name = row["state_name"]
                state.administrative_type = row["state_type"]
            state.lgd_code = row.get("state_lgd_code") or state.lgd_code
            state.source_name = source_name
            state.source_url = source_url
            state.is_verified = True
            state.is_active = True
            state.last_updated = now
            state.save()

            district_code = f"{state.code}-LGD-{row['district_lgd_code']}"
            district = District.objects.filter(
                state=state, lgd_code=row["district_lgd_code"]
            ).first()
            if district is None:
                district = District.objects.filter(
                    state=state, name__iexact=row["district_name"]
                ).first()
            values = {
                "code": district_code,
                "lgd_code": row["district_lgd_code"],
                "name": row["district_name"],
                "latitude": row.get("latitude"),
                "longitude": row.get("longitude"),
                "source_name": source_name,
                "source_url": source_url,
                "is_verified": True,
                "is_active": True,
                "last_updated": now,
            }
            if district is None:
                District.objects.create(state=state, **values)
            else:
                for field, value in values.items():
                    setattr(district, field, value)
                district.save()
