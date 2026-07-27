"""Trigger platform for the plant integration (Home Assistant 2026.7+).

Exposes purpose-specific ``plant.*`` triggers built on the integration's
species-threshold-aware status. Import-safe on every supported HA version: the
2026.7-only helper API is imported lazily and only when present, so on HA
2025.8-2026.6 async_get_triggers returns {} and nothing is registered.
"""

from __future__ import annotations

import homeassistant.helpers.trigger as ha_trigger
from homeassistant.core import HomeAssistant

_TRIGGERS_CACHE: dict[str, type] | None = None


def _has_purpose_trigger_api() -> bool:
    """True when the HA 2026.7 purpose-trigger helper API is available."""
    return hasattr(ha_trigger, "make_entity_target_state_trigger")


async def async_get_triggers(hass: HomeAssistant) -> dict[str, type]:
    """Return the plant.* triggers, or {} on HA without the 2026.7 API."""
    global _TRIGGERS_CACHE
    if not _has_purpose_trigger_api():
        return {}
    if _TRIGGERS_CACHE is None:
        from .trigger_impl import build_triggers

        _TRIGGERS_CACHE = build_triggers()
    return _TRIGGERS_CACHE
