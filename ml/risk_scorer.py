"""
DrainSense AI — Heuristic Risk Scorer

This module implements a transparent, rule-based waterlogging risk score
for drainage zones in Coimbatore, Tamil Nadu.

IMPORTANT: This is a HEURISTIC ESTIMATE, not a trained or validated ML model.
The score (0–100) is NOT a probability of flooding.
It is designed to be replaced by a validated ML model once labeled data is available.

Scoring rationale (documented for transparency):
  - Rainfall intensity is the dominant short-term trigger
  - Elevation and drainage infrastructure determine vulnerability
  - Historical records provide a prior risk baseline
  - Impervious surface area affects runoff volume
  - Data availability affects confidence, not the score itself

References used to inform thresholds:
  - IMD rainfall classification: https://mausam.imd.gov.in/
  - Urban flood risk literature for Indian cities
"""

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

import django

logger = logging.getLogger("drainsense")


# ---------------------------------------------------------------------------
# Heuristic weight configuration
# ---------------------------------------------------------------------------

WEIGHTS = {
    "rainfall_intensity": 0.35,   # current + recent observed rainfall
    "forecast_rainfall":  0.20,   # upcoming forecast
    "elevation_risk":     0.20,   # low elevation / topographic vulnerability
    "drainage_risk":      0.10,   # poor drainage density / infrastructure
    "imperviousness":     0.08,   # impervious surface runoff multiplier
    "historical_risk":    0.07,   # historical flood frequency prior
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-6, "Weights must sum to 1.0"


def _rainfall_intensity_score(rainfall_1h_mm: Optional[float], rainfall_24h_mm: Optional[float]) -> tuple[float, str]:
    """
    Score based on IMD rainfall classification thresholds.
    Returns (0-100 score, description)
    """
    if rainfall_1h_mm is None and rainfall_24h_mm is None:
        return 20.0, "No recent rainfall data available"

    score = 0.0
    parts = []

    if rainfall_1h_mm is not None:
        # IMD: heavy rain > 7.5mm/hr, very heavy > 35.5mm/hr, extremely heavy > 64.5mm/hr
        if rainfall_1h_mm >= 64.5:
            score = max(score, 95)
            parts.append(f"Extremely heavy rain: {rainfall_1h_mm:.1f}mm/hr")
        elif rainfall_1h_mm >= 35.5:
            score = max(score, 80)
            parts.append(f"Very heavy rain: {rainfall_1h_mm:.1f}mm/hr")
        elif rainfall_1h_mm >= 7.5:
            score = max(score, 55)
            parts.append(f"Heavy rain: {rainfall_1h_mm:.1f}mm/hr")
        elif rainfall_1h_mm >= 2.5:
            score = max(score, 30)
            parts.append(f"Moderate rain: {rainfall_1h_mm:.1f}mm/hr")
        else:
            score = max(score, 10)
            parts.append(f"Light rain: {rainfall_1h_mm:.1f}mm/hr")

    if rainfall_24h_mm is not None:
        # IMD: heavy rainfall day > 64.5mm, very heavy > 115.6mm, extremely heavy > 204.4mm
        if rainfall_24h_mm >= 204.4:
            score = max(score, 95)
            parts.append(f"Extremely heavy 24h total: {rainfall_24h_mm:.1f}mm")
        elif rainfall_24h_mm >= 115.6:
            score = max(score, 80)
            parts.append(f"Very heavy 24h total: {rainfall_24h_mm:.1f}mm")
        elif rainfall_24h_mm >= 64.5:
            score = max(score, 60)
            parts.append(f"Heavy 24h total: {rainfall_24h_mm:.1f}mm")
        elif rainfall_24h_mm >= 15.6:
            score = max(score, 35)
            parts.append(f"Moderate 24h total: {rainfall_24h_mm:.1f}mm")
        else:
            score = max(score, 10)
            parts.append(f"Light 24h total: {rainfall_24h_mm:.1f}mm")

    return score, "; ".join(parts) or "Low rainfall"


def _forecast_score(forecast_6h_mm: Optional[float]) -> tuple[float, str]:
    """Score based on 6h forecast rainfall."""
    if forecast_6h_mm is None:
        return 15.0, "No forecast data available"
    if forecast_6h_mm >= 50:
        return 90.0, f"Heavy rain forecast: {forecast_6h_mm:.1f}mm over 6h"
    elif forecast_6h_mm >= 25:
        return 70.0, f"Significant rain forecast: {forecast_6h_mm:.1f}mm over 6h"
    elif forecast_6h_mm >= 10:
        return 45.0, f"Moderate rain forecast: {forecast_6h_mm:.1f}mm over 6h"
    elif forecast_6h_mm >= 3:
        return 25.0, f"Light rain forecast: {forecast_6h_mm:.1f}mm over 6h"
    return 5.0, f"Minimal rain forecast: {forecast_6h_mm:.1f}mm over 6h"


def _elevation_score(avg_elevation_m: Optional[float], min_elevation_m: Optional[float]) -> tuple[float, str]:
    """Score based on topographic vulnerability. Lower = more at risk."""
    if avg_elevation_m is None:
        return 40.0, "Elevation data unavailable — assuming moderate risk"

    # Coimbatore elevation ranges roughly 100–500m above MSL
    # Low-lying areas (< 300m in this context) at higher risk from runoff
    if avg_elevation_m < 280:
        base = 70.0
    elif avg_elevation_m < 320:
        base = 45.0
    elif avg_elevation_m < 380:
        base = 25.0
    else:
        base = 10.0

    # Boost if min elevation is very low (bowl-shaped catchment)
    if min_elevation_m is not None and min_elevation_m < avg_elevation_m - 20:
        base = min(base + 15, 100)

    return base, f"Avg elevation {avg_elevation_m:.0f}m — {'low-lying' if avg_elevation_m < 310 else 'moderate' if avg_elevation_m < 360 else 'elevated'}"


def _drainage_score(drainage_density: Optional[float]) -> tuple[float, str]:
    """Score based on drainage infrastructure density. Lower density = higher risk."""
    if drainage_density is None:
        return 50.0, "Drainage density unknown — assuming moderate risk"
    # km of drain per km² — higher is better infrastructure
    if drainage_density < 1.0:
        return 80.0, f"Poor drainage density: {drainage_density:.2f} km/km²"
    elif drainage_density < 2.5:
        return 55.0, f"Moderate drainage density: {drainage_density:.2f} km/km²"
    elif drainage_density < 5.0:
        return 30.0, f"Adequate drainage density: {drainage_density:.2f} km/km²"
    return 10.0, f"Good drainage density: {drainage_density:.2f} km/km²"


def _imperviousness_score(imperviousness_pct: Optional[float]) -> tuple[float, str]:
    """Score based on impervious surface percentage."""
    if imperviousness_pct is None:
        return 35.0, "Imperviousness data unavailable"
    if imperviousness_pct >= 80:
        return 85.0, f"Highly impervious: {imperviousness_pct:.0f}% sealed surface"
    elif imperviousness_pct >= 60:
        return 65.0, f"Mostly impervious: {imperviousness_pct:.0f}% sealed surface"
    elif imperviousness_pct >= 40:
        return 45.0, f"Moderately impervious: {imperviousness_pct:.0f}% sealed surface"
    return 20.0, f"Permeable surface: {imperviousness_pct:.0f}% sealed"


def _historical_score(flood_count: int) -> tuple[float, str]:
    """Score based on historical waterlogging frequency."""
    if flood_count == 0:
        return 10.0, "No historical waterlogging records"
    elif flood_count <= 2:
        return 30.0, f"{flood_count} historical waterlogging event(s)"
    elif flood_count <= 5:
        return 55.0, f"{flood_count} historical waterlogging events"
    elif flood_count <= 10:
        return 75.0, f"{flood_count} historical waterlogging events — frequent"
    return 90.0, f"{flood_count} historical waterlogging events — very frequent"


def _score_to_category(score: float) -> str:
    """Convert a 0–100 score to a risk category."""
    if score >= 75:
        return "CRITICAL"
    elif score >= 55:
        return "HIGH"
    elif score >= 35:
        return "MODERATE"
    return "LOW"


def _assess_confidence(zone, warnings: list) -> str:
    """Determine confidence level based on data completeness."""
    missing = sum([
        zone.avg_elevation_m is None,
        zone.drainage_density is None,
        zone.imperviousness_pct is None,
    ])
    if missing >= 2 or zone.is_synthetic:
        return "LOW"
    elif missing == 1 or len(warnings) > 1:
        return "MEDIUM"
    return "HIGH"


def score_zone(zone) -> "RiskAssessment":
    """
    Compute a heuristic risk assessment for a zone.

    Fetches the most recent rainfall observation and forecast from the database,
    applies the heuristic scoring rules, and saves a new RiskAssessment.

    Returns the saved RiskAssessment object.
    """
    from zones.models import RiskAssessment
    from observations.models import RainfallObservation, RainfallForecast

    warnings = []
    if zone.is_synthetic:
        warnings.append("Zone attributes are synthetic demonstration data, not official measurements.")

    # Fetch latest rainfall observation
    latest_obs = (
        RainfallObservation.objects
        .filter(zone=zone)
        .order_by("-observed_at")
        .first()
    )

    # Check if observation is stale (> 3 hours)
    rainfall_1h = None
    rainfall_24h = None
    if latest_obs:
        obs_dt = latest_obs.observed_at if latest_obs.observed_at.tzinfo else latest_obs.observed_at.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - obs_dt
        if age > timedelta(hours=3):
            total_h = int(age.total_seconds() // 3600)
            total_m = int((age.total_seconds() % 3600) // 60)
            warnings.append(f"Most recent rainfall observation is {total_h}h {total_m}m old — ignored as stale.")
        elif latest_obs.quality_flag != "OK":
            warnings.append(
                f"Most recent rainfall observation is flagged {latest_obs.quality_flag} — ignored."
            )
        else:
            rainfall_1h = latest_obs.rainfall_1h_mm
            rainfall_24h = latest_obs.rainfall_24h_mm
    else:
        warnings.append("No rainfall observations available — rainfall component uses default estimate.")

    # Score the next six forecast hours from the most recent forecast run.
    forecast_now = datetime.now(timezone.utc)
    forecast_query = (
        RainfallForecast.objects
        .filter(zone=zone, forecast_for__gt=forecast_now)
    )
    latest_issue_at = forecast_query.order_by("-issued_at").values_list(
        "issued_at", flat=True
    ).first()
    forecast_6h = None
    if latest_issue_at is None:
        warnings.append("No rainfall forecast available — forecast component uses default estimate.")
    elif forecast_now - latest_issue_at > timedelta(hours=6):
        warnings.append("Most recent rainfall forecast is stale — forecast component uses default estimate.")
    else:
        forecast_hours = list(
            forecast_query.filter(issued_at=latest_issue_at)
            .order_by("forecast_for")[:6]
        )
        if len(forecast_hours) < 6:
            warnings.append(
                "Fewer than six forecast hours are available — forecast component uses default estimate."
            )
        else:
            forecast_6h = sum(item.rainfall_mm for item in forecast_hours)

    # Compute component scores
    rain_score, rain_desc = _rainfall_intensity_score(rainfall_1h, rainfall_24h)
    fcast_score, fcast_desc = _forecast_score(forecast_6h)
    elev_score, elev_desc = _elevation_score(zone.avg_elevation_m, zone.min_elevation_m)
    drain_score, drain_desc = _drainage_score(zone.drainage_density)
    imperv_score, imperv_desc = _imperviousness_score(zone.imperviousness_pct)
    hist_score, hist_desc = _historical_score(zone.historical_flood_count)

    # Weighted composite score
    composite = (
        WEIGHTS["rainfall_intensity"] * rain_score +
        WEIGHTS["forecast_rainfall"]  * fcast_score +
        WEIGHTS["elevation_risk"]     * elev_score +
        WEIGHTS["drainage_risk"]      * drain_score +
        WEIGHTS["imperviousness"]     * imperv_score +
        WEIGHTS["historical_risk"]    * hist_score
    )
    composite = round(min(max(composite, 0.0), 100.0), 2)
    category = _score_to_category(composite)
    confidence = _assess_confidence(zone, warnings)

    # Build contributing factors dict
    contributing_factors = {
        "rainfall_intensity": {
            "value": rain_score,
            "weight": WEIGHTS["rainfall_intensity"],
            "description": rain_desc,
            "component_contribution": round(WEIGHTS["rainfall_intensity"] * rain_score, 2),
        },
        "forecast_rainfall": {
            "value": fcast_score,
            "weight": WEIGHTS["forecast_rainfall"],
            "description": fcast_desc,
            "component_contribution": round(WEIGHTS["forecast_rainfall"] * fcast_score, 2),
        },
        "elevation_risk": {
            "value": elev_score,
            "weight": WEIGHTS["elevation_risk"],
            "description": elev_desc,
            "component_contribution": round(WEIGHTS["elevation_risk"] * elev_score, 2),
        },
        "drainage_infrastructure": {
            "value": drain_score,
            "weight": WEIGHTS["drainage_risk"],
            "description": drain_desc,
            "component_contribution": round(WEIGHTS["drainage_risk"] * drain_score, 2),
        },
        "impervious_surface": {
            "value": imperv_score,
            "weight": WEIGHTS["imperviousness"],
            "description": imperv_desc,
            "component_contribution": round(WEIGHTS["imperviousness"] * imperv_score, 2),
        },
        "historical_flood_frequency": {
            "value": hist_score,
            "weight": WEIGHTS["historical_risk"],
            "description": hist_desc,
            "component_contribution": round(WEIGHTS["historical_risk"] * hist_score, 2),
        },
    }

    # Save assessment
    assessment = RiskAssessment.objects.create(
        zone=zone,
        risk_score=composite,
        risk_category=category,
        score_method=RiskAssessment.SCORE_METHOD_HEURISTIC,
        model_version="heuristic-v1",
        is_ml_prediction=False,
        contributing_factors=contributing_factors,
        data_warnings=warnings,
        confidence_level=confidence,
        rainfall_1h_mm=rainfall_1h,
        rainfall_24h_mm=rainfall_24h,
        forecast_rainfall_6h_mm=forecast_6h,
        valid_for_hours=6,
    )

    logger.info(
        "Risk assessment: zone=%s score=%.1f category=%s confidence=%s",
        zone.code, composite, category, confidence
    )

    # Auto-generate intervention recommendation
    _create_or_update_intervention(zone, assessment)

    return assessment


def _create_or_update_intervention(zone, assessment):
    """Create or update an intervention recommendation for this assessment."""
    from interventions.models import InterventionRecommendation

    category = assessment.risk_category
    score = assessment.risk_score

    # Map category to urgency
    urgency_map = {
        "CRITICAL": InterventionRecommendation.URGENCY_CRITICAL,
        "HIGH": InterventionRecommendation.URGENCY_HIGH,
        "MODERATE": InterventionRecommendation.URGENCY_MEDIUM,
        "LOW": InterventionRecommendation.URGENCY_LOW,
        "UNKNOWN": InterventionRecommendation.URGENCY_LOW,
    }

    # Map category to action
    action_map = {
        "CRITICAL": InterventionRecommendation.ACTION_ESCALATE,
        "HIGH": InterventionRecommendation.ACTION_INSPECT,
        "MODERATE": InterventionRecommendation.ACTION_INSPECT,
        "LOW": InterventionRecommendation.ACTION_MONITOR,
        "UNKNOWN": InterventionRecommendation.ACTION_MONITOR,
    }

    # Build evidence list from contributing factors
    evidence = []
    for factor, detail in assessment.contributing_factors.items():
        if detail["component_contribution"] > 5:
            evidence.append({
                "type": "risk_factor",
                "description": factor.replace("_", " ").title(),
                "value": f"{detail['value']:.0f}/100 (contributes {detail['component_contribution']:.1f} pts)",
                "source": "DrainSense heuristic scorer v1",
            })

    reason = (
        f"Zone {zone.code} ({zone.name}) scored {score:.1f}/100 ({category} risk). "
        f"Top contributing factor: {_top_factor(assessment.contributing_factors)}. "
        f"Score method: {assessment.score_method}. "
        f"This is a heuristic estimate — not a validated ML prediction."
    )

    suggested_detail_map = {
        "CRITICAL": (
            f"Immediately escalate {zone.name} to senior drainage authority. "
            f"Deploy field inspection team to check drain outlets and low-lying road sections. "
            f"Issue public advisory if waterlogging risk to residential areas is confirmed."
        ),
        "HIGH": (
            f"Assign a drainage inspector to visit {zone.name} within 6 hours. "
            f"Check primary storm drains for blockages and confirm discharge capacity. "
            f"Verify current conditions before taking further action."
        ),
        "MODERATE": (
            f"Schedule inspection of {zone.name} within 24 hours. "
            f"Review last inspection report and check for reported blockages."
        ),
        "LOW": (
            f"Continue routine monitoring of {zone.name}. "
            f"No immediate action required based on current indicators."
        ),
    }

    suggested_action = suggested_detail_map.get(category, "Monitor situation.")

    # Compute priority score
    urgency_boost = {"CRITICAL": 1.3, "HIGH": 1.1, "MODERATE": 1.0, "LOW": 0.9, "UNKNOWN": 0.8}
    confidence_boost = {"HIGH": 1.1, "MEDIUM": 1.0, "LOW": 0.85}
    priority_score = (
        score
        * urgency_boost.get(category, 1.0)
        * confidence_boost.get(assessment.confidence_level, 1.0)
    )

    # Cancel existing pending interventions for this zone, create new one
    InterventionRecommendation.objects.filter(
        zone=zone,
        status=InterventionRecommendation.STATUS_PENDING,
    ).update(status=InterventionRecommendation.STATUS_CANCELLED)

    intervention = InterventionRecommendation.objects.create(
        zone=zone,
        risk_assessment=assessment,
        priority_rank=0,  # will be re-ranked globally below
        priority_score=round(priority_score, 2),
        action=action_map.get(category, InterventionRecommendation.ACTION_MONITOR),
        urgency=urgency_map.get(category, InterventionRecommendation.URGENCY_LOW),
        reason=reason,
        suggested_action_detail=suggested_action,
        supporting_evidence=evidence,
        status=InterventionRecommendation.STATUS_PENDING,
    )

    # Re-rank all pending interventions by priority_score
    _rerank_interventions()

    return intervention


def _rerank_interventions():
    """Re-compute priority_rank for all pending interventions."""
    from interventions.models import InterventionRecommendation
    pending = (
        InterventionRecommendation.objects
        .filter(status=InterventionRecommendation.STATUS_PENDING)
        .order_by("-priority_score")
    )
    for rank, item in enumerate(pending, start=1):
        InterventionRecommendation.objects.filter(pk=item.pk).update(priority_rank=rank)


def _top_factor(contributing_factors: dict) -> str:
    """Return the name of the highest-contributing factor."""
    if not contributing_factors:
        return "unknown"
    top = max(contributing_factors.items(), key=lambda x: x[1].get("component_contribution", 0))
    return top[0].replace("_", " ")
