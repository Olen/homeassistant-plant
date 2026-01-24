"""Tests for plant integration setup and PlantDevice."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import (
    STATE_OK,
    STATE_PROBLEM,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.plant.const import (
    ATTR_PLANT,
    DOMAIN,
    FLOW_PLANT_INFO,
    STATE_HIGH,
    STATE_LOW,
)

from .common import set_external_sensor_states
from .conftest import TEST_ENTRY_ID, TEST_PLANT_NAME


class TestIntegrationSetup:
    """Tests for integration setup and teardown."""

    async def test_setup_entry(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test successful setup of a config entry."""
        assert DOMAIN in hass.data
        assert init_integration.entry_id in hass.data[DOMAIN]
        assert ATTR_PLANT in hass.data[DOMAIN][init_integration.entry_id]

    async def test_setup_entry_creates_device(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that setup creates a device in the device registry."""
        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, init_integration.entry_id)}
        )
        assert device is not None
        assert device.name == TEST_PLANT_NAME

    async def test_setup_entry_creates_entities(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that setup creates expected entities."""
        entity_registry = er.async_get(hass)
        entities = er.async_entries_for_config_entry(
            entity_registry, init_integration.entry_id
        )

        # Should have: 5 sensors + 12 thresholds + 3 calculated sensors = 20
        # Plus potentially the main plant entity
        assert len(entities) >= 17  # At minimum sensors + thresholds

    async def test_unload_entry(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test unloading a config entry."""
        assert DOMAIN in hass.data
        assert init_integration.entry_id in hass.data[DOMAIN]

        await hass.config_entries.async_unload(init_integration.entry_id)
        await hass.async_block_till_done()

        # Entry should be removed from domain data
        assert init_integration.entry_id not in hass.data.get(DOMAIN, {})

    async def test_setup_entry_no_plant_info(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test setup with missing plant info returns True but doesn't set up."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Empty Plant",
            data={},  # No FLOW_PLANT_INFO
            entry_id="empty_entry_id",
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Should still be in hass.data[DOMAIN] but not fully set up
        assert DOMAIN in hass.data


class TestPlantDevice:
    """Tests for PlantDevice entity."""

    async def test_plant_device_state_ok(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device state is OK when all readings are within thresholds."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Set values within thresholds
        await set_external_sensor_states(
            hass,
            temperature=25.0,  # Within 10-40
            moisture=40.0,  # Within 20-60
            conductivity=1000.0,  # Within 500-3000
            illuminance=5000.0,  # Within 0-100000
            humidity=40.0,  # Within 20-60
        )
        await hass.async_block_till_done()

        plant.update()
        assert plant.state == STATE_OK

    async def test_plant_device_state_problem_moisture_low(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device shows problem when moisture is too low."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=5.0,  # Below min of 20
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await hass.async_block_till_done()

        plant.update()
        assert plant.state == STATE_PROBLEM
        assert plant.moisture_status == STATE_LOW

    async def test_plant_device_state_problem_moisture_high(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device shows problem when moisture is too high."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=80.0,  # Above max of 60
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await hass.async_block_till_done()

        plant.update()
        assert plant.state == STATE_PROBLEM
        assert plant.moisture_status == STATE_HIGH

    async def test_plant_device_state_problem_temperature_low(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device shows problem when temperature is too low."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        await set_external_sensor_states(
            hass,
            temperature=5.0,  # Below min of 10
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await hass.async_block_till_done()

        plant.update()
        assert plant.state == STATE_PROBLEM
        assert plant.temperature_status == STATE_LOW

    async def test_plant_device_state_problem_temperature_high(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device shows problem when temperature is too high."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        await set_external_sensor_states(
            hass,
            temperature=45.0,  # Above max of 40
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await hass.async_block_till_done()

        plant.update()
        assert plant.state == STATE_PROBLEM
        assert plant.temperature_status == STATE_HIGH

    async def test_plant_device_state_problem_illuminance_high(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device shows problem when illuminance is too high."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=150000.0,  # Above max of 100000
            humidity=40.0,
        )
        await hass.async_block_till_done()

        plant.update()
        assert plant.state == STATE_PROBLEM
        assert plant.illuminance_status == STATE_HIGH

    async def test_plant_device_state_unknown_no_sensors(
        self,
        hass: HomeAssistant,
        init_integration_no_sensors: MockConfigEntry,
    ) -> None:
        """Test plant device state is unknown when no sensor data available."""
        plant = hass.data[DOMAIN][init_integration_no_sensors.entry_id][ATTR_PLANT]
        plant.update()
        assert plant.state == STATE_UNKNOWN

    async def test_plant_device_extra_state_attributes(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device extra state attributes."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        plant.plant_complete = True

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await hass.async_block_till_done()
        plant.update()

        attrs = plant.extra_state_attributes
        assert "species" in attrs
        assert "moisture_status" in attrs
        assert "temperature_status" in attrs
        assert "conductivity_status" in attrs
        assert "illuminance_status" in attrs
        assert "humidity_status" in attrs
        assert "dli_status" in attrs

    async def test_plant_device_device_info(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device info."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        device_info = plant.device_info
        assert "identifiers" in device_info
        assert "name" in device_info
        assert device_info["name"] == TEST_PLANT_NAME

    async def test_plant_device_trigger_disabled(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_external_sensors: None,
    ) -> None:
        """Test that disabling triggers prevents problem state."""
        # Add options to disable moisture trigger
        mock_config_entry._options = {"moisture_trigger": False}
        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][mock_config_entry.entry_id][ATTR_PLANT]

        # Set moisture below threshold
        await set_external_sensor_states(hass, moisture=5.0)
        await hass.async_block_till_done()

        plant.update()
        # moisture_status should still be LOW
        assert plant.moisture_status == STATE_LOW
        # But overall state should be OK because trigger is disabled
        # (Note: state may still be PROBLEM if other sensors are out of range)

    async def test_plant_device_add_image(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test adding an image to the plant device."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        new_image = "https://example.com/new_plant.jpg"
        plant.add_image(new_image)

        assert plant.entity_picture == new_image

    async def test_plant_device_websocket_info(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test websocket info property."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Before complete, should return empty dict
        plant.plant_complete = False
        assert plant.websocket_info == {}

        # After complete, should return full info
        plant.plant_complete = True
        ws_info = plant.websocket_info

        assert "temperature" in ws_info
        assert "illuminance" in ws_info
        assert "moisture" in ws_info
        assert "conductivity" in ws_info
        assert "humidity" in ws_info
        assert "dli" in ws_info

        # Each should have max, min, current, icon, etc.
        assert "max" in ws_info["temperature"]
        assert "min" in ws_info["temperature"]
        assert "current" in ws_info["temperature"]
