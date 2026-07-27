"""Tests for the plant trigger/condition platforms (HA 2026.7+ prototype)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from custom_components.plant.trigger import _has_purpose_trigger_api

# The trigger/condition platform settled into its current shape in HA 2026.7; an
# earlier Labs form existed in 2026.2-2026.6 with a different API. The integration
# still supports 2025.8+, and the platform files are never imported on older cores,
# so skip the whole module unless the full purpose-trigger API is importable
# (capability-based, not a version-string check).
if not _has_purpose_trigger_api():
    pytest.skip(
        "plant purpose-trigger API not available on this HA",
        allow_module_level=True,
    )

import homeassistant.util.dt as dt_util
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.plant.automation_meta import (
    EXTERNAL_MEASUREMENTS,
    STATUS_MEASUREMENTS,
)
from custom_components.plant.condition import async_get_conditions
from custom_components.plant.const import ATTR_PLANT, DOMAIN as PLANT_DOMAIN
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


async def test_problem_detected_fires(hass: HomeAssistant) -> None:
    hass.states.async_set("plant.test", "ok")
    await hass.async_block_till_done()
    events = async_capture_events(hass, "plant_problem")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "trigger": {
                    "trigger": "plant.problem_detected",
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


async def test_moisture_became_ok_fires_on_recovery(hass: HomeAssistant) -> None:
    hass.states.async_set("plant.test", "problem", {"moisture_status": "Low"})
    await hass.async_block_till_done()
    events = async_capture_events(hass, "moisture_ok")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "trigger": {
                    "trigger": "plant.moisture_became_ok",
                    "target": {"entity_id": "plant.test"},
                },
                "action": {"event": "moisture_ok"},
            }
        },
    )
    await hass.async_block_till_done()
    hass.states.async_set("plant.test", "ok", {"moisture_status": "ok"})
    await hass.async_block_till_done()
    assert len(events) == 1


def _plant_entity_id(hass, init_integration) -> str:
    return hass.data[PLANT_DOMAIN][init_integration.entry_id][ATTR_PLANT].entity_id


async def test_moisture_sensor_no_spurious_stale_when_recovers_in_window(
    hass: HomeAssistant, init_integration
) -> None:
    """A source already stale at attach that recovers within `for` must NOT fire.

    This is the restart case: the integration hasn't populated the sensor yet, so
    it reads unknown/unavailable at attach. The grace-period state machine holds it
    as `pending` (not stale) and cancels the grace timer on recovery.
    """
    plant_id = _plant_entity_id(hass, init_integration)
    hass.states.async_set("sensor.test_moisture", "unavailable")
    await hass.async_block_till_done()
    events = async_capture_events(hass, "stale")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "trigger": {
                    "trigger": "plant.moisture_sensor_became_stale",
                    "target": {"entity_id": plant_id},
                    "options": {"for": {"seconds": 30}},
                },
                "action": {"event": "stale"},
            }
        },
    )
    await hass.async_block_till_done()
    # Part-way through the grace window, still dead -- must not fire yet.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=15))
    await hass.async_block_till_done()
    # Source populates before the grace window elapses -> not a stale event.
    hass.states.async_set("sensor.test_moisture", "42")
    await hass.async_block_till_done()
    assert len(events) == 0

    # Recovery (re)armed a freshness watch timer; detach it before teardown so
    # pytest-homeassistant-custom-component doesn't flag a lingering callback.
    automation_entity_id = hass.states.async_entity_ids("automation")[0]
    await hass.services.async_call(
        "automation",
        "turn_off",
        {"entity_id": automation_entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()


async def test_moisture_sensor_became_stale_after_grace_when_dead(
    hass: HomeAssistant, init_integration
) -> None:
    """A source stale at attach that stays dead past `for` fires once (unavailable).

    This catches a source that genuinely died during the restart: the grace timer
    expires while still `pending`, so it fires became_stale.
    """
    plant_id = _plant_entity_id(hass, init_integration)
    hass.states.async_set("sensor.test_moisture", "unavailable")
    await hass.async_block_till_done()
    events = async_capture_events(hass, "stale")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "trigger": {
                    "trigger": "plant.moisture_sensor_became_stale",
                    "target": {"entity_id": plant_id},
                    "options": {"for": {"seconds": 30}},
                },
                "action": {
                    "event": "stale",
                    "event_data": {"reason": "{{ trigger.reason }}"},
                },
            }
        },
    )
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()
    assert len(events) == 1
    assert events[0].data["reason"] == "unavailable"


async def test_moisture_sensor_became_stale_on_unavailable(
    hass: HomeAssistant, init_integration
) -> None:
    plant_id = _plant_entity_id(hass, init_integration)
    events = async_capture_events(hass, "stale")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "trigger": {
                    "trigger": "plant.moisture_sensor_became_stale",
                    "target": {"entity_id": plant_id},
                },
                "action": {
                    "event": "stale",
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


async def test_moisture_sensor_became_stale_on_no_update(
    hass: HomeAssistant, init_integration
) -> None:
    plant_id = _plant_entity_id(hass, init_integration)
    events = async_capture_events(hass, "stale")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "trigger": {
                    "trigger": "plant.moisture_sensor_became_stale",
                    "target": {"entity_id": plant_id},
                    "options": {"for": {"seconds": 30}},
                },
                "action": {"event": "stale"},
            }
        },
    )
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()
    assert len(events) == 1


async def test_moisture_sensor_became_fresh_on_recovery(
    hass: HomeAssistant, init_integration
) -> None:
    plant_id = _plant_entity_id(hass, init_integration)
    hass.states.async_set("sensor.test_moisture", "unavailable")
    await hass.async_block_till_done()
    events = async_capture_events(hass, "fresh")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "trigger": {
                    "trigger": "plant.moisture_sensor_became_fresh",
                    "target": {"entity_id": plant_id},
                    "options": {"for": {"seconds": 30}},
                },
                "action": {"event": "fresh"},
            }
        },
    )
    await hass.async_block_till_done()
    # Stale at attach -> `pending`. Let the grace window elapse while still dead so
    # the source becomes genuinely `stale` (no became_fresh yet -- fresh triggers
    # stay silent on stale transitions).
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()
    assert len(events) == 0
    # Now it recovers: a real stale->fresh transition fires became_fresh once.
    hass.states.async_set("sensor.test_moisture", "42")
    await hass.async_block_till_done()
    assert len(events) == 1

    # A "became_fresh" trigger re-arms its no-update watch timer after every
    # recovery (so it can detect a *future* stale->fresh transition too).
    # Turn the automation off so its trigger detaches and cancels that timer
    # before hass tears down -- otherwise pytest-homeassistant-custom-component
    # fails the test for a lingering scheduled callback, same as init_integration
    # explicitly unloads the config entry above for the same reason.
    automation_entity_id = hass.states.async_entity_ids("automation")[0]
    await hass.services.async_call(
        "automation",
        "turn_off",
        {"entity_id": automation_entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()
