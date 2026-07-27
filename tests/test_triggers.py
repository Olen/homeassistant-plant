"""Tests for the plant trigger/condition platforms (HA 2026.7+ prototype)."""

from __future__ import annotations

import pytest
from homeassistant.const import __version__ as HA_VERSION

# The trigger/condition platform settled into its current shape in HA 2026.7; an
# earlier Labs form existed in 2026.2-2026.6 with a different API. The integration
# still supports 2025.8+, and the platform files are never imported on older cores,
# so skip the whole module below 2026.7 rather than fail at collection/runtime.
_ha_parts = HA_VERSION.split(".")
if (int(_ha_parts[0]), int(_ha_parts[1])) < (2026, 7):
    pytest.skip(
        "plant triggers require the HA 2026.7+ trigger platform",
        allow_module_level=True,
    )

from homeassistant.core import HomeAssistant

from custom_components.plant.automation_meta import (
    EXTERNAL_MEASUREMENTS,
    STATUS_MEASUREMENTS,
)
from custom_components.plant.condition import async_get_conditions
from custom_components.plant.trigger import async_get_triggers


def _expected_trigger_keys() -> set[str]:
    keys = {"problem_detected", "problem_cleared"}
    for m in STATUS_MEASUREMENTS:
        keys |= {f"{m.key}_became_low", f"{m.key}_became_high", f"{m.key}_became_ok"}
    for m in EXTERNAL_MEASUREMENTS:
        keys |= {f"{m.key}_sensor_became_stale", f"{m.key}_sensor_became_fresh"}
    return keys


def _expected_condition_keys() -> set[str]:
    keys = {"has_problem"}
    for m in STATUS_MEASUREMENTS:
        keys |= {f"{m.key}_is_low", f"{m.key}_is_high", f"{m.key}_is_ok"}
    for m in EXTERNAL_MEASUREMENTS:
        keys |= {f"{m.key}_sensor_is_stale"}
    return keys


async def test_async_get_triggers_full_surface(hass: HomeAssistant) -> None:
    assert set(await async_get_triggers(hass)) == _expected_trigger_keys()
    assert len(_expected_trigger_keys()) == 43


async def test_async_get_conditions_full_surface(hass: HomeAssistant) -> None:
    assert set(await async_get_conditions(hass)) == _expected_condition_keys()
    assert len(_expected_condition_keys()) == 35
