"""Condition platform for the plant integration (Home Assistant 2026.7+).

Mirror of trigger.py: import-safe everywhere, returns {} on HA without the
2026.7 purpose-condition API.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

_CONDITIONS_CACHE: dict[str, type] | None = None


def _has_purpose_condition_api() -> bool:
    """True when the full HA 2026.7 purpose-condition helper API is importable.

    Checks the settled-2026.7 symbols, not just make_entity_state_condition
    (which also existed in the 2026.2-2026.6 Labs form without DomainSpec). Returns
    False on the 2025.8 floor, on the Labs-era API, and on any future HA where a
    required symbol has moved, so the platform stays inert instead of crashing
    discovery with an ImportError.
    """
    try:
        from homeassistant.helpers.automation import DomainSpec  # noqa: F401
        from homeassistant.helpers.condition import (  # noqa: F401
            make_entity_state_condition,
        )
    except ImportError:
        return False
    return True


async def async_get_conditions(hass: HomeAssistant) -> dict[str, type]:
    """Return the plant.* conditions, or {} on HA without the 2026.7 API."""
    global _CONDITIONS_CACHE
    if not _has_purpose_condition_api():
        return {}
    if _CONDITIONS_CACHE is None:
        try:
            from .condition_impl import build_conditions

            _CONDITIONS_CACHE = build_conditions()
        except ImportError as err:
            _LOGGER.debug("plant.* conditions unavailable on this HA version: %s", err)
            _CONDITIONS_CACHE = {}
    return _CONDITIONS_CACHE
