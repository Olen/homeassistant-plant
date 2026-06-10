"""Tests for plant threshold (number) entities."""

from __future__ import annotations

from homeassistant.components.number import NumberMode
from homeassistant.const import LIGHT_LUX, PERCENTAGE, UnitOfConductivity
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache_with_extra_data,
)

from custom_components.plant.const import (
    ATTR_PLANT,
    ATTR_THRESHOLDS,
    DOMAIN,
    UNIT_DLI,
)

from .conftest import TEST_PLANT_NAME


class TestThresholdEntitiesCreation:
    """Tests for threshold entity creation."""

    async def test_threshold_entities_created(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that all 19 number entities are created (18 thresholds + lux_to_ppfd)."""
        assert ATTR_THRESHOLDS in hass.data[DOMAIN][init_integration.entry_id]
        thresholds = hass.data[DOMAIN][init_integration.entry_id][ATTR_THRESHOLDS]

        # Should have 19 number entities: 18 thresholds + 1 lux_to_ppfd
        assert len(thresholds) == 19

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
        # 18 thresholds + 1 lux_to_ppfd conversion factor
        assert len(number_entities) == 19


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

    async def test_dli_threshold_step(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test DLI thresholds expose 0.1 step precision."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        assert plant.max_dli.native_step == 0.1
        assert plant.min_dli.native_step == 0.1

        max_state = hass.states.get(plant.max_dli.entity_id)
        min_state = hass.states.get(plant.min_dli.entity_id)

        assert max_state is not None
        assert min_state is not None
        assert max_state.attributes["step"] == 0.1
        assert min_state.attributes["step"] == 0.1


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
        assert threshold.native_value == 70.0


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

    async def test_max_soil_temperature_converts_fahrenheit_to_celsius(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Soil-temperature thresholds must publish converted values to
        the state machine on unit change, mirroring the existing air
        max_temperature behavior. Pre-fix the soil class only mutated
        _attr_native_value without writing state, so the published
        state stayed in the old unit."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.max_soil_temperature

        await threshold.async_set_native_value(68)
        await hass.async_block_till_done()

        threshold.state_attributes_changed(
            {"unit_of_measurement": "°F"},
            {"unit_of_measurement": "°C"},
        )
        await hass.async_block_till_done()

        state = hass.states.get(threshold.entity_id)
        assert state is not None
        assert int(state.state) == 20

    async def test_max_soil_temperature_converts_celsius_to_fahrenheit(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Soil max-temperature: °C → °F."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.max_soil_temperature

        await threshold.async_set_native_value(20)
        await hass.async_block_till_done()

        threshold.state_attributes_changed(
            {"unit_of_measurement": "°C"},
            {"unit_of_measurement": "°F"},
        )
        await hass.async_block_till_done()

        state = hass.states.get(threshold.entity_id)
        assert state is not None
        assert int(state.state) == 68

    async def test_min_soil_temperature_converts_fahrenheit_to_celsius(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Soil min-temperature: °F → °C."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.min_soil_temperature

        await threshold.async_set_native_value(50)
        await hass.async_block_till_done()

        threshold.state_attributes_changed(
            {"unit_of_measurement": "°F"},
            {"unit_of_measurement": "°C"},
        )
        await hass.async_block_till_done()

        state = hass.states.get(threshold.entity_id)
        assert state is not None
        assert int(state.state) == 10

    async def test_min_soil_temperature_converts_celsius_to_fahrenheit(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Soil min-temperature: °C → °F."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.min_soil_temperature

        await threshold.async_set_native_value(10)
        await hass.async_block_till_done()

        threshold.state_attributes_changed(
            {"unit_of_measurement": "°C"},
            {"unit_of_measurement": "°F"},
        )
        await hass.async_block_till_done()

        state = hass.states.get(threshold.entity_id)
        assert state is not None
        assert int(state.state) == 50

    async def test_temperature_conversion_persists_through_next_state_write(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Unit conversion must update the entity's _attr_native_value
        AND publish state — not just one or the other.

        Pre-fix the air-temp classes wrote the converted value via
        hass.states.async_set, leaving _attr_native_value untouched.
        The next time the entity calls async_write_ha_state (user
        edit, polling, RestoreState restoration), it published from
        native_value and the conversion was silently reverted.
        """
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        threshold = plant.max_temperature

        await threshold.async_set_native_value(68)
        await hass.async_block_till_done()

        threshold.state_attributes_changed(
            {"unit_of_measurement": "°F"},
            {"unit_of_measurement": "°C"},
        )
        await hass.async_block_till_done()

        # Conversion happened correctly the first time. (hass.states.async_set
        # writes the int value; subsequent NumberEntity writes format as
        # "20.0" — float() handles both.)
        assert float(hass.states.get(threshold.entity_id).state) == 20

        # Force any subsequent state write — same channel that polling,
        # restoration, or user edits would use.
        threshold.async_write_ha_state()
        await hass.async_block_till_done()

        # State must still reflect the converted value, not revert.
        assert float(hass.states.get(threshold.entity_id).state) == 20


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


# Pre-built NumberExtraStoredData payload for max_moisture (0-100 %, step 1).
def _moisture_extra(value: float) -> dict:
    return {
        "native_max_value": 100,
        "native_min_value": 0,
        "native_step": 1,
        "native_unit_of_measurement": PERCENTAGE,
        "native_value": value,
    }


class TestThresholdRestoreState:
    """Tests for RestoreState behavior of threshold entities.

    HA's RestoreState is keyed by entity_id and retains values for ~7 days
    after entity removal. A delete + re-add of a plant with the same name
    produces a colliding auto-derived entity_id, which without a guard
    would restore the deleted entity's stale value over the fresh
    OPB-fetched default. These tests cover both halves of the contract:

    - Brand-new config entries skip restore and use defaults.
    - Existing entries (already in the entity registry) still restore,
      so user edits survive normal restarts and reloads.
    """

    async def test_new_entity_skips_stale_restore_state(
        self,
        hass: HomeAssistant,
        plant_config_data: dict,
        mock_external_sensors,
        mock_no_openplantbook,
    ) -> None:
        """A brand-new config entry must use the default value from
        FLOW_PLANT_LIMITS, not stale RestoreState left behind by a
        previously-deleted entity that happened to share the same
        auto-derived entity_id.

        Reproduces the delete + re-add scenario from #392: the
        deleted plant left max_moisture=99 % in RestoreState; a fresh
        re-add with the same name must show the configured 60 %.
        """
        mock_restore_cache_with_extra_data(
            hass,
            [
                (
                    State("number.test_plant_max_soil_moisture", "99"),
                    _moisture_extra(99),
                ),
            ],
        )

        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data=plant_config_data,
            entry_id="brand_new_entry_id",
            title=TEST_PLANT_NAME,
        )
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][config_entry.entry_id][ATTR_PLANT]
        # plant_config_data sets max_moisture=60. Without the skip-restore
        # guard, the stale 99 from RestoreState would win.
        assert plant.max_moisture.native_value == 60

        await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()

    async def test_existing_entity_restores_user_edited_value(
        self,
        hass: HomeAssistant,
        plant_config_data: dict,
        mock_external_sensors,
        mock_no_openplantbook,
    ) -> None:
        """Existing entries (already present in the entity registry from
        a prior setup) must continue to restore their previous value.
        Only brand-new entries skip restore.
        """
        entry_id = "existing_entry_id"
        unique_id = f"{entry_id}-max-moisture"

        # Pre-register the entity so the integration sees it as existing.
        ent_reg = er.async_get(hass)
        registry_entry = ent_reg.async_get_or_create(
            domain="number",
            platform=DOMAIN,
            unique_id=unique_id,
        )

        mock_restore_cache_with_extra_data(
            hass,
            [(State(registry_entry.entity_id, "85"), _moisture_extra(85))],
        )

        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data=plant_config_data,
            entry_id=entry_id,
            title=TEST_PLANT_NAME,
        )
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][config_entry.entry_id][ATTR_PLANT]
        # The user previously edited max_moisture to 85; that must win
        # over the config default of 60.
        assert plant.max_moisture.native_value == 85

        await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()


class TestThresholdImperialDefaults:
    """Tests for the temperature threshold setup behavior in imperial mode.

    Covers two related defects from #438:

    * #438a — defaults in ``const.py`` and from OpenPlantbook are in °C; the
      four temperature threshold entities must convert them to the system
      unit before stamping the °F label, otherwise a 40 °C default becomes
      "40 °F" instead of "104 °F".
    * #438b — the slider bounds (``native_min_value`` / ``native_max_value``)
      must widen to °F-appropriate values in imperial mode; otherwise the
      100 °C cap silently becomes a 100 °F cap (≈ 37.8 °C), too low for
      heat-tolerant species.
    """

    async def test_temperature_thresholds_converted_when_system_imperial(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """All four temperature thresholds use °F values when system is imperial."""
        from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

        hass.config.units = US_CUSTOMARY_SYSTEM
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][mock_config_entry.entry_id][ATTR_PLANT]

        # Defaults in conftest: max=40°C, min=10°C, max_soil=40°C, min_soil=10°C
        # Converted: 40°C → 104°F, 10°C → 50°F
        assert plant.max_temperature.native_value == 104
        assert plant.min_temperature.native_value == 50
        assert plant.max_soil_temperature.native_value == 104
        assert plant.min_soil_temperature.native_value == 50

        assert plant.max_temperature._attr_native_unit_of_measurement == "°F"
        assert plant.min_temperature._attr_native_unit_of_measurement == "°F"
        assert plant.max_soil_temperature._attr_native_unit_of_measurement == "°F"
        assert plant.min_soil_temperature._attr_native_unit_of_measurement == "°F"

    async def test_temperature_thresholds_unchanged_when_system_metric(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Baseline: metric system leaves the °C defaults alone."""
        from homeassistant.util.unit_system import METRIC_SYSTEM

        hass.config.units = METRIC_SYSTEM
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][mock_config_entry.entry_id][ATTR_PLANT]

        assert plant.max_temperature.native_value == 40
        assert plant.min_temperature.native_value == 10
        assert plant.max_soil_temperature.native_value == 40
        assert plant.min_soil_temperature.native_value == 10

    async def test_temperature_slider_bounds_widen_when_system_imperial(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Slider bounds for the four temperature thresholds are 200 / -50 °F."""
        from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

        hass.config.units = US_CUSTOMARY_SYSTEM
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][mock_config_entry.entry_id][ATTR_PLANT]

        for threshold in (
            plant.max_temperature,
            plant.min_temperature,
            plant.max_soil_temperature,
            plant.min_soil_temperature,
        ):
            assert threshold.native_max_value == 200
            assert threshold.native_min_value == -50

    async def test_temperature_slider_bounds_unchanged_when_system_metric(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Baseline: metric system leaves the existing -50 / 100 °C bounds."""
        from homeassistant.util.unit_system import METRIC_SYSTEM

        hass.config.units = METRIC_SYSTEM
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][mock_config_entry.entry_id][ATTR_PLANT]

        for threshold in (
            plant.max_temperature,
            plant.min_temperature,
            plant.max_soil_temperature,
            plant.min_soil_temperature,
        ):
            assert threshold.native_max_value == 100
            assert threshold.native_min_value == -50


class TestPreConvertedFahrenheitLimits:
    """Tests that pre-converted Fahrenheit limits from generate_configentry are not double-converted.

    Covers the double-conversion bug where temperature limits stored in FLOW_PLANT_LIMITS
    (already converted to Fahrenheit by generate_configentry via display_temp()) were
    being converted again by _convert_default_temp() in the threshold entity __init__.

    Example bug: OpenPlantbook returns min_temp=7°C, generate_configentry converts to 45°F,
    but the entity __init__ then treated 45 as Celsius and converted again to 113°F.
    """

    async def test_preconverted_fahrenheit_limits_not_double_converted(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Temperature thresholds with pre-converted °F values are used as-is."""
        from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

        from custom_components.plant.const import DOMAIN_PLANTBOOK

        from .conftest import (
            CONF_MAX_SOIL_TEMPERATURE,
            CONF_MAX_TEMPERATURE,
            CONF_MIN_SOIL_TEMPERATURE,
            CONF_MIN_TEMPERATURE,
            TEST_PLANT_NAME,
            create_plant_config_data,
        )

        hass.config.units = US_CUSTOMARY_SYSTEM

        # Simulate limits that are ALREADY in Fahrenheit (as generate_configentry would produce)
        # OpenPlantbook: min=7°C, max=32°C  →  after display_temp(): min=45°F, max=90°F
        preconverted_fahrenheit_limits = {
            CONF_MAX_TEMPERATURE: 90,  # Already 90°F, not 90°C
            CONF_MIN_TEMPERATURE: 45,  # Already 45°F, not 45°C
            CONF_MAX_SOIL_TEMPERATURE: 86,  # Already 86°F (30°C)
            CONF_MIN_SOIL_TEMPERATURE: 50,  # Already 50°F (10°C)
            # Include other required limits
            "max_moisture": 60,
            "min_moisture": 20,
            "max_conductivity": 2000,
            "min_conductivity": 350,
            "max_illuminance": 7000,
            "min_illuminance": 2000,
            "max_humidity": 85,
            "min_humidity": 30,
            "max_dli": 9.0,
            "min_dli": 4.0,
            "max_co2": 2000,
            "min_co2": 400,
            "max_vpd": 1.6,
            "min_vpd": 0.4,
        }

        # Specify data_source=DOMAIN_PLANTBOOK to indicate values are pre-converted
        config_data = create_plant_config_data(
            limits=preconverted_fahrenheit_limits,
            data_source=DOMAIN_PLANTBOOK,
        )
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data=config_data,
            entry_id="test_preconverted_f",
            unique_id="test_preconverted_f",
            title=TEST_PLANT_NAME,
        )
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][config_entry.entry_id][ATTR_PLANT]

        # The values should be used AS-IS, not converted again
        # Bug behavior: 45°F treated as 45°C → converted to 113°F
        # Fixed behavior: 45°F stays 45°F
        assert plant.max_temperature.native_value == 90
        assert plant.min_temperature.native_value == 45
        assert plant.max_soil_temperature.native_value == 86
        assert plant.min_soil_temperature.native_value == 50

        # Unit should still be Fahrenheit
        assert plant.max_temperature._attr_native_unit_of_measurement == "°F"
        assert plant.min_temperature._attr_native_unit_of_measurement == "°F"

        await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()

    async def test_missing_limits_fall_back_to_converted_defaults(
        self,
        hass: HomeAssistant,
    ) -> None:
        """When limits are missing, fallback defaults are converted from Celsius."""
        from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

        from .conftest import TEST_PLANT_NAME, create_plant_config_data

        hass.config.units = US_CUSTOMARY_SYSTEM

        # Create limits WITHOUT temperature values to test fallback behavior
        limits_without_temp = {
            "max_moisture": 60,
            "min_moisture": 20,
            "max_conductivity": 2000,
            "min_conductivity": 350,
            "max_illuminance": 7000,
            "min_illuminance": 2000,
            "max_humidity": 85,
            "min_humidity": 30,
            "max_dli": 9.0,
            "min_dli": 4.0,
            "max_co2": 2000,
            "min_co2": 400,
            "max_vpd": 1.6,
            "min_vpd": 0.4,
            # Explicitly omit temperature keys to test fallback
        }

        config_data = create_plant_config_data(limits=limits_without_temp)
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data=config_data,
            entry_id="test_missing_temp",
            unique_id="test_missing_temp",
            title=TEST_PLANT_NAME,
        )
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][config_entry.entry_id][ATTR_PLANT]

        # Fallback defaults are in Celsius (from const.py) and SHOULD be converted
        # DEFAULT_MAX_TEMPERATURE = 40°C → 104°F
        # DEFAULT_MIN_TEMPERATURE = 10°C → 50°F
        # DEFAULT_MAX_SOIL_TEMPERATURE = 40°C → 104°F
        # DEFAULT_MIN_SOIL_TEMPERATURE = 10°C → 50°F
        assert plant.max_temperature.native_value == 104
        assert plant.min_temperature.native_value == 50
        assert plant.max_soil_temperature.native_value == 104
        assert plant.min_soil_temperature.native_value == 50

        await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()

    async def test_manual_celsius_limits_converted_when_imperial(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Manual/non-OpenPlantbook Celsius values ARE converted to Fahrenheit."""
        from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

        from custom_components.plant.const import DATA_SOURCE_MANUAL

        from .conftest import (
            CONF_MAX_SOIL_TEMPERATURE,
            CONF_MAX_TEMPERATURE,
            CONF_MIN_SOIL_TEMPERATURE,
            CONF_MIN_TEMPERATURE,
            TEST_PLANT_NAME,
            create_plant_config_data,
        )

        hass.config.units = US_CUSTOMARY_SYSTEM

        # Manual entry: user types Celsius values (not pre-converted by generate_configentry)
        manual_celsius_limits = {
            CONF_MAX_TEMPERATURE: 32,  # 32°C → should become 90°F
            CONF_MIN_TEMPERATURE: 7,   # 7°C → should become 45°F
            CONF_MAX_SOIL_TEMPERATURE: 30,  # 30°C → should become 86°F
            CONF_MIN_SOIL_TEMPERATURE: 10,  # 10°C → should become 50°F
            "max_moisture": 60,
            "min_moisture": 20,
            "max_conductivity": 2000,
            "min_conductivity": 350,
            "max_illuminance": 7000,
            "min_illuminance": 2000,
            "max_humidity": 85,
            "min_humidity": 30,
            "max_dli": 9.0,
            "min_dli": 4.0,
            "max_co2": 2000,
            "min_co2": 400,
            "max_vpd": 1.6,
            "min_vpd": 0.4,
        }

        # data_source=DATA_SOURCE_MANUAL means values are NOT pre-converted
        config_data = create_plant_config_data(
            limits=manual_celsius_limits,
            data_source=DATA_SOURCE_MANUAL,
        )
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data=config_data,
            entry_id="test_manual_celsius",
            unique_id="test_manual_celsius",
            title=TEST_PLANT_NAME,
        )
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][config_entry.entry_id][ATTR_PLANT]

        # Manual Celsius values SHOULD be converted to Fahrenheit
        # 32°C → 90°F, 7°C → 45°F, 30°C → 86°F, 10°C → 50°F
        assert plant.max_temperature.native_value == 90
        assert plant.min_temperature.native_value == 45
        assert plant.max_soil_temperature.native_value == 86
        assert plant.min_soil_temperature.native_value == 50

        await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()

