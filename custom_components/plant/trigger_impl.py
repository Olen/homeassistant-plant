"""2026.7-only trigger construction. Imported lazily by trigger.py."""

from __future__ import annotations

from homeassistant.const import STATE_OK, STATE_PROBLEM
from homeassistant.helpers.automation import DomainSpec
from homeassistant.helpers.trigger import make_entity_target_state_trigger

from .automation_meta import EXTERNAL_MEASUREMENTS, STATUS_MEASUREMENTS
from .const import DOMAIN, STATE_HIGH, STATE_LOW
from .stale import make_stale_trigger

# transition-name suffix -> plant <m>_status value it maps to
_STATUS_TRANSITIONS = {
    "became_low": STATE_LOW,
    "became_high": STATE_HIGH,
    "became_ok": STATE_OK,
}


def build_triggers() -> dict[str, type]:
    """Assemble the plant.* trigger surface (aggregate + per-measurement status)."""
    triggers: dict[str, type] = {
        # Aggregate plant health (entity state).
        "problem_detected": make_entity_target_state_trigger(DOMAIN, STATE_PROBLEM),
        "problem_cleared": make_entity_target_state_trigger(DOMAIN, STATE_OK),
    }
    # Per-measurement status, auto-thresholded off the plant's own <m>_status.
    for m in STATUS_MEASUREMENTS:
        for suffix, to_state in _STATUS_TRANSITIONS.items():
            triggers[f"{m.key}_{suffix}"] = make_entity_target_state_trigger(
                {DOMAIN: DomainSpec(value_source=m.status_attr)},
                to_state,
            )
    # Per-measurement source-sensor staleness (external measurements only).
    for m in EXTERNAL_MEASUREMENTS:
        triggers[f"{m.key}_sensor_became_stale"] = make_stale_trigger(m, fresh=False)
        triggers[f"{m.key}_sensor_became_fresh"] = make_stale_trigger(m, fresh=True)
    return triggers
