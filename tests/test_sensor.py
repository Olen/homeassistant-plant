"""Tests for plant sensor entities."""

from __future__ import annotations

import pytest
from homeassistant.const import (
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import EVENT_ENTITY_REGISTRY_UPDATED
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant.const import (
    ATTR_PLANT,
    DEFAULT_LUX_TO_PPFD,
    DOMAIN,
    UNIT_DLI,
    UNIT_PPFD,
)

from .common import set_sensor_state


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

    async def test_co2_sensor(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test CO2 sensor entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_co2

        assert sensor is not None
        assert "co2" in sensor.name.lower()
        assert sensor.device_class == "carbon_dioxide"

    async def test_soil_temperature_sensor(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test soil temperature sensor entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_soil_temperature

        assert sensor is not None
        assert "soil" in sensor.name.lower() and "temperature" in sensor.name.lower()
        assert sensor.device_class == "temperature"

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
        assert (
            sensor.native_value is None or sensor.native_value == sensor._default_state
        )

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
        assert (
            sensor.native_value is None or sensor.native_value == sensor._default_state
        )

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
        assert (
            sensor.native_value is None or sensor.native_value == sensor._default_state
        )

    async def test_sensor_handles_non_numeric_external(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test sensor handles non-numeric external sensor state."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_temperature

        # Set external sensor to non-numeric value
        hass.states.async_set(
            "sensor.test_temperature",
            "invalid",
            {"unit_of_measurement": "°C"},
        )
        await hass.async_block_till_done()

        await sensor.async_update()
        # Should have default state when external value is not a valid number
        assert (
            sensor.native_value is None or sensor.native_value == sensor._default_state
        )

    async def test_sensor_handles_missing_external_entity(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test sensor handles missing external sensor entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_temperature

        # Replace with a sensor that doesn't exist
        sensor.replace_external_sensor("sensor.nonexistent_sensor")
        await hass.async_block_till_done()

        await sensor.async_update()
        # Should have default state when external sensor doesn't exist
        assert (
            sensor.native_value is None or sensor.native_value == sensor._default_state
        )


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
        illuminance_sensor = plant.sensor_illuminance

        # Set illuminance value
        lux_value = 10000
        await set_sensor_state(
            hass,
            "sensor.test_illuminance",
            lux_value,
            {"unit_of_measurement": "lx"},
        )

        # First update illuminance sensor to get external value
        await illuminance_sensor.async_update()
        illuminance_sensor.async_write_ha_state()
        await hass.async_block_till_done()

        # Then update PPFD sensor
        await ppfd_sensor.async_update()

        # Calculate expected PPFD
        expected_ppfd = lux_value * DEFAULT_LUX_TO_PPFD / 1000000
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

    async def test_total_integral_has_unit_override(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test total integral sensor has unit override method."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Verify the sensor exists and is properly set up
        assert plant.total_integral is not None
        assert plant.total_integral.name is not None
        # Verify the class has the _unit method defined
        assert hasattr(plant.total_integral, "_unit")
        assert callable(plant.total_integral._unit)


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


class TestSensorEntityIdRename:
    """Tests for sensor handling when entity IDs are renamed."""

    async def test_external_sensor_rename_updates_tracking(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that renaming an external sensor updates the tracking."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_temperature

        old_entity_id = "sensor.test_temperature"
        new_entity_id = "sensor.renamed_temperature"

        # Verify the sensor is tracking the original external sensor
        assert sensor.external_sensor == old_entity_id

        # Create the new sensor state
        hass.states.async_set(
            new_entity_id,
            "25.0",
            {"unit_of_measurement": "°C"},
        )
        await hass.async_block_till_done()

        # Fire entity registry update event (simulating a rename)
        hass.bus.async_fire(
            EVENT_ENTITY_REGISTRY_UPDATED,
            {
                "action": "update",
                "entity_id": new_entity_id,
                "old_entity_id": old_entity_id,
                "changes": {"entity_id": new_entity_id},
            },
        )
        await hass.async_block_till_done()

        # Verify the sensor updated its external sensor reference
        assert sensor.external_sensor == new_entity_id

    async def test_non_rename_update_does_not_change_tracking(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that non-rename updates don't affect tracking."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_temperature

        original_external = sensor.external_sensor

        # Fire entity registry update event without old_entity_id (not a rename)
        hass.bus.async_fire(
            EVENT_ENTITY_REGISTRY_UPDATED,
            {
                "action": "update",
                "entity_id": "sensor.some_other_sensor",
                "changes": {"friendly_name": "New Name"},
            },
        )
        await hass.async_block_till_done()

        # Verify the external sensor reference is unchanged
        assert sensor.external_sensor == original_external

    async def test_unrelated_entity_rename_does_not_change_tracking(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that renaming an unrelated entity doesn't affect tracking."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_temperature

        original_external = sensor.external_sensor

        # Fire entity registry update event for an unrelated entity
        hass.bus.async_fire(
            EVENT_ENTITY_REGISTRY_UPDATED,
            {
                "action": "update",
                "entity_id": "sensor.completely_unrelated",
                "old_entity_id": "sensor.old_unrelated",
                "changes": {"entity_id": "sensor.completely_unrelated"},
            },
        )
        await hass.async_block_till_done()

        # Verify the external sensor reference is unchanged
        assert sensor.external_sensor == original_external

    async def test_total_integral_source_rename_updates_tracking(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that renaming the PPFD sensor updates the total integral tracking."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        integral_sensor = plant.total_integral
        ppfd_sensor = plant.ppfd

        old_entity_id = ppfd_sensor.entity_id
        new_entity_id = "sensor.renamed_ppfd"

        # Verify the integral sensor is tracking the PPFD sensor
        assert integral_sensor._source_entity == old_entity_id

        # Fire entity registry update event (simulating a rename)
        hass.bus.async_fire(
            EVENT_ENTITY_REGISTRY_UPDATED,
            {
                "action": "update",
                "entity_id": new_entity_id,
                "old_entity_id": old_entity_id,
                "changes": {"entity_id": new_entity_id},
            },
        )
        await hass.async_block_till_done()

        # Verify the integral sensor updated its source reference
        assert integral_sensor._source_entity == new_entity_id
        assert integral_sensor._sensor_source_id == new_entity_id

    async def test_dli_source_rename_updates_tracking(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that renaming the integral sensor updates the DLI tracking."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        dli_sensor = plant.dli
        integral_sensor = plant.total_integral

        old_entity_id = integral_sensor.entity_id
        new_entity_id = "sensor.renamed_integral"

        # Verify the DLI sensor is tracking the integral sensor
        assert dli_sensor._sensor_source_id == old_entity_id

        # Fire entity registry update event (simulating a rename)
        hass.bus.async_fire(
            EVENT_ENTITY_REGISTRY_UPDATED,
            {
                "action": "update",
                "entity_id": new_entity_id,
                "old_entity_id": old_entity_id,
                "changes": {"entity_id": new_entity_id},
            },
        )
        await hass.async_block_till_done()

        # Verify the DLI sensor updated its source reference
        assert dli_sensor._sensor_source_id == new_entity_id


class TestSensorRemovalAndConfigPersistence:
    """Tests for sensor removal handling and config entry persistence."""

    async def test_external_sensor_deletion_clears_reference(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that deleting an external sensor clears the reference."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_temperature

        original_external = "sensor.test_temperature"
        assert sensor.external_sensor == original_external

        # Fire entity registry remove event (simulating deletion)
        hass.bus.async_fire(
            EVENT_ENTITY_REGISTRY_UPDATED,
            {
                "action": "remove",
                "entity_id": original_external,
            },
        )
        await hass.async_block_till_done()

        # Verify the external sensor reference was cleared
        assert sensor.external_sensor is None

    async def test_unrelated_sensor_deletion_does_not_clear_reference(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that deleting an unrelated sensor doesn't affect tracking."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_temperature

        original_external = sensor.external_sensor

        # Fire entity registry remove event for an unrelated entity
        hass.bus.async_fire(
            EVENT_ENTITY_REGISTRY_UPDATED,
            {
                "action": "remove",
                "entity_id": "sensor.completely_unrelated",
            },
        )
        await hass.async_block_till_done()

        # Verify the external sensor reference is unchanged
        assert sensor.external_sensor == original_external

    async def test_replace_sensor_updates_config_entry(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that replacing a sensor updates the config entry."""
        from custom_components.plant.const import (
            FLOW_PLANT_INFO,
            FLOW_SENSOR_TEMPERATURE,
        )

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_temperature

        original_external = "sensor.test_temperature"
        new_external = "sensor.new_temperature"
        assert sensor.external_sensor == original_external

        # Set up the new sensor state
        hass.states.async_set(
            new_external,
            "25.0",
            {"unit_of_measurement": "°C"},
        )
        await hass.async_block_till_done()

        # Replace the external sensor
        sensor.replace_external_sensor(new_external)
        await hass.async_block_till_done()

        # Verify the sensor reference was updated
        assert sensor.external_sensor == new_external

        # Verify the config entry was updated
        entry = hass.config_entries.async_get_entry(init_integration.entry_id)
        assert entry is not None
        assert entry.data[FLOW_PLANT_INFO][FLOW_SENSOR_TEMPERATURE] == new_external

    async def test_remove_sensor_updates_config_entry(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that removing a sensor (setting to None) updates the config entry."""
        from custom_components.plant.const import (
            FLOW_PLANT_INFO,
            FLOW_SENSOR_MOISTURE,
        )

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_moisture

        original_external = "sensor.test_moisture"
        assert sensor.external_sensor == original_external

        # Remove the external sensor
        sensor.replace_external_sensor(None)
        await hass.async_block_till_done()

        # Verify the sensor reference was cleared
        assert sensor.external_sensor is None

        # Verify the config entry was updated
        entry = hass.config_entries.async_get_entry(init_integration.entry_id)
        assert entry is not None
        assert entry.data[FLOW_PLANT_INFO][FLOW_SENSOR_MOISTURE] is None

    async def test_external_sensor_deletion_updates_config_entry(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that deleting an external sensor also updates the config entry."""
        from custom_components.plant.const import (
            FLOW_PLANT_INFO,
            FLOW_SENSOR_ILLUMINANCE,
        )

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        sensor = plant.sensor_illuminance

        original_external = "sensor.test_illuminance"
        assert sensor.external_sensor == original_external

        # Fire entity registry remove event (simulating deletion)
        hass.bus.async_fire(
            EVENT_ENTITY_REGISTRY_UPDATED,
            {
                "action": "remove",
                "entity_id": original_external,
            },
        )
        await hass.async_block_till_done()

        # Verify the external sensor reference was cleared
        assert sensor.external_sensor is None

        # Verify the config entry was updated
        entry = hass.config_entries.async_get_entry(init_integration.entry_id)
        assert entry is not None
        assert entry.data[FLOW_PLANT_INFO][FLOW_SENSOR_ILLUMINANCE] is None

    async def test_all_sensors_have_config_keys(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that all current status sensors have config keys defined."""
        from custom_components.plant.const import (
            FLOW_SENSOR_CO2,
            FLOW_SENSOR_CONDUCTIVITY,
            FLOW_SENSOR_HUMIDITY,
            FLOW_SENSOR_ILLUMINANCE,
            FLOW_SENSOR_MOISTURE,
            FLOW_SENSOR_SOIL_TEMPERATURE,
            FLOW_SENSOR_TEMPERATURE,
        )

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Verify all sensors have the expected config keys
        assert plant.sensor_temperature._config_key == FLOW_SENSOR_TEMPERATURE
        assert plant.sensor_moisture._config_key == FLOW_SENSOR_MOISTURE
        assert plant.sensor_conductivity._config_key == FLOW_SENSOR_CONDUCTIVITY
        assert plant.sensor_illuminance._config_key == FLOW_SENSOR_ILLUMINANCE
        assert plant.sensor_humidity._config_key == FLOW_SENSOR_HUMIDITY
        assert plant.sensor_co2._config_key == FLOW_SENSOR_CO2
        assert plant.sensor_soil_temperature._config_key == FLOW_SENSOR_SOIL_TEMPERATURE


class TestDliSensorsWhenIlluminanceRemoved:
    """Tests for DLI-related sensors when illuminance sensor is removed."""

    async def test_ppfd_becomes_none_when_illuminance_external_removed(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that PPFD becomes None when illuminance external sensor is removed."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        illuminance_sensor = plant.sensor_illuminance
        ppfd_sensor = plant.ppfd

        # Update illuminance sensor to get value from external sensor
        illuminance_sensor.async_schedule_update_ha_state(True)
        await hass.async_block_till_done()

        # Verify illuminance has a value from the external sensor
        assert illuminance_sensor.native_value is not None

        # Update PPFD to get calculated value
        ppfd_sensor.async_schedule_update_ha_state(True)
        await hass.async_block_till_done()

        # PPFD should have a value when illuminance is available
        assert ppfd_sensor.native_value is not None

        # Remove the external sensor from the illuminance sensor
        illuminance_sensor.replace_external_sensor(None)
        await hass.async_block_till_done()

        # Trigger full update of illuminance sensor to update HA state
        illuminance_sensor.async_schedule_update_ha_state(True)
        await hass.async_block_till_done()

        # Illuminance sensor's value should now be None (default)
        assert illuminance_sensor.native_value is None

        # Update PPFD to reflect the change (it reads from illuminance sensor's state)
        ppfd_sensor.async_schedule_update_ha_state(True)
        await hass.async_block_till_done()

        # PPFD should become None when illuminance has no value
        assert ppfd_sensor.native_value is None

    async def test_illuminance_sensor_deletion_affects_ppfd(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that deleting the illuminance external sensor affects PPFD."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        illuminance_sensor = plant.sensor_illuminance
        ppfd_sensor = plant.ppfd

        original_external = "sensor.test_illuminance"
        assert illuminance_sensor.external_sensor == original_external

        # Fire entity registry remove event (simulating deletion)
        hass.bus.async_fire(
            EVENT_ENTITY_REGISTRY_UPDATED,
            {
                "action": "remove",
                "entity_id": original_external,
            },
        )
        await hass.async_block_till_done()

        # Verify illuminance external sensor was cleared
        assert illuminance_sensor.external_sensor is None

        # Update PPFD to reflect the change
        ppfd_sensor.async_schedule_update_ha_state(True)
        await hass.async_block_till_done()

        # PPFD should become None
        assert ppfd_sensor.native_value is None
