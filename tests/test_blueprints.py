"""Tests for the shipped automation blueprints (HA 2026.7+)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from custom_components.plant.trigger import _has_purpose_trigger_api

if not _has_purpose_trigger_api():
    pytest.skip(
        "plant purpose-trigger API not available on this HA",
        allow_module_level=True,
    )

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.plant.const import ATTR_PLANT, DOMAIN as PLANT_DOMAIN

from .common import set_external_sensor_states, update_plant_sensors
from .ha_common import async_capture_events

BLUEPRINTS = Path(__file__).parent.parent / "blueprints" / "automation" / "plant"


@pytest.fixture
def installed_blueprints(hass: HomeAssistant):
    """Copy the blueprints to where Home Assistant looks for them."""
    target = Path(hass.config.path("blueprints", "automation", "plant"))
    shutil.copytree(BLUEPRINTS, target, dirs_exist_ok=True)
    yield
    shutil.rmtree(target)


def _event_action(event_type: str, data: dict[str, str]) -> list[dict]:
    return [{"event": event_type, "event_data": data}]


async def _use_blueprint(hass: HomeAssistant, path: str, inputs: dict) -> None:
    assert await async_setup_component(
        hass,
        "automation",
        {"automation": {"use_blueprint": {"path": f"plant/{path}", "input": inputs}}},
    )
    await hass.async_block_till_done()


async def _set_moisture(hass: HomeAssistant, entry, moisture: float) -> None:
    """Feed a moisture reading through the plant and publish the plant's state."""
    await set_external_sensor_states(hass, moisture=moisture)
    await update_plant_sensors(hass, entry.entry_id)
    hass.data[PLANT_DOMAIN][entry.entry_id][ATTR_PLANT].async_write_ha_state()
    await hass.async_block_till_done()


async def _turn_off_automations(hass: HomeAssistant) -> None:
    """Detach the triggers, so their freshness timers do not outlive the test."""
    await hass.services.async_call(
        "automation", "turn_off", {"entity_id": "all"}, blocking=True
    )
    await hass.async_block_till_done()


def _plant_entity_id(hass: HomeAssistant, entry) -> str:
    return hass.data[PLANT_DOMAIN][entry.entry_id][ATTR_PLANT].entity_id


async def test_plant_problem_names_the_problems(
    hass: HomeAssistant, installed_blueprints
) -> None:
    hass.states.async_set("plant.fern", "ok", {"friendly_name": "Fern"})
    await hass.async_block_till_done()
    problems = async_capture_events(hass, "problem")
    cleared = async_capture_events(hass, "cleared")
    await _use_blueprint(
        hass,
        "plant_problem.yaml",
        {
            "plants": {"entity_id": "plant.fern"},
            "problem_actions": _event_action(
                "problem", {"name": "{{ plant_name }}", "problems": "{{ problems }}"}
            ),
            "cleared_actions": _event_action("cleared", {"name": "{{ plant_name }}"}),
        },
    )
    hass.states.async_set(
        "plant.fern",
        "problem",
        {
            "friendly_name": "Fern",
            "problems": [
                {"sensor_type": "moisture", "status": "Low"},
                {"sensor_type": "illuminance", "status": "High"},
            ],
        },
    )
    await hass.async_block_till_done()
    assert len(problems) == 1
    assert problems[0].data == {
        "name": "Fern",
        "problems": "moisture low, illuminance high",
    }

    hass.states.async_set("plant.fern", "ok", {"friendly_name": "Fern"})
    await hass.async_block_till_done()
    assert [e.data for e in cleared] == [{"name": "Fern"}]


async def test_plant_sensor_stale_names_sensor_and_plants(
    hass: HomeAssistant, init_integration, installed_blueprints
) -> None:
    plant_id = _plant_entity_id(hass, init_integration)
    stale = async_capture_events(hass, "stale")
    fresh = async_capture_events(hass, "fresh")
    await _use_blueprint(
        hass,
        "plant_sensor_stale.yaml",
        {
            "plants": {"entity_id": plant_id},
            "stale_actions": _event_action(
                "stale",
                {
                    "sensor": "{{ sensor }}",
                    "measurement": "{{ measurement }}",
                    "plants": "{{ plant_names }}",
                    "reason": "{{ reason }}",
                },
            ),
            "fresh_actions": _event_action("fresh", {"sensor": "{{ sensor }}"}),
        },
    )
    hass.states.async_set("sensor.test_soil_temperature", "unavailable")
    await hass.async_block_till_done()
    assert len(stale) == 1
    assert stale[0].data == {
        "sensor": "sensor.test_soil_temperature",
        "measurement": "soil temperature",
        "plants": hass.states.get(plant_id).attributes["friendly_name"],
        "reason": "unavailable",
    }

    hass.states.async_set("sensor.test_soil_temperature", "18")
    await hass.async_block_till_done()
    assert [e.data for e in fresh] == [{"sensor": "sensor.test_soil_temperature"}]
    await _turn_off_automations(hass)


async def test_plant_needs_water_reports_the_reading(
    hass: HomeAssistant, init_integration, installed_blueprints
) -> None:
    plant_id = _plant_entity_id(hass, init_integration)
    await _set_moisture(hass, init_integration, 40.0)
    events = async_capture_events(hass, "water")
    await _use_blueprint(
        hass,
        "plant_needs_water.yaml",
        {
            "plants": {"entity_id": plant_id},
            "water_actions": _event_action(
                "water", {"name": "{{ plant_name }}", "moisture": "{{ moisture }}"}
            ),
        },
    )
    await _set_moisture(hass, init_integration, 5.0)
    assert len(events) == 1
    assert (
        events[0].data["name"] == hass.states.get(plant_id).attributes["friendly_name"]
    )
    assert float(events[0].data["moisture"]) == 5
