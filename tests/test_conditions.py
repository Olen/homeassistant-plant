"""Tests for the plant.* condition surface (HA 2026.7+)."""

from __future__ import annotations

import pytest

from custom_components.plant.condition import _has_purpose_condition_api

if not _has_purpose_condition_api():
    pytest.skip(
        "plant purpose-condition API not available on this HA",
        allow_module_level=True,
    )

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.plant.const import ATTR_PLANT, DOMAIN as PLANT_DOMAIN
from custom_components.plant.stale import resolve_external_sensor


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


def _plant_entity_id(hass, init_integration) -> str:
    return hass.data[PLANT_DOMAIN][init_integration.entry_id][ATTR_PLANT].entity_id


async def test_moisture_sensor_is_stale_when_unavailable(
    hass: HomeAssistant, init_integration
) -> None:
    plant_id = _plant_entity_id(hass, init_integration)
    hass.states.async_set("sensor.test_moisture", "unavailable")
    await hass.async_block_till_done()
    got = await _condition_passes(
        hass,
        {
            "condition": "plant.moisture_sensor_is_stale",
            "target": {"entity_id": plant_id},
        },
    )
    assert got is True


async def test_moisture_sensor_is_stale_false_when_fresh(
    hass: HomeAssistant, init_integration
) -> None:
    plant_id = _plant_entity_id(hass, init_integration)
    hass.states.async_set("sensor.test_moisture", "42")
    await hass.async_block_till_done()
    got = await _condition_passes(
        hass,
        {
            "condition": "plant.moisture_sensor_is_stale",
            "target": {"entity_id": plant_id},
        },
    )
    assert got is False


async def test_stale_resolution_follows_replace_sensor(
    hass: HomeAssistant, init_integration
) -> None:
    """resolve_external_sensor and the stale condition must track a sensor swap.

    replace_external_sensor updates PlantDevice.sensor_moisture.external_sensor
    in place; resolve_external_sensor reads that attribute live, and the stale
    CONDITION (unlike the trigger, which only re-binds on reload) re-resolves
    the source on every evaluation. So both must follow a replace_sensor swap
    without any reload.
    """
    plant_id = _plant_entity_id(hass, init_integration)
    plant = hass.data[PLANT_DOMAIN][init_integration.entry_id][ATTR_PLANT]

    assert (
        resolve_external_sensor(hass, plant_id, "sensor_moisture")
        == "sensor.test_moisture"
    )

    hass.states.async_set("sensor.new_moisture", "42")
    await hass.async_block_till_done()
    plant.sensor_moisture.replace_external_sensor("sensor.new_moisture")
    await hass.async_block_till_done()

    assert (
        resolve_external_sensor(hass, plant_id, "sensor_moisture")
        == "sensor.new_moisture"
    )

    # Old source going stale must no longer matter; new source drives the result.
    hass.states.async_set("sensor.test_moisture", "unavailable")
    hass.states.async_set("sensor.new_moisture", "unavailable")
    await hass.async_block_till_done()
    got = await _condition_passes(
        hass,
        {
            "condition": "plant.moisture_sensor_is_stale",
            "target": {"entity_id": plant_id},
        },
    )
    assert got is True

    hass.states.async_set("sensor.test_moisture", "unavailable")
    hass.states.async_set("sensor.new_moisture", "42")
    await hass.async_block_till_done()
    got = await _condition_passes(
        hass,
        {
            "condition": "plant.moisture_sensor_is_stale",
            "target": {"entity_id": plant_id},
        },
    )
    assert got is False
