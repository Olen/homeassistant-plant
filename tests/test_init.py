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
from homeassistant.helpers import device_registry as dr, entity_registry as er
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

        # Verify the main plant entity is tied to the config entry
        plant_entity_id = entity_registry.async_get_entity_id(DOMAIN, DOMAIN, entry_id)
        assert plant_entity_id is not None
        plant_entry = entity_registry.async_get(plant_entity_id)
        assert plant_entry.config_entry_id == entry_id

        # Remove the config entry (this calls async_remove_entry)
        await hass.config_entries.async_remove(entry_id)
        await hass.async_block_till_done()

        # Verify entities are removed from registry
        entities_after = er.async_entries_for_config_entry(entity_registry, entry_id)
        assert len(entities_after) == 0

        # Verify the main plant entity is also removed
        assert entity_registry.async_get(plant_entity_id) is None

        # Verify device is removed from registry
        device_after = device_registry.async_get_device(
            identifiers={(DOMAIN, entry_id)}
        )
        assert device_after is None

    async def test_setup_completes_when_registry_entry_not_immediate(
        self,
        hass: HomeAssistant,
        mock_external_sensors: None,
    ) -> None:
        """Test setup completes gracefully when registry_entry is None initially.

        The function should retry with registry lookup and give up gracefully
        instead of blocking the entire setup with ConfigEntryNotReady.
        """
        from tests.conftest import create_plant_config_data

        config_data = create_plant_config_data()
        entry = MockConfigEntry(
            domain=DOMAIN,
            data=config_data,
            entry_id="test_registry_delayed",
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Setup should complete successfully (not stuck in SETUP_RETRY)
        assert entry.state.name == "LOADED"

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

    async def test_plant_device_species_capitalization(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test plant species is capitalized correctly (binomial nomenclature).

        The genus (first word) should be capitalized, rest should be preserved.
        E.g., "monstera deliciosa" -> "Monstera deliciosa"
        """
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        plant.plant_complete = True
        plant.update()

        attrs = plant.extra_state_attributes
        species = attrs["species"]

        # First letter should be uppercase
        assert species[0].isupper(), f"First letter should be uppercase: {species}"
        # Species should be "Monstera deliciosa" (first word capitalized)
        assert species == "Monstera deliciosa"

    async def test_plant_device_species_capitalization_lowercase_input(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test species capitalization when input is all lowercase."""
        from tests.conftest import create_plant_config_data

        # Create config with all lowercase display_species
        config_data = create_plant_config_data(
            display_species="solanum lycopersicum",
        )

        entry = MockConfigEntry(
            domain=DOMAIN,
            data=config_data,
            entry_id="test_lowercase_species",
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]
        plant.plant_complete = True
        plant.update()

        attrs = plant.extra_state_attributes
        species = attrs["species"]

        # First letter should be uppercase, rest preserved
        assert species == "Solanum lycopersicum"

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
            CONF_MAX_VPD,
            CONF_MIN_CONDUCTIVITY,
            CONF_MIN_DLI,
            CONF_MIN_HUMIDITY,
            CONF_MIN_ILLUMINANCE,
            CONF_MIN_MOISTURE,
            CONF_MIN_TEMPERATURE,
            CONF_MIN_VPD,
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
                        CONF_MAX_VPD: 1.6,
                        CONF_MIN_VPD: 0.4,
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

    async def test_plant_device_add_media_source_image(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test adding a media-source image passes through as-is."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        media_source_url = "media-source://media_source/local/plants/test.jpg"
        plant.add_image(media_source_url)

        # The entity_picture should be the media-source URL (passed through)
        assert plant.entity_picture == media_source_url

        # The config entry should also store the media-source URL
        assert init_integration.options.get("entity_picture") == media_source_url

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
            CONF_MAX_VPD,
            CONF_MIN_CONDUCTIVITY,
            CONF_MIN_DLI,
            CONF_MIN_HUMIDITY,
            CONF_MIN_ILLUMINANCE,
            CONF_MIN_MOISTURE,
            CONF_MIN_TEMPERATURE,
            CONF_MIN_VPD,
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
                        CONF_MAX_VPD: 1.6,
                        CONF_MIN_VPD: 0.4,
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
            CONF_MAX_VPD,
            CONF_MIN_CONDUCTIVITY,
            CONF_MIN_DLI,
            CONF_MIN_HUMIDITY,
            CONF_MIN_ILLUMINANCE,
            CONF_MIN_MOISTURE,
            CONF_MIN_TEMPERATURE,
            CONF_MIN_VPD,
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
                        CONF_MAX_VPD: 1.6,
                        CONF_MIN_VPD: 0.4,
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
            CONF_MAX_VPD,
            CONF_MIN_CO2,
            CONF_MIN_CONDUCTIVITY,
            CONF_MIN_DLI,
            CONF_MIN_HUMIDITY,
            CONF_MIN_ILLUMINANCE,
            CONF_MIN_MOISTURE,
            CONF_MIN_SOIL_TEMPERATURE,
            CONF_MIN_TEMPERATURE,
            CONF_MIN_VPD,
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
                        CONF_MAX_VPD: 1.6,
                        CONF_MIN_VPD: 0.4,
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
            CONF_MAX_VPD,
            CONF_MIN_CO2,
            CONF_MIN_CONDUCTIVITY,
            CONF_MIN_DLI,
            CONF_MIN_HUMIDITY,
            CONF_MIN_ILLUMINANCE,
            CONF_MIN_MOISTURE,
            CONF_MIN_SOIL_TEMPERATURE,
            CONF_MIN_TEMPERATURE,
            CONF_MIN_VPD,
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
                        CONF_MAX_VPD: 1.6,
                        CONF_MIN_VPD: 0.4,
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


class TestHysteresis:
    """Tests for hysteresis behavior on threshold checks."""

    async def test_moisture_low_holds_within_hysteresis_band(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that moisture LOW state holds when value is within hysteresis band.

        Default moisture: min=20, max=60, range=40, band=2.0 (5% of 40).
        Enters PROBLEM at <20, should stay PROBLEM until >22.
        """
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Step 1: Drop below min → PROBLEM
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=15.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.moisture_status == STATE_LOW
        assert plant.state == STATE_PROBLEM

        # Step 2: Rise to just above min but within band (20.5 < 20 + 2 = 22)
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=20.5,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.moisture_status == STATE_LOW  # Still held
        assert plant.state == STATE_PROBLEM

        # Step 3: Rise above band (23 > 22) → clears to OK
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=23.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.moisture_status == STATE_OK
        assert plant.state == STATE_OK

    async def test_moisture_high_holds_within_hysteresis_band(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that moisture HIGH state holds when value is within hysteresis band.

        Default moisture: min=20, max=60, range=40, band=2.0.
        Enters PROBLEM at >60, should stay PROBLEM until <58.
        """
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Step 1: Rise above max → PROBLEM
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=65.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.moisture_status == STATE_HIGH
        assert plant.state == STATE_PROBLEM

        # Step 2: Drop to just below max but within band (59.0 >= 60 - 2 = 58)
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=59.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.moisture_status == STATE_HIGH  # Still held
        assert plant.state == STATE_PROBLEM

        # Step 3: Drop below band (57.0 < 58) → clears to OK
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=57.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.moisture_status == STATE_OK
        assert plant.state == STATE_OK

    async def test_temperature_low_holds_within_hysteresis_band(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test temperature LOW hysteresis.

        Default temperature: min=10, max=40, range=30, band=1.5.
        Enters at <10, clears at >11.5.
        """
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Drop below min
        await set_external_sensor_states(
            hass,
            temperature=8.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.temperature_status == STATE_LOW

        # Rise within band (11.0 <= 10 + 1.5 = 11.5)
        await set_external_sensor_states(
            hass,
            temperature=11.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.temperature_status == STATE_LOW  # held

        # Rise above band (12.0 > 11.5)
        await set_external_sensor_states(
            hass,
            temperature=12.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.temperature_status == STATE_OK

    async def test_no_hysteresis_on_fresh_state(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that hysteresis does not apply when state is fresh (None).

        A value within the hysteresis band but above the min threshold
        should be OK on first check, not held as LOW.
        """
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Ensure fresh state (moisture_status is None before any reading)
        assert plant.moisture_status is None

        # Set moisture within hysteresis band (21 is > min=20 but < min+band=22)
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=21.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Should be OK, not LOW — no previous LOW state to hold
        assert plant.moisture_status == STATE_OK
        assert plant.state == STATE_OK

    async def test_hysteresis_resets_on_sensor_unavailable(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that hysteresis state resets when sensor becomes unavailable.

        After reset, returning within band should be OK (fresh state).
        """
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Enter PROBLEM
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=15.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.moisture_status == STATE_LOW

        # Sensor goes unavailable → status reset
        hass.states.async_set("sensor.test_moisture", STATE_UNAVAILABLE)
        await hass.async_block_till_done()
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.moisture_status is None

        # Value returns within hysteresis band → should be OK (no held state)
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=21.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.moisture_status == STATE_OK

    async def test_illuminance_high_holds_within_hysteresis_band(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test illuminance HIGH hysteresis (max-only check).

        Default illuminance: min=0, max=100000, range=100000, band=5000.
        Enters at >100000, clears at <95000.
        """
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Rise above max
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=110000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.illuminance_status == STATE_HIGH
        assert plant.state == STATE_PROBLEM

        # Drop within band (96000 >= 100000 - 5000 = 95000)
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=96000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.illuminance_status == STATE_HIGH  # held
        assert plant.state == STATE_PROBLEM

        # Drop below band (94000 < 95000)
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=94000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.illuminance_status == STATE_OK
        assert plant.state == STATE_OK

    async def test_dli_low_holds_within_hysteresis_band(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test DLI LOW hysteresis.

        Default DLI: min=2, max=30, range=28, band=1.4.
        Enters at <2, clears at >3.4.
        """
        from unittest.mock import PropertyMock, patch

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Set normal sensor values first
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        def mock_dli(last_period):
            """Context manager to mock DLI sensor with given last_period."""
            mock_attrs = {"last_period": last_period}
            return (
                patch.object(
                    type(plant.dli),
                    "extra_state_attributes",
                    new_callable=PropertyMock,
                    return_value=mock_attrs,
                ),
                patch.object(
                    type(plant.dli),
                    "native_value",
                    new_callable=PropertyMock,
                    return_value=last_period,
                ),
                patch.object(
                    type(plant.dli),
                    "state",
                    new_callable=PropertyMock,
                    return_value=str(last_period),
                ),
            )

        # Step 1: Drop below min (1.0 < 2)
        p1, p2, p3 = mock_dli(1.0)
        with p1, p2, p3:
            plant.update()
        assert plant.dli_status == STATE_LOW
        assert plant.state == STATE_PROBLEM

        # Step 2: Rise within band (2.5 <= 2 + 1.4 = 3.4) → still LOW
        p1, p2, p3 = mock_dli(2.5)
        with p1, p2, p3:
            plant.update()
        assert plant.dli_status == STATE_LOW
        assert plant.state == STATE_PROBLEM

        # Step 3: Rise above band (4.0 > 3.4) → clears
        p1, p2, p3 = mock_dli(4.0)
        with p1, p2, p3:
            plant.update()
        assert plant.dli_status == STATE_OK
        assert plant.state == STATE_OK

    async def test_conductivity_hysteresis(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test conductivity hysteresis.

        Default conductivity: min=500, max=3000, range=2500, band=125.
        Enters LOW at <500, clears at >625.
        """
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Drop below min
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=400.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.conductivity_status == STATE_LOW

        # Rise within band (600 <= 500 + 125 = 625)
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=600.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.conductivity_status == STATE_LOW  # held

        # Rise above band (650 > 625)
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=650.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.conductivity_status == STATE_OK

    async def test_threshold_unavailable_preserves_status(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that unavailable threshold entities don't crash _check_threshold.

        When a threshold number entity has state 'unavailable', the plant
        should keep its current status rather than raising ValueError.
        """
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # First establish a known state
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.state == STATE_OK
        assert plant.moisture_status == STATE_OK

        # Make the min_moisture threshold entity unavailable
        hass.states.async_set(plant.min_moisture.entity_id, STATE_UNAVAILABLE)
        await hass.async_block_till_done()

        # Update should not crash — moisture_status should be preserved
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.moisture_status == STATE_OK

    async def test_threshold_unknown_preserves_status(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that unknown threshold entities don't crash _check_threshold."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Establish a LOW moisture state
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=5.0,  # Below min of 20
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.moisture_status == STATE_LOW

        # Make the max_moisture threshold entity unknown
        hass.states.async_set(plant.max_moisture.entity_id, STATE_UNKNOWN)
        await hass.async_block_till_done()

        # Update should not crash — moisture_status should stay LOW
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.moisture_status == STATE_LOW


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


class TestMoistureGracePeriod:
    """Tests for moisture grace period feature after watering."""

    async def test_grace_period_suppresses_high_moisture_alert(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that grace period suppresses high moisture alerts after watering.

        Scenario:
        1. Start with normal moisture (40%)
        2. Water plant - moisture jumps by 15% (to 55%)
        3. Grace period activates
        4. Moisture rises above threshold (65% > 60%)
        5. Verify problem is NOT reported during grace period
        """
        from homeassistant.util import dt as dt_util

        from custom_components.plant.const import (
            FLOW_MOISTURE_GRACE_PERIOD,
        )

        # Configure grace period of 3600 seconds (1 hour)
        hass.config_entries.async_update_entry(
            init_integration, options={FLOW_MOISTURE_GRACE_PERIOD: 3600}
        )
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Step 1: Start with normal moisture
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.state == STATE_OK
        assert plant.moisture_status == STATE_OK
        assert plant._last_moisture_value == 40.0
        assert plant._moisture_grace_end_time is None

        # Step 2: Simulate watering - moisture increases by 15% (triggers grace period)
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=55.0,  # Increased by 15% from 40%
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Grace period should be activated
        assert plant._last_moisture_value == 55.0
        assert plant._moisture_grace_end_time is not None
        # Grace period should be set to approximately now + 3600 seconds
        grace_remaining = (
            plant._moisture_grace_end_time - dt_util.now()
        ).total_seconds()
        assert (
            3595 < grace_remaining < 3605
        ), f"Grace period remaining: {grace_remaining}"

        # Step 3: Moisture rises above max threshold (65% > 60%)
        # But grace period is still active - should NOT report problem
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=65.0,  # Above max of 60
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Moisture is high but grace period suppresses the problem
        assert plant.moisture_status == STATE_HIGH
        assert plant.state == STATE_OK  # No problem reported!
        assert plant._last_moisture_value == 65.0

    async def test_low_moisture_triggers_during_grace_period(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that low moisture alerts still trigger during grace period.

        Grace period only suppresses HIGH moisture problems, not LOW.
        This ensures we still get alerts if plant needs water.
        """
        from datetime import timedelta
        from unittest.mock import patch

        from custom_components.plant.const import FLOW_MOISTURE_GRACE_PERIOD

        # Configure grace period
        hass.config_entries.async_update_entry(
            init_integration, options={FLOW_MOISTURE_GRACE_PERIOD: 3600}
        )
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Start with normal moisture
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Trigger watering detection
        with patch("custom_components.plant.dt_util.now") as mock_now:
            from homeassistant.util import dt as dt_util

            base_time = dt_util.now()
            mock_now.return_value = base_time

            await set_external_sensor_states(hass, moisture=55.0)
            await update_plant_sensors(hass, init_integration.entry_id)

            # Grace period active
            assert plant._moisture_grace_end_time is not None

        # Now moisture drops LOW during grace period
        with patch("custom_components.plant.dt_util.now") as mock_now:
            current_time = base_time + timedelta(minutes=15)
            mock_now.return_value = current_time

            await set_external_sensor_states(
                hass,
                temperature=25.0,
                moisture=15.0,  # Below min of 20
                conductivity=1000.0,
                illuminance=5000.0,
                humidity=40.0,
            )
            await update_plant_sensors(hass, init_integration.entry_id)

            # LOW moisture should trigger problem even during grace period
            assert plant.moisture_status == STATE_LOW
            assert plant.state == STATE_PROBLEM
            assert plant._last_moisture_value == 15.0

    async def test_grace_period_expiration_enables_high_alerts(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
        freezer,
    ) -> None:
        """Test that high moisture alerts trigger after grace period expires.

        Scenario:
        1. Activate grace period
        2. Moisture goes high during grace period (suppressed)
        3. Time advances past grace period end
        4. Update sensors - problem should now be reported
        """
        from datetime import timedelta

        from homeassistant.util import dt as dt_util

        from custom_components.plant.const import FLOW_MOISTURE_GRACE_PERIOD

        # Short grace period for testing
        hass.config_entries.async_update_entry(
            init_integration, options={FLOW_MOISTURE_GRACE_PERIOD: 600}
        )
        await hass.async_block_till_done()  # 10 minutes

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Start normal
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Freeze time at a known point
        base_time = dt_util.now()
        freezer.move_to(base_time)

        # Water plant
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=55.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Moisture goes high
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=65.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Problem suppressed during grace period
        assert plant.moisture_status == STATE_HIGH
        assert plant.state == STATE_OK

        # Advance time past grace period (15 minutes > 10 minutes)
        freezer.move_to(base_time + timedelta(minutes=15))

        # Trigger update - moisture still high
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=65.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Grace period expired - problem should now be reported
        assert plant.moisture_status == STATE_HIGH
        assert plant.state == STATE_PROBLEM
        # Grace end time should be cleared
        assert plant._moisture_grace_end_time is None

    async def test_grace_period_zero_means_no_suppression(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that grace period of 0 disables the feature entirely.

        With grace period = 0, high moisture should trigger immediately.
        """
        from custom_components.plant.const import FLOW_MOISTURE_GRACE_PERIOD

        # Disable grace period
        hass.config_entries.async_update_entry(
            init_integration, options={FLOW_MOISTURE_GRACE_PERIOD: 0}
        )
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Start normal
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant.state == STATE_OK

        # Large moisture increase (would normally trigger grace period)
        await set_external_sensor_states(hass, moisture=55.0)
        await update_plant_sensors(hass, init_integration.entry_id)

        # No grace period should be set
        assert plant._moisture_grace_end_time is None

        # High moisture should trigger problem immediately
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=65.0,  # Above max of 60
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Problem should be reported immediately (no grace period)
        assert plant.moisture_status == STATE_HIGH
        assert plant.state == STATE_PROBLEM

    async def test_sensor_unavailable_resets_tracking_state(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that sensor becoming unavailable resets grace period tracking.

        When moisture sensor goes unavailable, we should reset:
        - _last_moisture_value
        - _moisture_grace_end_time
        - moisture_status
        """
        from unittest.mock import patch

        from custom_components.plant.const import FLOW_MOISTURE_GRACE_PERIOD

        hass.config_entries.async_update_entry(
            init_integration, options={FLOW_MOISTURE_GRACE_PERIOD: 3600}
        )
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Start with moisture data and active grace period
        with patch("custom_components.plant.dt_util.now") as mock_now:
            from homeassistant.util import dt as dt_util

            base_time = dt_util.now()
            mock_now.return_value = base_time

            await set_external_sensor_states(hass, moisture=40.0)
            await update_plant_sensors(hass, init_integration.entry_id)

            # Trigger watering
            await set_external_sensor_states(hass, moisture=55.0)
            await update_plant_sensors(hass, init_integration.entry_id)

            # Verify grace period is active
            assert plant._last_moisture_value == 55.0
            assert plant._moisture_grace_end_time is not None

        # Make moisture sensor unavailable
        hass.states.async_set("sensor.test_moisture", STATE_UNAVAILABLE)
        await update_plant_sensors(hass, init_integration.entry_id)

        # All tracking state should be reset
        assert plant._last_moisture_value is None
        assert plant._moisture_grace_end_time is None
        assert plant.moisture_status is None

    async def test_sensor_removed_resets_tracking_state(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that removing moisture sensor resets grace period tracking."""
        from unittest.mock import patch

        from custom_components.plant.const import FLOW_MOISTURE_GRACE_PERIOD

        hass.config_entries.async_update_entry(
            init_integration, options={FLOW_MOISTURE_GRACE_PERIOD: 3600}
        )
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Setup active grace period
        with patch("custom_components.plant.dt_util.now") as mock_now:
            from homeassistant.util import dt as dt_util

            base_time = dt_util.now()
            mock_now.return_value = base_time

            await set_external_sensor_states(hass, moisture=40.0)
            await update_plant_sensors(hass, init_integration.entry_id)

            await set_external_sensor_states(hass, moisture=55.0)
            await update_plant_sensors(hass, init_integration.entry_id)

            assert plant._moisture_grace_end_time is not None

        # Remove the moisture sensor
        plant.sensor_moisture = None
        plant.update()

        # Tracking state should be reset
        assert plant._last_moisture_value is None
        assert plant._moisture_grace_end_time is None
        assert plant.moisture_status is None

    async def test_sensor_non_numeric_resets_tracking_state(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that non-numeric sensor value resets grace period tracking."""
        from unittest.mock import patch

        from custom_components.plant.const import FLOW_MOISTURE_GRACE_PERIOD

        hass.config_entries.async_update_entry(
            init_integration, options={FLOW_MOISTURE_GRACE_PERIOD: 3600}
        )
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Setup active grace period
        with patch("custom_components.plant.dt_util.now") as mock_now:
            from homeassistant.util import dt as dt_util

            base_time = dt_util.now()
            mock_now.return_value = base_time

            await set_external_sensor_states(hass, moisture=40.0)
            await update_plant_sensors(hass, init_integration.entry_id)

            await set_external_sensor_states(hass, moisture=55.0)
            await update_plant_sensors(hass, init_integration.entry_id)

            assert plant._moisture_grace_end_time is not None

        # Set sensor to non-numeric value
        hass.states.async_set("sensor.test_moisture", "unknown")
        await update_plant_sensors(hass, init_integration.entry_id)

        # Tracking state should be reset
        assert plant._last_moisture_value is None
        assert plant._moisture_grace_end_time is None
        assert plant.moisture_status is None

    async def test_small_moisture_increase_does_not_trigger_grace_period(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that small moisture increases don't activate grace period.

        Only increases >= MOISTURE_INCREASE_THRESHOLD (10%) trigger grace period.
        """
        from custom_components.plant.const import FLOW_MOISTURE_GRACE_PERIOD

        hass.config_entries.async_update_entry(
            init_integration, options={FLOW_MOISTURE_GRACE_PERIOD: 3600}
        )
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Start at 40%
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant._last_moisture_value == 40.0
        assert plant._moisture_grace_end_time is None

        # Increase by only 5% (below 10% threshold)
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=45.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Grace period should NOT be activated
        assert plant._last_moisture_value == 45.0
        assert plant._moisture_grace_end_time is None

        # Now if moisture goes high, problem should be reported immediately
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=54.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Still no grace period
        assert plant._moisture_grace_end_time is None

        # Now jump to 65% (11% increase from 54%, triggers grace period but too late)
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Now increase by 7% (below 10% threshold) multiple times to get above max
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=47.0,  # +7%
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant._moisture_grace_end_time is None

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=54.0,  # +7%
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)
        assert plant._moisture_grace_end_time is None

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=61.0,  # +7%, now above max of 60
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Grace period should still NOT be activated (only 7% increase each time)
        assert plant._moisture_grace_end_time is None
        # Problem should be reported immediately (no grace period)
        assert plant.moisture_status == STATE_HIGH
        assert plant.state == STATE_PROBLEM

    async def test_grace_period_default_value(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that default grace period value is 0 (disabled)."""
        from custom_components.plant.const import DEFAULT_MOISTURE_GRACE_PERIOD

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Default should be 0
        assert DEFAULT_MOISTURE_GRACE_PERIOD == 0
        assert plant.moisture_grace_period == 0

    async def test_multiple_watering_events_reset_grace_period(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that each watering event resets the grace period timer.

        If plant is watered multiple times, each watering should start
        a new grace period.
        """
        from custom_components.plant.const import FLOW_MOISTURE_GRACE_PERIOD

        hass.config_entries.async_update_entry(
            init_integration, options={FLOW_MOISTURE_GRACE_PERIOD: 3600}
        )
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # First watering
        from homeassistant.util import dt as dt_util

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=40.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=55.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        first_grace_end = plant._moisture_grace_end_time
        assert first_grace_end is not None
        # Grace period should be approximately 3600 seconds from now
        first_remaining = (first_grace_end - dt_util.now()).total_seconds()
        assert 3595 < first_remaining < 3605

        # Second watering (moisture drops slightly then increases again)
        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=50.0,
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        await set_external_sensor_states(
            hass,
            temperature=25.0,
            moisture=65.0,  # +15% increase triggers new grace period
            conductivity=1000.0,
            illuminance=5000.0,
            humidity=40.0,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        second_grace_end = plant._moisture_grace_end_time
        # New grace period should be set (later than first one)
        assert second_grace_end is not None
        assert second_grace_end > first_grace_end
