"""
DrainSense AI — AWS Strands Agents SDK integration

This module uses the AWS Strands Agents SDK (open-source, backed by AWS Bedrock)
to generate evidence-based explanations for waterlogging risk assessments.

The agent:
 - receives structured, validated zone data (no free-form unvalidated input)
 - explains the contributing risk factors
 - recommends a specific action and urgency
 - identifies missing data and limitations
 - requires human verification for consequential actions
 - has a deterministic fallback when unavailable

The agent does NOT fabricate risk scores, sensor readings, or model metrics.
It explains an existing, pre-computed risk assessment.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("drainsense")

# Strands imports — graceful fallback if SDK unavailable
try:
    from strands import Agent
    from strands.models import BedrockModel
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False
    logger.warning("strands-agents SDK not available. Agent will use fallback mode.")


SYSTEM_PROMPT = """You are DrainSense AI, an environmental decision-support assistant 
for municipal drainage inspectors in Coimbatore, Tamil Nadu, India.

Your role is to explain waterlogging risk assessments clearly and actionably.

Rules you must follow:
1. Only use the structured data provided in each request. Never invent sensor readings, 
   rainfall values, flood reports, or model metrics.
2. When data is missing or uncertain, say so explicitly.
3. Risk scores are heuristic estimates (0-100 scale), NOT probability percentages. 
   Do not describe a score of 70 as "70% probability of flooding".
4. Always recommend human field verification before consequential actions.
5. Keep explanations concise and specific to the provided zone data.
6. If asked about anything outside drainage risk assessment, redirect to your core purpose.

Output format:
Return valid JSON with these exact keys:
- risk_summary: 2-3 sentences explaining the overall risk level
- contributing_factors: list of dicts with {factor, value, significance, explanation}
- data_limitations: list of strings noting missing or uncertain data  
- recommended_action: specific action for the field inspector
- urgency: one of LOW/MEDIUM/HIGH/CRITICAL
- human_verification_required: boolean (true for HIGH/CRITICAL urgency)
- confidence: one of LOW/MEDIUM/HIGH
"""


def _build_zone_context(intervention) -> dict:
    """
    Build structured, validated context from an intervention recommendation.
    Returns only data that exists in the database — no fabrication.
    """
    zone = intervention.zone
    assessment = intervention.risk_assessment

    context = {
        "zone": {
            "code": zone.code,
            "name": zone.name,
            "latitude": zone.latitude,
            "longitude": zone.longitude,
            "avg_elevation_m": zone.avg_elevation_m,
            "min_elevation_m": zone.min_elevation_m,
            "drainage_density": zone.drainage_density,
            "imperviousness_pct": zone.imperviousness_pct,
            "historical_flood_count": zone.historical_flood_count,
            "last_flood_date": str(zone.last_flood_date) if zone.last_flood_date else None,
            "data_source": zone.data_source,
            "is_synthetic": zone.is_synthetic,
        },
        "intervention": {
            "priority_rank": intervention.priority_rank,
            "action": intervention.action,
            "urgency": intervention.urgency,
            "reason": intervention.reason,
            "supporting_evidence": intervention.supporting_evidence,
        },
    }

    if assessment:
        context["risk_assessment"] = {
            "risk_score": round(assessment.risk_score, 1),
            "risk_category": assessment.risk_category,
            "score_method": assessment.score_method,
            "model_version": assessment.model_version,
            "confidence_level": assessment.confidence_level,
            "rainfall_1h_mm": assessment.rainfall_1h_mm,
            "rainfall_24h_mm": assessment.rainfall_24h_mm,
            "forecast_rainfall_6h_mm": assessment.forecast_rainfall_6h_mm,
            "contributing_factors": assessment.contributing_factors,
            "data_warnings": assessment.data_warnings,
            "assessed_at": assessment.assessed_at.isoformat(),
        }
    else:
        context["risk_assessment"] = None

    return context


def _fallback_explanation(intervention, error_reason: str = "") -> dict:
    """
    Deterministic fallback explanation when the agent is unavailable.
    Uses structured data from the database — no fabrication.
    """
    zone = intervention.zone
    assessment = intervention.risk_assessment

    score = assessment.risk_score if assessment else None
    category = assessment.risk_category if assessment else "UNKNOWN"
    warnings = assessment.data_warnings if assessment else []

    factors = []
    if assessment and assessment.contributing_factors:
        for name, detail in assessment.contributing_factors.items():
            factors.append({
                "factor": name,
                "value": detail.get("value"),
                "significance": detail.get("weight", "unknown"),
                "explanation": detail.get("description", ""),
            })

    return {
        "risk_summary": (
            f"Zone {zone.code} ({zone.name}) has been assessed as {category} risk "
            f"with a heuristic score of {score:.1f}/100. "
            f"This is a rule-based estimate, not a validated ML prediction."
            if score is not None else
            f"Zone {zone.code} ({zone.name}) risk category: {category}. No score available."
        ),
        "contributing_factors": factors,
        "data_limitations": warnings or ["Agent explanation not available — using fallback."],
        "recommended_action": intervention.suggested_action_detail or intervention.get_action_display(),
        "urgency": intervention.urgency,
        "human_verification_required": intervention.urgency in ("HIGH", "CRITICAL"),
        "confidence": assessment.confidence_level if assessment else "LOW",
        "agent_available": False,
        "fallback_reason": error_reason or "AWS Strands agent unavailable",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def explain_intervention(intervention) -> dict:
    """
    Use the AWS Strands agent to explain a risk assessment for an intervention.

    Falls back to a deterministic structured explanation if:
    - The agent SDK is not available
    - AWS credentials are not configured
    - The agent call fails or times out

    Never exposes credentials. Never fabricates data.
    """
    # Check SDK availability
    if not STRANDS_AVAILABLE:
        result = _fallback_explanation(intervention, "strands-agents SDK not installed")
        _save_agent_result(intervention, result, error="SDK not available")
        return result

    # Check AWS credentials present (don't validate — just check non-empty)
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID", "")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    if not aws_key or not aws_secret:
        result = _fallback_explanation(
            intervention,
            "AWS credentials not configured. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env"
        )
        _save_agent_result(intervention, result, error="No AWS credentials")
        return result

    # Build the structured prompt
    zone_context = _build_zone_context(intervention)
    user_message = (
        f"Explain the waterlogging risk for this zone and provide a specific intervention recommendation.\n\n"
        f"Zone data:\n{json.dumps(zone_context, indent=2, default=str)}\n\n"
        f"Return your response as valid JSON only, following the output format in your system prompt."
    )

    try:
        model = BedrockModel(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        )
        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
        )

        logger.info("Calling Strands agent for zone %s", intervention.zone.code)
        response = agent(user_message)

        # Extract text from response
        response_text = str(response)

        # Parse JSON from response
        result = _parse_agent_json(response_text)
        result["agent_available"] = True
        result["generated_at"] = datetime.now(timezone.utc).isoformat()
        result["model_used"] = "claude-3-5-haiku via AWS Bedrock (Strands SDK)"

        _save_agent_result(intervention, result)
        return result

    except Exception as exc:
        logger.error("Strands agent call failed: %s", exc)
        result = _fallback_explanation(intervention, str(exc))
        _save_agent_result(intervention, result, error=str(exc))
        return result


def _parse_agent_json(response_text: str) -> dict:
    """Extract and parse JSON from agent response text."""
    import re
    # Try to find JSON block
    json_match = re.search(r'\{[\s\S]+\}', response_text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    # Return raw text wrapped in a result dict if JSON parsing fails
    return {
        "risk_summary": response_text[:500] if response_text else "No response from agent.",
        "contributing_factors": [],
        "data_limitations": ["Agent returned non-JSON response."],
        "recommended_action": "Review manually.",
        "urgency": "MEDIUM",
        "human_verification_required": True,
        "confidence": "LOW",
    }


def _save_agent_result(intervention, result: dict, error: str = "") -> None:
    """Persist agent result back to the intervention record."""
    try:
        from django.utils import timezone as dj_timezone
        intervention.agent_explanation = json.dumps(result, default=str)
        intervention.agent_ran_at = dj_timezone.now()
        if error:
            intervention.agent_error = error[:500]
        intervention.save(update_fields=["agent_explanation", "agent_ran_at", "agent_error"])
    except Exception as exc:
        logger.warning("Could not save agent result to DB: %s", exc)
