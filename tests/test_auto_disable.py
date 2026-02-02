"""Tests for auto-disable of entities when no external sensor is configured."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant.const import (
    ATTR_PLANT,
    DOMAIN,
    SERVICE_REPLACE_SENSOR,
)

from .conftest import (
    TEST_ENTRY_ID,
    create_plant_config_data,
    setup_mock_external_sensors,
)


class TestAutoDisableOnSetup:
    """Tests for entity auto-disable during integration setup."""

    async def test_entities_disabled_on_setup_no_sensors(
        self,
        hass: HomeAssistant,
        init_integration_no_sensors: MockConfigEntry,
    ) -> None:
        """All meter sensors and thresholds should be disabled when no external sensors configured."""
        ent_reg = er.async_get(hass)
        plant = hass.data[DOMAIN][init_integration_no_sensors.entry_id][ATTR_PLANT]

        # Check all meter sensors are disabled
        for meter in plant.meter_entities:
            entry = ent_reg.async_get(meter.entity_id)
            assert entry is not None, f"Entity {meter.entity_id} not in registry"
            assert (
                entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION
            ), f"{meter.entity_id} should be disabled"

        # Check all threshold entities are disabled
        for threshold in plant.threshold_entities:
            entry = ent_reg.async_get(threshold.entity_id)
            assert entry is not None, f"Entity {threshold.entity_id} not in registry"
            assert (
                entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION
            ), f"{threshold.entity_id} should be disabled"

        # Check illuminance-derived entities are disabled
        for entity in [plant.ppfd, plant.total_integral, plant.dli, plant.dli_24h]:
            if entity is None:
                continue
            entry = ent_reg.async_get(entity.entity_id)
            assert entry is not None, f"Entity {entity.entity_id} not in registry"
            assert (
                entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION
            ), f"{entity.entity_id} should be disabled"

    async def test_entities_enabled_on_setup_with_sensors(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """No entities should be integration-disabled when all external sensors configured."""
        ent_reg = er.async_get(hass)
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        for meter in plant.meter_entities:
            entry = ent_reg.async_get(meter.entity_id)
            assert entry is not None
            assert (
                entry.disabled_by != er.RegistryEntryDisabler.INTEGRATION
            ), f"{meter.entity_id} should not be integration-disabled"

        for threshold in plant.threshold_entities:
            entry = ent_reg.async_get(threshold.entity_id)
            assert entry is not None
            assert (
                entry.disabled_by != er.RegistryEntryDisabler.INTEGRATION
            ), f"{threshold.entity_id} should not be integration-disabled"


class TestAutoDisableOnReplaceSensor:
    """Tests for entity auto-disable/enable when sensors are replaced at runtime."""

    async def test_replace_sensor_enables_entities(
        self,
        hass: HomeAssistant,
        init_integration_no_sensors: MockConfigEntry,
    ) -> None:
        """Adding an external sensor should re-enable the related entities."""
        ent_reg = er.async_get(hass)
        plant = hass.data[DOMAIN][init_integration_no_sensors.entry_id][ATTR_PLANT]

        # Verify initially disabled
        entry = ent_reg.async_get(plant.sensor_temperature.entity_id)
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        # Directly call replace_external_sensor (service can't reach disabled entities
        # because their state is not registered)
        new_sensor_id = "sensor.new_temperature"
        hass.states.async_set(
            new_sensor_id,
            "25",
            {"unit_of_measurement": "°C", "device_class": "temperature"},
        )
        await hass.async_block_till_done()

        plant.sensor_temperature.replace_external_sensor(new_sensor_id)
        await hass.async_block_till_done()

        # Meter sensor, max and min thresholds should now be enabled
        for entity in [
            plant.sensor_temperature,
            plant.max_temperature,
            plant.min_temperature,
        ]:
            entry = ent_reg.async_get(entity.entity_id)
            assert (
                entry.disabled_by != er.RegistryEntryDisabler.INTEGRATION
            ), f"{entity.entity_id} should be re-enabled"

    async def test_replace_sensor_disables_entities(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Removing an external sensor should disable the related entities."""
        ent_reg = er.async_get(hass)
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        meter_entity = plant.sensor_temperature.entity_id

        # Verify initially enabled
        entry = ent_reg.async_get(meter_entity)
        assert entry.disabled_by is None

        # Remove the sensor
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REPLACE_SENSOR,
            {"meter_entity": meter_entity, "new_sensor": ""},
            blocking=True,
        )
        await hass.async_block_till_done()

        # Meter sensor, max and min thresholds should now be disabled
        for entity in [
            plant.sensor_temperature,
            plant.max_temperature,
            plant.min_temperature,
        ]:
            entry = ent_reg.async_get(entity.entity_id)
            assert (
                entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION
            ), f"{entity.entity_id} should be disabled"

    async def test_illuminance_removal_disables_derived_entities(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Removing illuminance sensor should disable DLI, PPFD, integral, etc."""
        ent_reg = er.async_get(hass)
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        meter_entity = plant.sensor_illuminance.entity_id

        # Remove illuminance sensor
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REPLACE_SENSOR,
            {"meter_entity": meter_entity, "new_sensor": ""},
            blocking=True,
        )
        await hass.async_block_till_done()

        # All illuminance-related entities should be disabled
        derived_entities = [
            plant.sensor_illuminance,
            plant.max_illuminance,
            plant.min_illuminance,
            plant.max_dli,
            plant.min_dli,
            plant.ppfd,
            plant.total_integral,
            plant.dli,
            plant.dli_24h,
        ]
        for entity in derived_entities:
            if entity is None:
                continue
            entry = ent_reg.async_get(entity.entity_id)
            assert entry is not None, f"Entity {entity.entity_id} not in registry"
            assert (
                entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION
            ), f"{entity.entity_id} should be disabled"


class TestAutoDisablePartialSensors:
    """Tests for mixed enabled/disabled state with partial sensor configuration."""

    async def test_partial_sensors_mixed_state(
        self,
        hass: HomeAssistant,
        enable_custom_integrations,
    ) -> None:
        """Only configured sensors should be enabled; unconfigured ones disabled."""
        # Create config with only temperature and moisture sensors
        config_data = create_plant_config_data(
            temperature_sensor="sensor.test_temperature",
            moisture_sensor="sensor.test_moisture",
            conductivity_sensor=None,
            illuminance_sensor=None,
            humidity_sensor=None,
            co2_sensor=None,
            soil_temperature_sensor=None,
        )

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Test Plant",
            data=config_data,
            entry_id=TEST_ENTRY_ID,
            unique_id=TEST_ENTRY_ID,
        )
        entry.add_to_hass(hass)

        # Set up the mock external sensors that are configured
        await setup_mock_external_sensors(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        ent_reg = er.async_get(hass)
        plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]

        # Temperature and moisture should be enabled
        for entity in [
            plant.sensor_temperature,
            plant.max_temperature,
            plant.min_temperature,
            plant.sensor_moisture,
            plant.max_moisture,
            plant.min_moisture,
        ]:
            reg_entry = ent_reg.async_get(entity.entity_id)
            assert reg_entry is not None
            assert (
                reg_entry.disabled_by != er.RegistryEntryDisabler.INTEGRATION
            ), f"{entity.entity_id} should be enabled"

        # Conductivity, humidity, co2, soil_temperature should be disabled
        for entity in [
            plant.sensor_conductivity,
            plant.max_conductivity,
            plant.min_conductivity,
            plant.sensor_humidity,
            plant.max_humidity,
            plant.min_humidity,
            plant.sensor_co2,
            plant.max_co2,
            plant.min_co2,
            plant.sensor_soil_temperature,
            plant.max_soil_temperature,
            plant.min_soil_temperature,
        ]:
            reg_entry = ent_reg.async_get(entity.entity_id)
            assert reg_entry is not None
            assert (
                reg_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION
            ), f"{entity.entity_id} should be disabled"

        # Illuminance-derived entities should also be disabled
        for entity in [
            plant.sensor_illuminance,
            plant.max_illuminance,
            plant.min_illuminance,
            plant.dli,
            plant.dli_24h,
        ]:
            if entity is None:
                continue
            reg_entry = ent_reg.async_get(entity.entity_id)
            assert reg_entry is not None
            assert (
                reg_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION
            ), f"{entity.entity_id} should be disabled"

        # Cleanup
        if hass.config_entries.async_get_entry(entry.entry_id):
            await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()
