"""Tests for the plant.* condition surface (HA 2026.7+)."""

from __future__ import annotations

import pytest
from homeassistant.const import __version__ as HA_VERSION

_p = HA_VERSION.split(".")
if (int(_p[0]), int(_p[1])) < (2026, 7):
    pytest.skip(
        "plant conditions require the HA 2026.7+ platform",
        allow_module_level=True,
    )

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_capture_events


async def _condition_passes(hass: HomeAssistant, cond: dict) -> bool:
    events = async_capture_events(hass, "cond_passed")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "trigger": {"platform": "event", "event_type": "probe"},
                "condition": cond,
                "action": {"event": "cond_passed"},
            }
        },
    )
    await hass.async_block_till_done()
    await hass.services.async_call(
        "automation",
        "trigger",
        {"entity_id": "automation.automation_0", "skip_condition": False},
        blocking=True,
    )
    await hass.async_block_till_done()
    return len(events) == 1


@pytest.mark.parametrize(("state", "expected"), [("problem", True), ("ok", False)])
async def test_has_problem(hass: HomeAssistant, state: str, expected: bool) -> None:
    hass.states.async_set("plant.test", state)
    await hass.async_block_till_done()
    got = await _condition_passes(
        hass, {"condition": "plant.has_problem", "target": {"entity_id": "plant.test"}}
    )
    assert got is expected


@pytest.mark.parametrize(
    ("status", "expected"), [("Low", True), ("High", False), ("ok", False)]
)
async def test_moisture_is_low(
    hass: HomeAssistant, status: str, expected: bool
) -> None:
    hass.states.async_set("plant.test", "problem", {"moisture_status": status})
    await hass.async_block_till_done()
    got = await _condition_passes(
        hass,
        {"condition": "plant.moisture_is_low", "target": {"entity_id": "plant.test"}},
    )
    assert got is expected
