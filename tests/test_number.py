"""Tests for plant threshold (number) entities."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.number import NumberMode
from homeassistant.const import LIGHT_LUX, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory

from custom_components.plant.const import (
    ATTR_PLANT,
    ATTR_THRESHOLDS,
    DOMAIN,
    UNIT_CONDUCTIVITY,
    UNIT_DLI,
)

from .conftest import TEST_ENTRY_ID


class TestThresholdEntitiesCreation:
    """Tests for threshold entity creation."""

    async def test_threshold_entities_created(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that all 12 threshold entities are created."""
        assert ATTR_THRESHOLDS in hass.data[DOMAIN][init_integration.entry_id]
        thresholds = hass.data[DOMAIN][init_integration.entry_id][ATTR_THRESHOLDS]

        # Should have 12 threshold entities
        assert len(thresholds) == 12

    async def test_threshold_entities_in_registry(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test threshold entities are registered in entity registry."""
        entity_registry = er.async_get(hass)
        entities = er.async_entries_for_config_entry(
            entity_registry, init_integration.entry_id
        )

        number_entities = [e for e in entities if e.domain == "number"]
        assert len(number_entities) == 12


class TestMoistureThresholds:
    """Tests for moisture threshold entities."""

    async def test_max_moisture_threshold(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test max moisture threshold entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.max_moisture

        assert threshold is not None
        assert "max" in threshold.name.lower()
        assert "moisture" in threshold.name.lower()
        assert threshold.native_unit_of_measurement == PERCENTAGE
        assert threshold.native_min_value == 0
        assert threshold.native_max_value == 100
        assert threshold.native_step == 1

    async def test_min_moisture_threshold(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test min moisture threshold entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.min_moisture

        assert threshold is not None
        assert "min" in threshold.name.lower()
        assert "moisture" in threshold.name.lower()
        assert threshold.native_unit_of_measurement == PERCENTAGE

    async def test_moisture_threshold_default_values(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test moisture threshold default values from config."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Default values from conftest: max=60, min=20
        assert plant.max_moisture.native_value == 60
        assert plant.min_moisture.native_value == 20


class TestTemperatureThresholds:
    """Tests for temperature threshold entities."""

    async def test_max_temperature_threshold(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test max temperature threshold entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.max_temperature

        assert threshold is not None
        assert "max" in threshold.name.lower()
        assert "temperature" in threshold.name.lower()
        # Unit should match HA's configured unit system
        assert threshold.native_unit_of_measurement in ["°C", "°F"]

    async def test_min_temperature_threshold(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test min temperature threshold entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.min_temperature

        assert threshold is not None
        assert "min" in threshold.name.lower()
        assert "temperature" in threshold.name.lower()

    async def test_temperature_threshold_default_values(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test temperature threshold default values from config."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Default values from conftest: max=40, min=10
        assert plant.max_temperature.native_value == 40
        assert plant.min_temperature.native_value == 10


class TestConductivityThresholds:
    """Tests for conductivity threshold entities."""

    async def test_max_conductivity_threshold(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test max conductivity threshold entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.max_conductivity

        assert threshold is not None
        assert "max" in threshold.name.lower()
        assert "conductivity" in threshold.name.lower()
        assert threshold.native_unit_of_measurement == UNIT_CONDUCTIVITY
        assert threshold.native_step == 50

    async def test_min_conductivity_threshold(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test min conductivity threshold entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.min_conductivity

        assert threshold is not None
        assert "min" in threshold.name.lower()
        assert "conductivity" in threshold.name.lower()

    async def test_conductivity_threshold_default_values(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test conductivity threshold default values from config."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Default values from conftest: max=3000, min=500
        assert plant.max_conductivity.native_value == 3000
        assert plant.min_conductivity.native_value == 500


class TestIlluminanceThresholds:
    """Tests for illuminance threshold entities."""

    async def test_max_illuminance_threshold(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test max illuminance threshold entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.max_illuminance

        assert threshold is not None
        assert "max" in threshold.name.lower()
        assert "illuminance" in threshold.name.lower()
        assert threshold.native_unit_of_measurement == LIGHT_LUX
        assert threshold.native_max_value == 200000
        assert threshold.native_step == 500

    async def test_min_illuminance_threshold(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test min illuminance threshold entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.min_illuminance

        assert threshold is not None
        assert "min" in threshold.name.lower()
        assert "illuminance" in threshold.name.lower()


class TestHumidityThresholds:
    """Tests for humidity threshold entities."""

    async def test_max_humidity_threshold(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test max humidity threshold entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.max_humidity

        assert threshold is not None
        assert "max" in threshold.name.lower()
        assert "humidity" in threshold.name.lower()
        assert threshold.native_unit_of_measurement == PERCENTAGE

    async def test_min_humidity_threshold(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test min humidity threshold entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.min_humidity

        assert threshold is not None
        assert "min" in threshold.name.lower()
        assert "humidity" in threshold.name.lower()


class TestDliThresholds:
    """Tests for DLI threshold entities."""

    async def test_max_dli_threshold(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test max DLI threshold entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.max_dli

        assert threshold is not None
        assert "max" in threshold.name.lower()
        assert "dli" in threshold.name.lower()
        assert threshold.native_unit_of_measurement == UNIT_DLI

    async def test_min_dli_threshold(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test min DLI threshold entity."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.min_dli

        assert threshold is not None
        assert "min" in threshold.name.lower()
        assert "dli" in threshold.name.lower()

    async def test_dli_threshold_default_values(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test DLI threshold default values from config."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Default values from conftest: max=30, min=2
        assert plant.max_dli.native_value == 30
        assert plant.min_dli.native_value == 2


class TestThresholdEntityProperties:
    """Tests for common threshold entity properties."""

    async def test_threshold_entity_category(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that threshold entities have CONFIG category."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        for threshold in plant.threshold_entities:
            assert threshold.entity_category == EntityCategory.CONFIG

    async def test_threshold_mode(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that threshold entities use BOX mode."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        for threshold in plant.threshold_entities:
            assert threshold.mode == NumberMode.BOX

    async def test_threshold_device_info(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that threshold entities have correct device info."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        for threshold in plant.threshold_entities:
            device_info = threshold.device_info
            assert "identifiers" in device_info
            assert (DOMAIN, plant.unique_id) in device_info["identifiers"]


class TestThresholdStateChanges:
    """Tests for threshold state change handling."""

    async def test_set_native_value(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test setting threshold value programmatically."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.max_moisture

        await threshold.async_set_native_value(75)
        assert threshold.native_value == 75

    async def test_threshold_state_change(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test threshold responds to state changes."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.max_moisture

        # Simulate state change
        threshold.state_changed(old_state="60", new_state="70")
        assert threshold.native_value == "70"
