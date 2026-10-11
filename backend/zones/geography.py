"""Shared validation and queryset filtering for geographic API parameters."""

from django.db.models import Q
from rest_framework.exceptions import ValidationError

from .models import District, State


def _reference_query(model, raw_value):
    query = Q(code=raw_value)
    if raw_value.isdecimal():
        query |= Q(pk=int(raw_value))
    if model is State:
        query |= Q(lgd_code=raw_value)
    return query


def resolve_state(raw_value):
    try:
        return State.objects.get(_reference_query(State, raw_value), is_active=True)
    except State.DoesNotExist as exc:
        raise ValidationError({"state": f"Unknown or inactive state '{raw_value}'."}) from exc
    except State.MultipleObjectsReturned as exc:
        raise ValidationError({"state": "State identifier is ambiguous."}) from exc


def resolve_district(raw_value, state=None):
    query = _reference_query(District, raw_value) | Q(lgd_code=raw_value)
    districts = District.objects.filter(query, is_active=True)
    if state is not None:
        districts = districts.filter(state=state)
    try:
        return districts.get()
    except District.DoesNotExist as exc:
        message = (
            f"Unknown or inactive district '{raw_value}' for the selected state."
            if state else f"Unknown or inactive district '{raw_value}'."
        )
        raise ValidationError({"district": message}) from exc
    except District.MultipleObjectsReturned as exc:
        raise ValidationError(
            {"district": "District identifier is ambiguous; provide its state."}
        ) from exc


def apply_geographic_filters(queryset, params, related_prefix=""):
    """Filter records whose location relation is `related_prefix + district`."""
    raw_state = params.get("state")
    raw_district = params.get("district")
    if not raw_state and not raw_district:
        return queryset

    state = resolve_state(raw_state) if raw_state else None
    if state is not None:
        queryset = queryset.filter(
            **{f"{related_prefix}district__state": state}
        )
    if raw_district:
        district = resolve_district(raw_district, state=state)
        queryset = queryset.filter(**{f"{related_prefix}district": district})
    return queryset


def filter_by_zone_id(queryset, raw_value, lookup="pk"):
    """Validate and apply a zone identifier within an already-scoped queryset."""
    if not str(raw_value).isdecimal():
        raise ValidationError({"zone": f"Invalid zone identifier '{raw_value}'."})
    filtered = queryset.filter(**{lookup: int(raw_value)})
    if not filtered.exists():
        raise ValidationError({
            "zone": f"Unknown zone '{raw_value}' for the selected geography."
        })
    return filtered
