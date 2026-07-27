"""Trigger platform for the plant integration (Home Assistant 2026.7+).

Exposes purpose-specific ``plant.*`` triggers built on the integration's
species-threshold-aware status. Import-safe on every supported HA version: the
2026.7-only helper API is imported lazily and only when present, so on HA
2025.8-2026.6 async_get_triggers returns {} and nothing is registered.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

_TRIGGERS_CACHE: dict[str, type] | None = None


def _has_purpose_trigger_api() -> bool:
    """True when the full HA 2026.7 purpose-trigger helper API is importable.

    Checks the settled-2026.7 symbols, not just make_entity_target_state_trigger
    (which also existed in the 2026.2-2026.6 Labs form without DomainSpec). Returns
    False on the 2025.8 floor, on the Labs-era API, and on any future HA where a
    required symbol has moved, so the platform stays inert instead of crashing
    discovery with an ImportError.
    """
    try:
        from homeassistant.helpers.automation import DomainSpec  # noqa: F401
        from homeassistant.helpers.trigger import (  # noqa: F401
            make_entity_target_state_trigger,
        )
    except ImportError:
        return False
    return True


async def async_get_triggers(hass: HomeAssistant) -> dict[str, type]:
    """Return the plant.* triggers, or {} on HA without the 2026.7 API."""
    global _TRIGGERS_CACHE
    if not _has_purpose_trigger_api():
        return {}
    if _TRIGGERS_CACHE is None:
        try:
            from .trigger_impl import build_triggers

            _TRIGGERS_CACHE = build_triggers()
        except ImportError as err:
            _LOGGER.debug("plant.* triggers unavailable on this HA version: %s", err)
            _TRIGGERS_CACHE = {}
    return _TRIGGERS_CACHE
