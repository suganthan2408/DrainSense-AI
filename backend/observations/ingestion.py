"""
DrainSense AI — Data ingestion

Fetches rainfall forecasts from Open-Meteo (free, no API key required).
Documentation: https://open-meteo.com/en/docs

Only fetches forecasts — does not modify historical records.
Marks all fetched records with the correct DataSource.
"""

import logging
import os
from datetime import datetime, timezone

import requests

logger = logging.getLogger("drainsense")

OPEN_METEO_BASE = os.environ.get("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1")
FETCH_TIMEOUT_S = 15


def fetch_open_meteo_forecasts() -> int:
    """
    Fetch hourly precipitation forecast for all zones from Open-Meteo.
    Returns count of new forecast records saved.
    """
    from zones.models import Zone
    from observations.models import DataSource, RainfallForecast

    source, _ = DataSource.objects.get_or_create(
        name="Open-Meteo Forecast API",
        defaults={
            "url": "https://open-meteo.com/",
            "description": "Free, open-source weather forecast API. No API key required.",
            "license_info": "Open-Meteo data is licensed under CC BY 4.0",
            "is_live": True,
            "is_synthetic": False,
        },
    )

    zones = Zone.objects.all()
    total_saved = 0
    now = datetime.now(timezone.utc)

    for zone in zones:
        try:
            params = {
                "latitude": zone.latitude,
                "longitude": zone.longitude,
                "hourly": "precipitation,precipitation_probability,temperature_2m,relative_humidity_2m,wind_speed_10m",
                "forecast_days": 2,
                "timezone": "Asia/Kolkata",
            }
            resp = requests.get(
                f"{OPEN_METEO_BASE}/forecast",
                params=params,
                timeout=FETCH_TIMEOUT_S,
            )
            resp.raise_for_status()
            data = resp.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            precip = hourly.get("precipitation", [])
            precip_prob = hourly.get("precipitation_probability", [])
            temps = hourly.get("temperature_2m", [])
            humidity = hourly.get("relative_humidity_2m", [])
            wind = hourly.get("wind_speed_10m", [])

            for i, time_str in enumerate(times):
                forecast_dt = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)
                if forecast_dt <= now:
                    continue  # skip past hours

                horizon_h = (forecast_dt - now).total_seconds() / 3600
                rain_val = precip[i] if i < len(precip) and precip[i] is not None else 0.0

                _, created = RainfallForecast.objects.get_or_create(
                    zone=zone,
                    issued_at=now.replace(minute=0, second=0, microsecond=0),
                    forecast_for=forecast_dt,
                    defaults={
                        "source": source,
                        "forecast_horizon_hours": round(horizon_h, 1),
                        "rainfall_mm": rain_val,
                        "precipitation_probability_pct": precip_prob[i] if i < len(precip_prob) else None,
                        "temperature_c": temps[i] if i < len(temps) else None,
                        "humidity_pct": humidity[i] if i < len(humidity) else None,
                        "wind_speed_kmh": wind[i] if i < len(wind) else None,
                    },
                )
                if created:
                    total_saved += 1

            # Update source freshness
            source.last_fetched_at = now
            source.save(update_fields=["last_fetched_at"])

        except requests.exceptions.RequestException as exc:
            logger.warning("Open-Meteo fetch failed for zone %s: %s", zone.code, exc)
            continue

    logger.info("Fetched %d new forecast records from Open-Meteo", total_saved)
    return total_saved
