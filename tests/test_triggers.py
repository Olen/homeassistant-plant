"""Tests for the plant trigger/condition platforms (HA 2026.7+ prototype)."""

from __future__ import annotations

from datetime import timedelta

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

import homeassistant.util.dt as dt_util
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.plant.condition import async_get_conditions
from custom_components.plant.trigger import async_get_triggers


async def test_async_get_triggers(hass: HomeAssistant) -> None:
    """The platform advertises the expected trigger keys."""
    triggers = await async_get_triggers(hass)
    assert set(triggers) == {
        "became_problem",
        "became_ok",
        "moisture_became_low",
        "moisture_became_high",
        "sensor_became_stale",
    }


async def test_async_get_conditions(hass: HomeAssistant) -> None:
    """The platform advertises the expected condition keys."""
    conditions = await async_get_conditions(hass)
    assert set(conditions) == {"is_problem", "moisture_is_low", "sensor_is_stale"}


async def test_became_problem_fires(hass: HomeAssistant) -> None:
    """plant.became_problem fires when the plant transitions ok -> problem."""
    hass.states.async_set("plant.test", "ok")
    await hass.async_block_till_done()

    events = async_capture_events(hass, "plant_problem")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "trigger": {
                    "trigger": "plant.became_problem",
                    "target": {"entity_id": "plant.test"},
                },
                "action": {"event": "plant_problem"},
            }
        },
    )
    await hass.async_block_till_done()

    hass.states.async_set("plant.test", "problem")
    await hass.async_block_till_done()
    assert len(events) == 1


async def test_moisture_became_low_uses_status_attribute(hass: HomeAssistant) -> None:
    """plant.moisture_became_low fires off the plant's own moisture_status (no threshold)."""
    hass.states.async_set("plant.test", "ok", {"moisture_status": "ok"})
    await hass.async_block_till_done()

    events = async_capture_events(hass, "moisture_low")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "trigger": {
                    "trigger": "plant.moisture_became_low",
                    "target": {"entity_id": "plant.test"},
                },
                "action": {"event": "moisture_low"},
            }
        },
    )
    await hass.async_block_till_done()

    hass.states.async_set("plant.test", "problem", {"moisture_status": "Low"})
    await hass.async_block_till_done()
    assert len(events) == 1


async def test_sensor_became_stale_on_no_update(hass: HomeAssistant) -> None:
    """plant.sensor_became_stale fires when a targeted sensor goes silent for `for`."""
    hass.states.async_set("sensor.test_moisture", "20")
    await hass.async_block_till_done()

    events = async_capture_events(hass, "sensor_stale")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "trigger": {
                    "trigger": "plant.sensor_became_stale",
                    "target": {"entity_id": "sensor.test_moisture"},
                    "options": {"for": {"seconds": 30}},
                },
                "action": {
                    "event": "sensor_stale",
                    "event_data": {"reason": "{{ trigger.reason }}"},
                },
            }
        },
    )
    await hass.async_block_till_done()

    # No update within the window -> stale.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()
    assert len(events) == 1
    assert events[0].data["reason"] == "no_update"


async def test_sensor_became_stale_on_unavailable(hass: HomeAssistant) -> None:
    """plant.sensor_became_stale fires immediately when a sensor goes unavailable."""
    hass.states.async_set("sensor.test_moisture", "20")
    await hass.async_block_till_done()

    events = async_capture_events(hass, "sensor_stale")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "trigger": {
                    "trigger": "plant.sensor_became_stale",
                    "target": {"entity_id": "sensor.test_moisture"},
                    "options": {"for": {"hours": 24}},
                },
                "action": {
                    "event": "sensor_stale",
                    "event_data": {"reason": "{{ trigger.reason }}"},
                },
            }
        },
    )
    await hass.async_block_till_done()

    hass.states.async_set("sensor.test_moisture", "unavailable")
    await hass.async_block_till_done()
    assert len(events) == 1
    assert events[0].data["reason"] == "unavailable"


@pytest.mark.parametrize(
    ("plant_state", "expected"),
    [("problem", True), ("ok", False)],
)
async def test_is_problem_condition(
    hass: HomeAssistant, plant_state: str, expected: bool
) -> None:
    """plant.is_problem reflects the plant's current state."""
    hass.states.async_set("plant.test", plant_state)
    await hass.async_block_till_done()

    events = async_capture_events(hass, "cond_passed")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "trigger": {"platform": "event", "event_type": "plant_cond_probe"},
                "condition": {
                    "condition": "plant.is_problem",
                    "target": {"entity_id": "plant.test"},
                },
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
    assert (len(events) == 1) is expected
