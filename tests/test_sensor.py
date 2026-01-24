"""Tests for plant sensor entities."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import (
    LIGHT_LUX,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.plant.const import (
    ATTR_PLANT,
    ATTR_SENSORS,
    DEFAULT_LUX_TO_PPFD,
    DOMAIN,
    UNIT_DLI,
    UNIT_PPFD,
)
from custom_components.plant.sensor import PlantCurrentPpfd

from .common import set_external_sensor_states, set_sensor_state
from .conftest import TEST_ENTRY_ID, TEST_PLANT_NAME


class TestPlantCurrentSensors:
    """Tests for PlantCurrentStatus sensor entities."""

    async def test_sensor_entities_created(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that all sensor entities are created."""
        entity_registry = er.async_get(hass)
        entities = er.async_entries_for_config_entry(
            entity_registry, init_integration.entry_id
        )

        sensor_entities = [e for e in entities if e.domain == "sensor"]
        # Should have: moisture, temperature, conductivity, illuminance, humidity
        # + ppfd, total integral, dli = 8 sensors
        assert len(sensor_entities) >= 5

    async def test_temperature_sensor(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test temperature sensor entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_temperature

        assert sensor is not None
        assert "temperature" in sensor.name.lower()
        assert sensor.device_class == "temperature"

    async def test_moisture_sensor(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test moisture sensor entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_moisture

        assert sensor is not None
        assert "moisture" in sensor.name.lower()
        assert sensor.device_class == "moisture"

    async def test_conductivity_sensor(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test conductivity sensor entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_conductivity

        assert sensor is not None
        assert "conductivity" in sensor.name.lower()

    async def test_illuminance_sensor(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test illuminance sensor entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_illuminance

        assert sensor is not None
        assert "illuminance" in sensor.name.lower()
        assert sensor.device_class == "illuminance"

    async def test_humidity_sensor(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test humidity sensor entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_humidity

        assert sensor is not None
        assert "humidity" in sensor.name.lower()
        assert sensor.device_class == "humidity"

    async def test_sensor_tracks_external_sensor(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that plant sensor tracks external sensor state."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_temperature

        # Set external sensor value
        await set_sensor_state(
            hass,
            "sensor.test_temperature",
            25.5,
            {"unit_of_measurement": "°C"},
        )
        await hass.async_block_till_done()

        # Update the sensor
        await sensor.async_update()
        assert sensor.native_value == 25.5

    async def test_sensor_handles_unavailable_external(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test sensor handles unavailable external sensor."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_temperature

        # Set external sensor to unavailable
        hass.states.async_set("sensor.test_temperature", STATE_UNAVAILABLE)
        await hass.async_block_till_done()

        await sensor.async_update()
        # Should have default state when external is unavailable
        assert sensor.native_value is None or sensor.native_value == sensor._default_state

    async def test_sensor_handles_unknown_external(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test sensor handles unknown external sensor state."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_temperature

        # Set external sensor to unknown
        hass.states.async_set("sensor.test_temperature", STATE_UNKNOWN)
        await hass.async_block_till_done()

        await sensor.async_update()
        assert sensor.native_value is None or sensor.native_value == sensor._default_state

    async def test_sensor_extra_state_attributes(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test sensor extra state attributes include external sensor."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_temperature

        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "external_sensor" in attrs
        assert attrs["external_sensor"] == "sensor.test_temperature"

    async def test_replace_external_sensor(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test replacing the external sensor."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_temperature

        # Create a new sensor
        hass.states.async_set(
            "sensor.new_temperature",
            "30",
            {"unit_of_measurement": "°C"},
        )
        await hass.async_block_till_done()

        # Replace the external sensor
        sensor.replace_external_sensor("sensor.new_temperature")

        assert sensor.external_sensor == "sensor.new_temperature"

    async def test_sensor_no_external_sensor(
        self,
        hass: HomeAssistant,
        init_integration_no_sensors: MockConfigEntry,
    ) -> None:
        """Test sensor behavior when no external sensor is configured."""
        plant = hass.data[DOMAIN][init_integration_no_sensors.entry_id][ATTR_PLANT]
        sensor = plant.sensor_temperature

        await sensor.async_update()
        # Should have default/None value
        assert sensor.native_value is None or sensor.native_value == sensor._default_state


class TestPpfdSensor:
    """Tests for PPFD sensor entity."""

    async def test_ppfd_sensor_created(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that PPFD sensor is created."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        assert plant.ppfd is not None
        assert "ppfd" in plant.ppfd.name.lower()

    async def test_ppfd_calculation(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test PPFD calculation from illuminance."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        ppfd_sensor = plant.ppfd

        # Set illuminance value
        lux_value = 10000
        await set_sensor_state(
            hass,
            "sensor.test_illuminance",
            lux_value,
            {"unit_of_measurement": "lx"},
        )
        await hass.async_block_till_done()

        # Calculate expected PPFD
        expected_ppfd = lux_value * DEFAULT_LUX_TO_PPFD / 1000000

        await ppfd_sensor.async_update()
        assert ppfd_sensor.native_value == pytest.approx(expected_ppfd, rel=0.01)

    async def test_ppfd_with_unavailable_illuminance(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test PPFD calculation when illuminance is unavailable."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        ppfd_sensor = plant.ppfd

        # Set illuminance to unavailable
        hass.states.async_set(
            plant.sensor_illuminance.entity_id,
            STATE_UNAVAILABLE,
        )
        await hass.async_block_till_done()

        await ppfd_sensor.async_update()
        assert ppfd_sensor.native_value is None

    async def test_ppfd_unit(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test PPFD sensor unit of measurement."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        ppfd_sensor = plant.ppfd

        assert ppfd_sensor.native_unit_of_measurement == UNIT_PPFD


class TestDliSensor:
    """Tests for DLI (Daily Light Integral) sensor entity."""

    async def test_dli_sensor_created(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that DLI sensor is created."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        assert plant.dli is not None
        assert "dli" in plant.dli.name.lower()

    async def test_dli_unit(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test DLI sensor unit of measurement."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        dli_sensor = plant.dli

        assert dli_sensor._unit_of_measurement == UNIT_DLI


class TestTotalLightIntegralSensor:
    """Tests for Total Light Integral sensor entity."""

    async def test_total_integral_sensor_created(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that total light integral sensor is created."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        assert plant.total_integral is not None
        assert "integral" in plant.total_integral.name.lower()

    async def test_total_integral_unit(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test total integral sensor unit of measurement."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        assert plant.total_integral._unit_of_measurement == UNIT_DLI


class TestSensorDeviceInfo:
    """Tests for sensor device info."""

    async def test_sensor_device_info(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that sensors have correct device info."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        for sensor in plant.meter_entities:
            device_info = sensor.device_info
            assert "identifiers" in device_info
            assert (DOMAIN, plant.unique_id) in device_info["identifiers"]

    async def test_integral_sensor_device_info(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that integral sensors have correct device info."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        for sensor in plant.integral_entities:
            device_info = sensor.device_info
            assert "identifiers" in device_info
            assert (DOMAIN, plant.unique_id) in device_info["identifiers"]
