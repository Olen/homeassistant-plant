"""Tests for plant integration services."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant.const import (
    ATTR_PLANT,
    DOMAIN,
    SERVICE_REPLACE_SENSOR,
)


class TestReplaceSensorService:
    """Tests for the plant.replace_sensor service."""

    async def test_replace_sensor_service_registered(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that replace_sensor service is registered."""
        assert hass.services.has_service(DOMAIN, SERVICE_REPLACE_SENSOR)

    async def test_replace_sensor_valid(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test replacing sensor with valid inputs."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        meter_entity = plant.sensor_temperature.entity_id

        # Create a new sensor to replace with
        new_sensor_id = "sensor.new_temperature"
        hass.states.async_set(
            new_sensor_id,
            "25",
            {"unit_of_measurement": "°C", "device_class": "temperature"},
        )
        await hass.async_block_till_done()

        # Call the service
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REPLACE_SENSOR,
            {
                "meter_entity": meter_entity,
                "new_sensor": new_sensor_id,
            },
            blocking=True,
        )
        await hass.async_block_till_done()

        # Verify the sensor was replaced
        assert plant.sensor_temperature.external_sensor == new_sensor_id

    async def test_replace_sensor_with_empty_clears_sensor(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test replacing sensor with empty string clears the external sensor."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        meter_entity = plant.sensor_temperature.entity_id

        # Call the service with empty new_sensor
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REPLACE_SENSOR,
            {
                "meter_entity": meter_entity,
                "new_sensor": "",
            },
            blocking=True,
        )
        await hass.async_block_till_done()

        # External sensor should be cleared (None)
        assert plant.sensor_temperature.external_sensor is None

    async def test_replace_sensor_invalid_meter_entity(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test replace sensor with invalid meter entity is rejected."""
        # Create a non-plant sensor
        hass.states.async_set("sensor.some_other_sensor", "100")
        await hass.async_block_till_done()

        # Call the service with non-plant meter entity
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REPLACE_SENSOR,
            {
                "meter_entity": "sensor.some_other_sensor",
                "new_sensor": "sensor.test_temperature",
            },
            blocking=True,
        )
        await hass.async_block_till_done()

        # Should not raise but return False (rejected)
        # The service logs a warning but doesn't raise

    async def test_replace_sensor_invalid_new_sensor_not_sensor(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test replace sensor rejects non-sensor entities."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        meter_entity = plant.sensor_temperature.entity_id

        # Create a non-sensor entity
        hass.states.async_set("switch.not_a_sensor", "on")
        await hass.async_block_till_done()

        # Call the service with non-sensor entity
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REPLACE_SENSOR,
            {
                "meter_entity": meter_entity,
                "new_sensor": "switch.not_a_sensor",
            },
            blocking=True,
        )
        await hass.async_block_till_done()

        # Should be rejected - original sensor should remain
        assert plant.sensor_temperature.external_sensor == "sensor.test_temperature"

    async def test_replace_sensor_nonexistent_new_sensor(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test replace sensor with nonexistent new sensor is rejected."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        meter_entity = plant.sensor_temperature.entity_id

        # Call the service with nonexistent sensor
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REPLACE_SENSOR,
            {
                "meter_entity": meter_entity,
                "new_sensor": "sensor.does_not_exist",
            },
            blocking=True,
        )
        await hass.async_block_till_done()

        # Should be rejected - original sensor should remain
        assert plant.sensor_temperature.external_sensor == "sensor.test_temperature"

    async def test_replace_sensor_nonexistent_meter(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test replace sensor with nonexistent meter entity."""
        # Call the service with nonexistent meter entity
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REPLACE_SENSOR,
            {
                "meter_entity": "plant.does_not_exist_meter",
                "new_sensor": "sensor.test_temperature",
            },
            blocking=True,
        )
        await hass.async_block_till_done()

        # Should not raise, just log warning

    async def test_replace_multiple_sensors(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test replacing multiple sensors."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Create new sensors
        hass.states.async_set("sensor.new_temp", "26", {"unit_of_measurement": "°C"})
        hass.states.async_set("sensor.new_moisture", "50", {"unit_of_measurement": "%"})
        await hass.async_block_till_done()

        # Replace temperature sensor
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REPLACE_SENSOR,
            {
                "meter_entity": plant.sensor_temperature.entity_id,
                "new_sensor": "sensor.new_temp",
            },
            blocking=True,
        )

        # Replace moisture sensor
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REPLACE_SENSOR,
            {
                "meter_entity": plant.sensor_moisture.entity_id,
                "new_sensor": "sensor.new_moisture",
            },
            blocking=True,
        )
        await hass.async_block_till_done()

        assert plant.sensor_temperature.external_sensor == "sensor.new_temp"
        assert plant.sensor_moisture.external_sensor == "sensor.new_moisture"


class TestServiceUnload:
    """Tests for service cleanup on unload."""

    async def test_service_removed_on_full_unload(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that service is removed when all entries are unloaded."""
        # Service should exist
        assert hass.services.has_service(DOMAIN, SERVICE_REPLACE_SENSOR)

        # Unload the entry
        await hass.config_entries.async_unload(init_integration.entry_id)
        await hass.async_block_till_done()

        # After unloading all entries, service should be removed
        # (only if no other entries remain)
        if DOMAIN not in hass.data or len(hass.data[DOMAIN]) == 0:
            assert not hass.services.has_service(DOMAIN, SERVICE_REPLACE_SENSOR)
