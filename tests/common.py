"""Common test utilities for plant integration tests."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.plant.const import ATTR_PLANT, ATTR_SENSORS, DOMAIN


def get_plant_entity_ids(hass: HomeAssistant, entry_id: str) -> dict[str, list[str]]:
    """Get all entity IDs for a plant config entry organized by type."""
    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_registry, entry_id)

    result = {
        "plant": [],
        "sensors": [],
        "numbers": [],
    }

    for entity in entities:
        if entity.domain == DOMAIN:
            result["plant"].append(entity.entity_id)
        elif entity.domain == "sensor":
            result["sensors"].append(entity.entity_id)
        elif entity.domain == "number":
            result["numbers"].append(entity.entity_id)

    return result


async def set_sensor_state(
    hass: HomeAssistant,
    entity_id: str,
    state: str | float,
    attributes: dict[str, Any] | None = None,
) -> None:
    """Set a sensor state for testing."""
    if attributes is None:
        attributes = {}
    hass.states.async_set(entity_id, str(state), attributes)
    await hass.async_block_till_done()


async def set_external_sensor_states(
    hass: HomeAssistant,
    temperature: float | None = None,
    moisture: float | None = None,
    conductivity: float | None = None,
    illuminance: float | None = None,
    humidity: float | None = None,
    co2: float | None = None,
    soil_temperature: float | None = None,
) -> None:
    """Set external sensor states for testing."""
    if temperature is not None:
        await set_sensor_state(
            hass,
            "sensor.test_temperature",
            temperature,
            {"unit_of_measurement": "°C", "device_class": "temperature"},
        )
    if moisture is not None:
        await set_sensor_state(
            hass,
            "sensor.test_moisture",
            moisture,
            {"unit_of_measurement": "%", "device_class": "moisture"},
        )
    if conductivity is not None:
        await set_sensor_state(
            hass,
            "sensor.test_conductivity",
            conductivity,
            {"unit_of_measurement": "µS/cm", "device_class": "conductivity"},
        )
    if illuminance is not None:
        await set_sensor_state(
            hass,
            "sensor.test_illuminance",
            illuminance,
            {"unit_of_measurement": "lx", "device_class": "illuminance"},
        )
    if humidity is not None:
        await set_sensor_state(
            hass,
            "sensor.test_humidity",
            humidity,
            {"unit_of_measurement": "%", "device_class": "humidity"},
        )
    if co2 is not None:
        await set_sensor_state(
            hass,
            "sensor.test_co2",
            co2,
            {"unit_of_measurement": "ppm", "device_class": "carbon_dioxide"},
        )
    if soil_temperature is not None:
        await set_sensor_state(
            hass,
            "sensor.test_soil_temperature",
            soil_temperature,
            {"unit_of_measurement": "°C", "device_class": "temperature"},
        )


def assert_entity_state(
    hass: HomeAssistant, entity_id: str, expected_state: str
) -> None:
    """Assert that an entity has the expected state."""
    state = hass.states.get(entity_id)
    assert state is not None, f"Entity {entity_id} not found"
    assert (
        state.state == expected_state
    ), f"Entity {entity_id} has state {state.state}, expected {expected_state}"


def assert_entity_attribute(
    hass: HomeAssistant,
    entity_id: str,
    attribute: str,
    expected_value: Any,
) -> None:
    """Assert that an entity has the expected attribute value."""
    state = hass.states.get(entity_id)
    assert state is not None, f"Entity {entity_id} not found"
    assert (
        attribute in state.attributes
    ), f"Entity {entity_id} does not have attribute {attribute}"
    assert state.attributes[attribute] == expected_value, (
        f"Entity {entity_id} attribute {attribute} is {state.attributes[attribute]}, "
        f"expected {expected_value}"
    )


async def update_plant_sensors(hass: HomeAssistant, entry_id: str) -> None:
    """Update all plant sensors to read from external sensors.

    This triggers the internal plant sensors to read current values
    from their configured external sensors, and then updates the plant state.
    """
    plant_data = hass.data[DOMAIN][entry_id]
    plant = plant_data[ATTR_PLANT]

    # Update all plant sensors to read external sensor values
    if ATTR_SENSORS in plant_data:
        for sensor in plant_data[ATTR_SENSORS]:
            await sensor.async_update()
            sensor.async_write_ha_state()

    await hass.async_block_till_done()

    # Update the plant state calculation
    plant.update()
