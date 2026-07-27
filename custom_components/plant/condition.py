"""Condition platform for the plant integration (Home Assistant 2026.7+).

Mirror of trigger.py: import-safe everywhere, returns {} on HA without the
2026.7 purpose-condition API.
"""

from __future__ import annotations

import homeassistant.helpers.condition as ha_condition
from homeassistant.core import HomeAssistant

_CONDITIONS_CACHE: dict[str, type] | None = None


def _has_purpose_condition_api() -> bool:
    """True when the HA 2026.7 purpose-condition helper API is available."""
    return hasattr(ha_condition, "make_entity_state_condition")


async def async_get_conditions(hass: HomeAssistant) -> dict[str, type]:
    """Return the plant.* conditions, or {} on HA without the 2026.7 API."""
    global _CONDITIONS_CACHE
    if not _has_purpose_condition_api():
        return {}
    if _CONDITIONS_CACHE is None:
        from .condition_impl import build_conditions

        _CONDITIONS_CACHE = build_conditions()
    return _CONDITIONS_CACHE
