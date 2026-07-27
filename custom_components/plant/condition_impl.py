"""2026.7-only condition construction. Imported lazily by condition.py."""

from __future__ import annotations

from homeassistant.const import STATE_OK, STATE_PROBLEM
from homeassistant.helpers.automation import DomainSpec
from homeassistant.helpers.condition import make_entity_state_condition

from .automation_meta import STATUS_MEASUREMENTS
from .const import DOMAIN, STATE_HIGH, STATE_LOW

_STATUS_CONDITIONS = {
    "is_low": STATE_LOW,
    "is_high": STATE_HIGH,
    "is_ok": STATE_OK,
}


def build_conditions() -> dict[str, type]:
    """Assemble the plant.* condition surface (aggregate + per-measurement status)."""
    conditions: dict[str, type] = {
        "has_problem": make_entity_state_condition(DOMAIN, STATE_PROBLEM),
    }
    for m in STATUS_MEASUREMENTS:
        for suffix, state in _STATUS_CONDITIONS.items():
            conditions[f"{m.key}_{suffix}"] = make_entity_state_condition(
                {DOMAIN: DomainSpec(value_source=m.status_attr)},
                state,
            )
    return conditions
