"""Tests for plant integration setup and PlantDevice."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import (
    STATE_OK,
    STATE_PROBLEM,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant import async_setup
from custom_components.plant.const import (
    ATTR_PLANT,
    DOMAIN,
    FLOW_PLANT_INFO,
    STATE_HIGH,
    STATE_LOW,
)

from .common import set_external_sensor_states, update_plant_sensors
from .conftest import TEST_PLANT_NAME


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

        # Should have: 7 sensors + 17 thresholds + 3 calculated sensors = 27
        # Plus potentially the main plant entity
        assert len(entities) >= 24  # At minimum sensors + thresholds

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

    async def test_remove_entry(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test removing a config entry cleans up entity and device registries."""
        entry_id = init_integration.entry_id

        # Verify entities and device exist before removal
        entity_registry = er.async_get(hass)
        device_registry = dr.async_get(hass)

        entities_before = er.async_entries_for_config_entry(entity_registry, entry_id)
        device_before = device_registry.async_get_device(
            identifiers={(DOMAIN, entry_id)}
        )
        assert len(entities_before) > 0
        assert device_before is not None

        # Remove the config entry (this calls async_remove_entry)
        await hass.config_entries.async_remove(entry_id)
        await hass.async_block_till_done()

        # Verify entities are removed from registry
        entities_after = er.async_entries_for_config_entry(entity_registry, entry_id)
        assert len(entities_after) == 0

        # Verify device is removed from registry
        device_after = device_registry.async_get_device(
            identifiers={(DOMAIN, entry_id)}
        )
        assert device_after is None

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

        # Update internal sensors and plant state
        await update_plant_sensors(hass, init_integration.entry_id)
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

        await update_plant_sensors(hass, init_integration.entry_id)
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

        await update_plant_sensors(hass, init_integration.entry_id)
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

        await update_plant_sensors(hass, init_integration.entry_id)
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

        await update_plant_sensors(hass, init_integration.entry_id)
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

        await update_plant_sensors(hass, init_integration.entry_id)
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
            co2=800.0,
            soil_temperature=22.0,
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
        assert "co2_status" in attrs
        assert "soil_temperature_status" in attrs

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
        mock_external_sensors: None,
    ) -> None:
        """Test that disabling triggers prevents problem state."""
        from homeassistant.const import ATTR_ENTITY_PICTURE, ATTR_NAME

        from custom_components.plant.const import (
            CONF_MAX_CONDUCTIVITY,
            CONF_MAX_DLI,
            CONF_MAX_HUMIDITY,
            CONF_MAX_ILLUMINANCE,
            CONF_MAX_MOISTURE,
            CONF_MAX_TEMPERATURE,
            CONF_MIN_CONDUCTIVITY,
            CONF_MIN_DLI,
            CONF_MIN_HUMIDITY,
            CONF_MIN_ILLUMINANCE,
            CONF_MIN_MOISTURE,
            CONF_MIN_TEMPERATURE,
            DATA_SOURCE,
            FLOW_MOISTURE_TRIGGER,
            OPB_DISPLAY_PID,
        )

        # Create config entry with moisture trigger disabled
        entry = MockConfigEntry(
            domain=DOMAIN,
            entry_id="test_entry_trigger_disabled",
            unique_id="test_entry_trigger_disabled",
            title="Test Plant",
            data={
                DATA_SOURCE: "Default values",
                FLOW_PLANT_INFO: {
                    ATTR_NAME: "Test Plant",
                    "species": "monstera deliciosa",
                    OPB_DISPLAY_PID: "Monstera deliciosa",
                    ATTR_ENTITY_PICTURE: "https://example.com/plant.jpg",
                    "limits": {
                        CONF_MAX_MOISTURE: 60,
                        CONF_MIN_MOISTURE: 20,
                        CONF_MAX_TEMPERATURE: 40,
                        CONF_MIN_TEMPERATURE: 10,
                        CONF_MAX_CONDUCTIVITY: 3000,
                        CONF_MIN_CONDUCTIVITY: 500,
                        CONF_MAX_ILLUMINANCE: 100000,
                        CONF_MIN_ILLUMINANCE: 0,
                        CONF_MAX_HUMIDITY: 60,
                        CONF_MIN_HUMIDITY: 20,
                        CONF_MAX_DLI: 30,
                        CONF_MIN_DLI: 2,
                    },
                    "temperature_sensor": "sensor.test_temperature",
                    "moisture_sensor": "sensor.test_moisture",
                    "conductivity_sensor": "sensor.test_conductivity",
                    "illuminance_sensor": "sensor.test_illuminance",
                    "humidity_sensor": "sensor.test_humidity",
                },
            },
            options={FLOW_MOISTURE_TRIGGER: False},
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]

        # Set all sensors - moisture below threshold, others normal
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=5.0,  # Below threshold
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )

        await update_plant_sensors(hass, entry.entry_id)

        # moisture_status should still be LOW
        assert plant.moisture_status == STATE_LOW
        # But overall state should be OK because trigger is disabled
        assert plant.state == STATE_OK

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
        assert "co2" in ws_info
        assert "soil_temperature" in ws_info

        # Each should have max, min, current, icon, etc.
        assert "max" in ws_info["temperature"]
        assert "min" in ws_info["temperature"]
        assert "current" in ws_info["temperature"]

    async def test_plant_device_state_problem_conductivity_low(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device shows problem when conductivity is too low."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=100.0,  # Below min of 500
            illuminance=5000.0,
            humidity=40.0,
        )

        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.state == STATE_PROBLEM
        assert plant.conductivity_status == STATE_LOW

    async def test_plant_device_state_problem_conductivity_high(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device shows problem when conductivity is too high."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=5000.0,  # Above max of 3000
            illuminance=5000.0,
            humidity=40.0,
        )

        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.state == STATE_PROBLEM
        assert plant.conductivity_status == STATE_HIGH

    async def test_plant_device_state_problem_humidity_low(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device shows problem when humidity is too low."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=10.0,  # Below min of 20
        )

        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.state == STATE_PROBLEM
        assert plant.humidity_status == STATE_LOW

    async def test_plant_device_state_problem_humidity_high(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device shows problem when humidity is too high."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=80.0,  # Above max of 60
        )

        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.state == STATE_PROBLEM
        assert plant.humidity_status == STATE_HIGH

    async def test_plant_device_state_problem_co2_low(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device shows problem when CO2 is too low."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
            co2=200.0,  # Below min of 400
        )

        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.state == STATE_PROBLEM
        assert plant.co2_status == STATE_LOW

    async def test_plant_device_state_problem_co2_high(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device shows problem when CO2 is too high."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
            co2=3000.0,  # Above max of 2000
        )

        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.state == STATE_PROBLEM
        assert plant.co2_status == STATE_HIGH

    async def test_plant_device_state_problem_soil_temperature_low(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device shows problem when soil temperature is too low."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
            soil_temperature=5.0,  # Below min of 10
        )

        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.state == STATE_PROBLEM
        assert plant.soil_temperature_status == STATE_LOW

    async def test_plant_device_state_problem_soil_temperature_high(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device shows problem when soil temperature is too high."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
            soil_temperature=50.0,  # Above max of 40
        )

        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.state == STATE_PROBLEM
        assert plant.soil_temperature_status == STATE_HIGH

    async def test_plant_device_conductivity_trigger_disabled(
        self,
        hass: HomeAssistant,
        mock_external_sensors: None,
    ) -> None:
        """Test that disabling conductivity trigger prevents problem state."""
        from homeassistant.const import ATTR_ENTITY_PICTURE, ATTR_NAME

        from custom_components.plant.const import (
            CONF_MAX_CONDUCTIVITY,
            CONF_MAX_DLI,
            CONF_MAX_HUMIDITY,
            CONF_MAX_ILLUMINANCE,
            CONF_MAX_MOISTURE,
            CONF_MAX_TEMPERATURE,
            CONF_MIN_CONDUCTIVITY,
            CONF_MIN_DLI,
            CONF_MIN_HUMIDITY,
            CONF_MIN_ILLUMINANCE,
            CONF_MIN_MOISTURE,
            CONF_MIN_TEMPERATURE,
            DATA_SOURCE,
            FLOW_CONDUCTIVITY_TRIGGER,
            OPB_DISPLAY_PID,
        )

        entry = MockConfigEntry(
            domain=DOMAIN,
            entry_id="test_entry_cond_trigger_disabled",
            unique_id="test_entry_cond_trigger_disabled",
            title="Test Plant",
            data={
                DATA_SOURCE: "Default values",
                FLOW_PLANT_INFO: {
                    ATTR_NAME: "Test Plant",
                    "species": "monstera deliciosa",
                    OPB_DISPLAY_PID: "Monstera deliciosa",
                    ATTR_ENTITY_PICTURE: "https://example.com/plant.jpg",
                    "limits": {
                        CONF_MAX_MOISTURE: 60,
                        CONF_MIN_MOISTURE: 20,
                        CONF_MAX_TEMPERATURE: 40,
                        CONF_MIN_TEMPERATURE: 10,
                        CONF_MAX_CONDUCTIVITY: 3000,
                        CONF_MIN_CONDUCTIVITY: 500,
                        CONF_MAX_ILLUMINANCE: 100000,
                        CONF_MIN_ILLUMINANCE: 0,
                        CONF_MAX_HUMIDITY: 60,
                        CONF_MIN_HUMIDITY: 20,
                        CONF_MAX_DLI: 30,
                        CONF_MIN_DLI: 2,
                    },
                    "temperature_sensor": "sensor.test_temperature",
                    "moisture_sensor": "sensor.test_moisture",
                    "conductivity_sensor": "sensor.test_conductivity",
                    "illuminance_sensor": "sensor.test_illuminance",
                    "humidity_sensor": "sensor.test_humidity",
                },
            },
            options={FLOW_CONDUCTIVITY_TRIGGER: False},
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=100.0,  # Below threshold
            illuminance=5000.0,
            humidity=40.0,
        )

        await update_plant_sensors(hass, entry.entry_id)

        assert plant.conductivity_status == STATE_LOW
        assert plant.state == STATE_OK

    async def test_plant_device_humidity_trigger_disabled(
        self,
        hass: HomeAssistant,
        mock_external_sensors: None,
    ) -> None:
        """Test that disabling humidity trigger prevents problem state."""
        from homeassistant.const import ATTR_ENTITY_PICTURE, ATTR_NAME

        from custom_components.plant.const import (
            CONF_MAX_CONDUCTIVITY,
            CONF_MAX_DLI,
            CONF_MAX_HUMIDITY,
            CONF_MAX_ILLUMINANCE,
            CONF_MAX_MOISTURE,
            CONF_MAX_TEMPERATURE,
            CONF_MIN_CONDUCTIVITY,
            CONF_MIN_DLI,
            CONF_MIN_HUMIDITY,
            CONF_MIN_ILLUMINANCE,
            CONF_MIN_MOISTURE,
            CONF_MIN_TEMPERATURE,
            DATA_SOURCE,
            FLOW_HUMIDITY_TRIGGER,
            OPB_DISPLAY_PID,
        )

        entry = MockConfigEntry(
            domain=DOMAIN,
            entry_id="test_entry_humidity_trigger_disabled",
            unique_id="test_entry_humidity_trigger_disabled",
            title="Test Plant",
            data={
                DATA_SOURCE: "Default values",
                FLOW_PLANT_INFO: {
                    ATTR_NAME: "Test Plant",
                    "species": "monstera deliciosa",
                    OPB_DISPLAY_PID: "Monstera deliciosa",
                    ATTR_ENTITY_PICTURE: "https://example.com/plant.jpg",
                    "limits": {
                        CONF_MAX_MOISTURE: 60,
                        CONF_MIN_MOISTURE: 20,
                        CONF_MAX_TEMPERATURE: 40,
                        CONF_MIN_TEMPERATURE: 10,
                        CONF_MAX_CONDUCTIVITY: 3000,
                        CONF_MIN_CONDUCTIVITY: 500,
                        CONF_MAX_ILLUMINANCE: 100000,
                        CONF_MIN_ILLUMINANCE: 0,
                        CONF_MAX_HUMIDITY: 60,
                        CONF_MIN_HUMIDITY: 20,
                        CONF_MAX_DLI: 30,
                        CONF_MIN_DLI: 2,
                    },
                    "temperature_sensor": "sensor.test_temperature",
                    "moisture_sensor": "sensor.test_moisture",
                    "conductivity_sensor": "sensor.test_conductivity",
                    "illuminance_sensor": "sensor.test_illuminance",
                    "humidity_sensor": "sensor.test_humidity",
                },
            },
            options={FLOW_HUMIDITY_TRIGGER: False},
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=10.0,  # Below threshold
        )

        await update_plant_sensors(hass, entry.entry_id)

        assert plant.humidity_status == STATE_LOW
        assert plant.state == STATE_OK

    async def test_plant_device_co2_trigger_disabled(
        self,
        hass: HomeAssistant,
        mock_external_sensors: None,
    ) -> None:
        """Test that disabling CO2 trigger prevents problem state."""
        from homeassistant.const import ATTR_ENTITY_PICTURE, ATTR_NAME

        from custom_components.plant.const import (
            CONF_MAX_CO2,
            CONF_MAX_CONDUCTIVITY,
            CONF_MAX_DLI,
            CONF_MAX_HUMIDITY,
            CONF_MAX_ILLUMINANCE,
            CONF_MAX_MOISTURE,
            CONF_MAX_SOIL_TEMPERATURE,
            CONF_MAX_TEMPERATURE,
            CONF_MIN_CO2,
            CONF_MIN_CONDUCTIVITY,
            CONF_MIN_DLI,
            CONF_MIN_HUMIDITY,
            CONF_MIN_ILLUMINANCE,
            CONF_MIN_MOISTURE,
            CONF_MIN_SOIL_TEMPERATURE,
            CONF_MIN_TEMPERATURE,
            DATA_SOURCE,
            FLOW_CO2_TRIGGER,
            OPB_DISPLAY_PID,
        )

        entry = MockConfigEntry(
            domain=DOMAIN,
            entry_id="test_entry_co2_trigger_disabled",
            unique_id="test_entry_co2_trigger_disabled",
            title="Test Plant",
            data={
                DATA_SOURCE: "Default values",
                FLOW_PLANT_INFO: {
                    ATTR_NAME: "Test Plant",
                    "species": "monstera deliciosa",
                    OPB_DISPLAY_PID: "Monstera deliciosa",
                    ATTR_ENTITY_PICTURE: "https://example.com/plant.jpg",
                    "limits": {
                        CONF_MAX_MOISTURE: 60,
                        CONF_MIN_MOISTURE: 20,
                        CONF_MAX_TEMPERATURE: 40,
                        CONF_MIN_TEMPERATURE: 10,
                        CONF_MAX_CONDUCTIVITY: 3000,
                        CONF_MIN_CONDUCTIVITY: 500,
                        CONF_MAX_ILLUMINANCE: 100000,
                        CONF_MIN_ILLUMINANCE: 0,
                        CONF_MAX_HUMIDITY: 60,
                        CONF_MIN_HUMIDITY: 20,
                        CONF_MAX_DLI: 30,
                        CONF_MIN_DLI: 2,
                        CONF_MAX_CO2: 2000,
                        CONF_MIN_CO2: 400,
                        CONF_MAX_SOIL_TEMPERATURE: 40,
                        CONF_MIN_SOIL_TEMPERATURE: 10,
                    },
                    "temperature_sensor": "sensor.test_temperature",
                    "moisture_sensor": "sensor.test_moisture",
                    "conductivity_sensor": "sensor.test_conductivity",
                    "illuminance_sensor": "sensor.test_illuminance",
                    "humidity_sensor": "sensor.test_humidity",
                    "co2_sensor": "sensor.test_co2",
                    "soil_temperature_sensor": "sensor.test_soil_temperature",
                },
            },
            options={FLOW_CO2_TRIGGER: False},
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
            co2=200.0,  # Below threshold
        )

        await update_plant_sensors(hass, entry.entry_id)

        assert plant.co2_status == STATE_LOW
        assert plant.state == STATE_OK

    async def test_plant_device_soil_temperature_trigger_disabled(
        self,
        hass: HomeAssistant,
        mock_external_sensors: None,
    ) -> None:
        """Test that disabling soil temperature trigger prevents problem state."""
        from homeassistant.const import ATTR_ENTITY_PICTURE, ATTR_NAME

        from custom_components.plant.const import (
            CONF_MAX_CO2,
            CONF_MAX_CONDUCTIVITY,
            CONF_MAX_DLI,
            CONF_MAX_HUMIDITY,
            CONF_MAX_ILLUMINANCE,
            CONF_MAX_MOISTURE,
            CONF_MAX_SOIL_TEMPERATURE,
            CONF_MAX_TEMPERATURE,
            CONF_MIN_CO2,
            CONF_MIN_CONDUCTIVITY,
            CONF_MIN_DLI,
            CONF_MIN_HUMIDITY,
            CONF_MIN_ILLUMINANCE,
            CONF_MIN_MOISTURE,
            CONF_MIN_SOIL_TEMPERATURE,
            CONF_MIN_TEMPERATURE,
            DATA_SOURCE,
            FLOW_SOIL_TEMPERATURE_TRIGGER,
            OPB_DISPLAY_PID,
        )

        entry = MockConfigEntry(
            domain=DOMAIN,
            entry_id="test_entry_soil_temp_trigger_disabled",
            unique_id="test_entry_soil_temp_trigger_disabled",
            title="Test Plant",
            data={
                DATA_SOURCE: "Default values",
                FLOW_PLANT_INFO: {
                    ATTR_NAME: "Test Plant",
                    "species": "monstera deliciosa",
                    OPB_DISPLAY_PID: "Monstera deliciosa",
                    ATTR_ENTITY_PICTURE: "https://example.com/plant.jpg",
                    "limits": {
                        CONF_MAX_MOISTURE: 60,
                        CONF_MIN_MOISTURE: 20,
                        CONF_MAX_TEMPERATURE: 40,
                        CONF_MIN_TEMPERATURE: 10,
                        CONF_MAX_CONDUCTIVITY: 3000,
                        CONF_MIN_CONDUCTIVITY: 500,
                        CONF_MAX_ILLUMINANCE: 100000,
                        CONF_MIN_ILLUMINANCE: 0,
                        CONF_MAX_HUMIDITY: 60,
                        CONF_MIN_HUMIDITY: 20,
                        CONF_MAX_DLI: 30,
                        CONF_MIN_DLI: 2,
                        CONF_MAX_CO2: 2000,
                        CONF_MIN_CO2: 400,
                        CONF_MAX_SOIL_TEMPERATURE: 40,
                        CONF_MIN_SOIL_TEMPERATURE: 10,
                    },
                    "temperature_sensor": "sensor.test_temperature",
                    "moisture_sensor": "sensor.test_moisture",
                    "conductivity_sensor": "sensor.test_conductivity",
                    "illuminance_sensor": "sensor.test_illuminance",
                    "humidity_sensor": "sensor.test_humidity",
                    "co2_sensor": "sensor.test_co2",
                    "soil_temperature_sensor": "sensor.test_soil_temperature",
                },
            },
            options={FLOW_SOIL_TEMPERATURE_TRIGGER: False},
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
            soil_temperature=5.0,  # Below threshold
        )

        await update_plant_sensors(hass, entry.entry_id)

        assert plant.soil_temperature_status == STATE_LOW
        assert plant.state == STATE_OK

    async def test_plant_device_dli_status_low(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device shows problem when DLI is too low."""
        from unittest.mock import PropertyMock, patch

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Set all normal values first
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Mock DLI sensor to have a low last_period value
        # min_dli is 2, so set last_period to 1 (below threshold)
        mock_attrs = {"last_period": 1.0}
        with patch.object(
            type(plant.dli),
            "extra_state_attributes",
            new_callable=PropertyMock,
            return_value=mock_attrs,
        ):
            with patch.object(
                type(plant.dli),
                "native_value",
                new_callable=PropertyMock,
                return_value=1.0,
            ):
                with patch.object(
                    type(plant.dli),
                    "state",
                    new_callable=PropertyMock,
                    return_value="1.0",
                ):
                    plant.update()

        assert plant.dli_status == STATE_LOW
        assert plant.state == STATE_PROBLEM

    async def test_plant_device_dli_status_high(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device shows problem when DLI is too high."""
        from unittest.mock import PropertyMock, patch

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Set all normal values first
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Mock DLI sensor to have a high last_period value
        # max_dli is 30, so set last_period to 40 (above threshold)
        mock_attrs = {"last_period": 40.0}
        with patch.object(
            type(plant.dli),
            "extra_state_attributes",
            new_callable=PropertyMock,
            return_value=mock_attrs,
        ):
            with patch.object(
                type(plant.dli),
                "native_value",
                new_callable=PropertyMock,
                return_value=40.0,
            ):
                with patch.object(
                    type(plant.dli),
                    "state",
                    new_callable=PropertyMock,
                    return_value="40.0",
                ):
                    plant.update()

        assert plant.dli_status == STATE_HIGH
        assert plant.state == STATE_PROBLEM

    async def test_plant_device_dli_status_ok(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant device shows OK when DLI is within thresholds."""
        from unittest.mock import PropertyMock, patch

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Set all normal values first
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Mock DLI sensor to have a normal last_period value
        # min_dli is 2, max_dli is 30, so set last_period to 15 (within threshold)
        mock_attrs = {"last_period": 15.0}
        with patch.object(
            type(plant.dli),
            "extra_state_attributes",
            new_callable=PropertyMock,
            return_value=mock_attrs,
        ):
            with patch.object(
                type(plant.dli),
                "native_value",
                new_callable=PropertyMock,
                return_value=15.0,
            ):
                with patch.object(
                    type(plant.dli),
                    "state",
                    new_callable=PropertyMock,
                    return_value="15.0",
                ):
                    plant.update()

        assert plant.dli_status == STATE_OK
        assert plant.state == STATE_OK

    async def test_plant_status_reset_when_sensor_unavailable(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that sensor status is reset when sensor becomes unavailable."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # First set moisture to trigger problem state
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=5.0,  # Below min of 20
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Verify problem state
        assert plant.moisture_status == STATE_LOW
        assert plant.state == STATE_PROBLEM

        # Now set moisture sensor to unavailable
        hass.states.async_set("sensor.test_moisture", STATE_UNAVAILABLE)
        await hass.async_block_till_done()
        await update_plant_sensors(hass, init_integration.entry_id)

        # Moisture status should be reset
        assert plant.moisture_status is None
        # Plant should be OK since other sensors are in range
        assert plant.state == STATE_OK

    async def test_plant_status_reset_when_external_sensor_removed(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that sensor status is reset when external sensor is removed."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # First set temperature to trigger problem state
        await set_external_sensor_states(
            hass,
            temperature=50.0,  # Above max of 40
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Verify problem state
        assert plant.temperature_status == STATE_HIGH
        assert plant.state == STATE_PROBLEM

        # Remove the external sensor from the plant sensor
        plant.sensor_temperature.replace_external_sensor(None)
        await hass.async_block_till_done()
        await update_plant_sensors(hass, init_integration.entry_id)

        # Temperature status should be reset
        assert plant.temperature_status is None
        # Plant should be OK since other sensors are in range
        assert plant.state == STATE_OK

    async def test_plant_recovers_from_problem_when_dli_sensor_unavailable(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant recovers from problem state when DLI sensor becomes unavailable."""
        from unittest.mock import PropertyMock, patch

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Set normal sensor values
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Mock DLI sensor to trigger problem
        mock_attrs = {"last_period": 1.0}  # Below min_dli of 2
        with patch.object(
            type(plant.dli),
            "extra_state_attributes",
            new_callable=PropertyMock,
            return_value=mock_attrs,
        ):
            with patch.object(
                type(plant.dli),
                "native_value",
                new_callable=PropertyMock,
                return_value=1.0,
            ):
                with patch.object(
                    type(plant.dli),
                    "state",
                    new_callable=PropertyMock,
                    return_value="1.0",
                ):
                    plant.update()

        # Verify problem state
        assert plant.dli_status == STATE_LOW
        assert plant.state == STATE_PROBLEM

        # Now make DLI unavailable
        with patch.object(
            type(plant.dli),
            "native_value",
            new_callable=PropertyMock,
            return_value=STATE_UNAVAILABLE,
        ):
            plant.update()

        # DLI status should be reset
        assert plant.dli_status is None
        # Plant should recover to OK
        assert plant.state == STATE_OK


class TestYamlImport:
    """Tests for YAML configuration import (async_setup)."""

    async def test_async_setup_no_yaml_config(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test async_setup returns True when no YAML config present."""
        result = await async_setup(hass, {})
        assert result is True

    async def test_async_setup_triggers_import(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services: None,
    ) -> None:
        """Test async_setup triggers import for YAML plants."""
        yaml_config = {
            DOMAIN: {
                "my_plant": {
                    "sensors": {
                        "moisture": "sensor.moisture",
                        "temperature": "sensor.temperature",
                        "brightness": "sensor.brightness",  # Native HA uses brightness
                        "conductivity": "sensor.conductivity",
                    },
                    "min_moisture": 20,
                    "max_moisture": 60,
                    "min_brightness": 4000,
                    "max_brightness": 60000,
                    "min_temperature": 15,
                    "max_temperature": 35,
                    "min_conductivity": 500,
                    "max_conductivity": 3000,
                }
            }
        }

        with patch(
            "custom_components.plant.async_migrate_plant",
            new_callable=AsyncMock,
        ) as mock_migrate:
            result = await async_setup(hass, yaml_config)

            assert result is True
            # async_migrate_plant should be called for the plant
            assert mock_migrate.called
            assert mock_migrate.call_count == 1
            # Check it was called with the plant_id and config
            call_args = mock_migrate.call_args
            assert call_args[0][1] == "my_plant"  # plant_id

    async def test_async_setup_skips_already_imported(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test async_setup skips import when plants already imported."""
        # Add an existing config entry with SOURCE_IMPORT
        existing_entry = MockConfigEntry(
            domain=DOMAIN,
            source=SOURCE_IMPORT,
            title="Already Imported Plant",
            data={},
            entry_id="existing_import_entry",
        )
        existing_entry.add_to_hass(hass)

        yaml_config = {
            DOMAIN: {
                "my_plant": {
                    "sensors": {
                        "moisture": "sensor.moisture",
                    },
                }
            }
        }

        with patch(
            "custom_components.plant.async_migrate_plant",
            new_callable=AsyncMock,
        ) as mock_migrate:
            result = await async_setup(hass, yaml_config)

            assert result is True
            # async_migrate_plant should NOT be called since already imported
            assert not mock_migrate.called

    async def test_async_setup_skips_openplantbook_key(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services: None,
    ) -> None:
        """Test async_setup skips the openplantbook key in YAML config."""
        yaml_config = {
            DOMAIN: {
                "openplantbook": {
                    "client_id": "xxx",
                    "secret": "yyy",
                },
                "my_plant": {
                    "sensors": {
                        "moisture": "sensor.moisture",
                    },
                },
            }
        }

        with patch(
            "custom_components.plant.async_migrate_plant",
            new_callable=AsyncMock,
        ) as mock_migrate:
            result = await async_setup(hass, yaml_config)

            assert result is True
            # Should be called once for my_plant, not for openplantbook
            assert mock_migrate.call_count == 1
