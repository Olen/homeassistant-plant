"""Tests for plant threshold (number) entities."""

from __future__ import annotations

from homeassistant.components.number import NumberMode
from homeassistant.const import LIGHT_LUX, PERCENTAGE, UnitOfConductivity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant.const import (
    ATTR_PLANT,
    ATTR_THRESHOLDS,
    DOMAIN,
    UNIT_DLI,
)


class TestThresholdEntitiesCreation:
    """Tests for threshold entity creation."""

    async def test_threshold_entities_created(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that all 15 number entities are created (14 thresholds + lux_to_ppfd)."""
        assert ATTR_THRESHOLDS in hass.data[DOMAIN][init_integration.entry_id]
        thresholds = hass.data[DOMAIN][init_integration.entry_id][ATTR_THRESHOLDS]

        # Should have 15 number entities: 14 thresholds + 1 lux_to_ppfd
        assert len(thresholds) == 15

    async def test_threshold_entities_in_registry(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test number entities are registered in entity registry."""
        entity_registry = er.async_get(hass)
        entities = er.async_entries_for_config_entry(
            entity_registry, init_integration.entry_id
        )

        number_entities = [e for e in entities if e.domain == "number"]
        # 14 thresholds + 1 lux_to_ppfd conversion factor
        assert len(number_entities) == 15


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

    async def test_temperature_threshold_allows_negative_values(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that temperature thresholds allow negative values."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.min_temperature

        # Verify min_value allows negative temperatures
        assert threshold.native_min_value == -50

        # Set a negative temperature value
        await threshold.async_set_native_value(-10)
        assert threshold.native_value == -10

        # Set an extreme negative temperature value
        await threshold.async_set_native_value(-45)
        assert threshold.native_value == -45


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
        assert (
            threshold.native_unit_of_measurement
            == UnitOfConductivity.MICROSIEMENS_PER_CM
        )
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


class TestTemperatureUnitConversion:
    """Tests for temperature unit conversion when unit of measurement changes."""

    async def test_max_temperature_converts_fahrenheit_to_celsius(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test max temperature converts from °F to °C."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.max_temperature

        # Set initial value to 68°F using the entity's method
        await threshold.async_set_native_value(68)
        await hass.async_block_till_done()

        old_attributes = {"unit_of_measurement": "°F"}
        new_attributes = {"unit_of_measurement": "°C"}

        threshold.state_attributes_changed(old_attributes, new_attributes)
        await hass.async_block_till_done()

        # Check that state was updated (68°F -> 20°C)
        state = hass.states.get(threshold.entity_id)
        assert state is not None
        assert int(state.state) == 20

    async def test_max_temperature_converts_celsius_to_fahrenheit(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test max temperature converts from °C to °F."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.max_temperature

        # Set initial value to 20°C using the entity's method
        await threshold.async_set_native_value(20)
        await hass.async_block_till_done()

        old_attributes = {"unit_of_measurement": "°C"}
        new_attributes = {"unit_of_measurement": "°F"}

        threshold.state_attributes_changed(old_attributes, new_attributes)
        await hass.async_block_till_done()

        # Check that state was updated (20°C -> 68°F)
        state = hass.states.get(threshold.entity_id)
        assert state is not None
        assert int(state.state) == 68

    async def test_min_temperature_converts_fahrenheit_to_celsius(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test min temperature converts from °F to °C."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.min_temperature

        # Set initial value to 50°F using the entity's method
        await threshold.async_set_native_value(50)
        await hass.async_block_till_done()

        old_attributes = {"unit_of_measurement": "°F"}
        new_attributes = {"unit_of_measurement": "°C"}

        threshold.state_attributes_changed(old_attributes, new_attributes)
        await hass.async_block_till_done()

        # Check that state was updated (50°F -> 10°C)
        state = hass.states.get(threshold.entity_id)
        assert state is not None
        assert int(state.state) == 10

    async def test_min_temperature_converts_celsius_to_fahrenheit(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test min temperature converts from °C to °F."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.min_temperature

        # Set initial value to 10°C using the entity's method
        await threshold.async_set_native_value(10)
        await hass.async_block_till_done()

        old_attributes = {"unit_of_measurement": "°C"}
        new_attributes = {"unit_of_measurement": "°F"}

        threshold.state_attributes_changed(old_attributes, new_attributes)
        await hass.async_block_till_done()

        # Check that state was updated (10°C -> 50°F)
        state = hass.states.get(threshold.entity_id)
        assert state is not None
        assert int(state.state) == 50

    async def test_temperature_no_conversion_when_units_same(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test no conversion happens when unit stays the same."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.max_temperature

        # Get initial state
        initial_state = hass.states.get(threshold.entity_id)
        initial_value = initial_state.state

        old_attributes = {"unit_of_measurement": "°C"}
        new_attributes = {"unit_of_measurement": "°C"}

        threshold.state_attributes_changed(old_attributes, new_attributes)
        await hass.async_block_till_done()

        # Value should remain unchanged
        state = hass.states.get(threshold.entity_id)
        assert state.state == initial_value

    async def test_temperature_no_conversion_when_old_unit_none(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test no conversion when old unit is None."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.max_temperature

        # Get initial state
        initial_state = hass.states.get(threshold.entity_id)
        initial_value = initial_state.state

        old_attributes = {"unit_of_measurement": None}
        new_attributes = {"unit_of_measurement": "°C"}

        threshold.state_attributes_changed(old_attributes, new_attributes)
        await hass.async_block_till_done()

        # Value should remain unchanged
        state = hass.states.get(threshold.entity_id)
        assert state.state == initial_value

    async def test_temperature_no_conversion_when_new_unit_none(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test no conversion when new unit is None."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.max_temperature

        # Get initial state
        initial_state = hass.states.get(threshold.entity_id)
        initial_value = initial_state.state

        old_attributes = {"unit_of_measurement": "°C"}
        new_attributes = {"unit_of_measurement": None}

        threshold.state_attributes_changed(old_attributes, new_attributes)
        await hass.async_block_till_done()

        # Value should remain unchanged
        state = hass.states.get(threshold.entity_id)
        assert state.state == initial_value


class TestLuxToPpfdEntity:
    """Tests for lux to PPFD conversion factor entity."""

    async def test_lux_to_ppfd_entity_created(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test lux_to_ppfd entity is created and added to plant."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        assert plant.lux_to_ppfd is not None
        assert "lux" in plant.lux_to_ppfd.name.lower()
        assert "ppfd" in plant.lux_to_ppfd.name.lower()

    async def test_lux_to_ppfd_default_value(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test lux_to_ppfd has correct default value for sunlight."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Default value is 0.0185 for sunlight
        assert plant.lux_to_ppfd.native_value == 0.0185

    async def test_lux_to_ppfd_entity_properties(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test lux_to_ppfd entity has correct properties."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        lux_to_ppfd = plant.lux_to_ppfd

        # Check min/max range is reasonable for different light sources
        assert lux_to_ppfd.native_min_value == 0.001
        assert lux_to_ppfd.native_max_value == 0.1
        assert lux_to_ppfd.native_step == 0.0001

        # Should be a config entity
        assert lux_to_ppfd.entity_category == EntityCategory.CONFIG

        # Should have display precision hint for GUI (4 decimal places)
        assert lux_to_ppfd._attr_suggested_display_precision == 4

    async def test_lux_to_ppfd_can_be_changed(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test lux_to_ppfd value can be changed for grow lights."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        lux_to_ppfd = plant.lux_to_ppfd

        # Simulate changing to LED grow light value
        await lux_to_ppfd.async_set_native_value(0.014)
        await hass.async_block_till_done()

        assert lux_to_ppfd.native_value == 0.014
