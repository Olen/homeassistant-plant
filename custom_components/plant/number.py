"""Max/Min threshold classes for the plant device"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberDeviceClass, NumberMode, RestoreNumber
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    LIGHT_LUX,
    PERCENTAGE,
    STATE_UNKNOWN,
    UnitOfConductivity,
    UnitOfTemperature,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import (
    Entity,
    EntityCategory,
    async_generate_entity_id,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import (
    ATTR_CONDUCTIVITY,
    ATTR_DLI,
    ATTR_MAX,
    ATTR_MIN,
    ATTR_MOISTURE,
    ATTR_PLANT,
    ATTR_THRESHOLDS,
    CONF_LUX_TO_PPFD,
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
    DEFAULT_LUX_TO_PPFD,
    DEFAULT_MAX_CO2,
    DEFAULT_MAX_CONDUCTIVITY,
    DEFAULT_MAX_DLI,
    DEFAULT_MAX_HUMIDITY,
    DEFAULT_MAX_ILLUMINANCE,
    DEFAULT_MAX_MOISTURE,
    DEFAULT_MAX_SOIL_TEMPERATURE,
    DEFAULT_MAX_TEMPERATURE,
    DEFAULT_MIN_CO2,
    DEFAULT_MIN_CONDUCTIVITY,
    DEFAULT_MIN_DLI,
    DEFAULT_MIN_HUMIDITY,
    DEFAULT_MIN_ILLUMINANCE,
    DEFAULT_MIN_MOISTURE,
    DEFAULT_MIN_SOIL_TEMPERATURE,
    DEFAULT_MIN_TEMPERATURE,
    DOMAIN,
    FLOW_PLANT_INFO,
    FLOW_PLANT_LIMITS,
    ICON_CO2,
    ICON_CONDUCTIVITY,
    ICON_DLI,
    ICON_HUMIDITY,
    ICON_ILLUMINANCE,
    ICON_MOISTURE,
    ICON_PPFD,
    ICON_SOIL_TEMPERATURE,
    ICON_TEMPERATURE,
    READING_CO2,
    READING_CONDUCTIVITY,
    READING_DLI,
    READING_HUMIDITY,
    READING_ILLUMINANCE,
    READING_MOISTURE,
    READING_SOIL_TEMPERATURE,
    READING_TEMPERATURE,
    TEMPERATURE_MAX_VALUE,
    TEMPERATURE_MIN_VALUE,
    TRANSLATION_KEY_LUX_TO_PPFD,
    TRANSLATION_KEY_MAX_CO2,
    TRANSLATION_KEY_MAX_CONDUCTIVITY,
    TRANSLATION_KEY_MAX_DLI,
    TRANSLATION_KEY_MAX_HUMIDITY,
    TRANSLATION_KEY_MAX_ILLUMINANCE,
    TRANSLATION_KEY_MAX_MOISTURE,
    TRANSLATION_KEY_MAX_SOIL_TEMPERATURE,
    TRANSLATION_KEY_MAX_TEMPERATURE,
    TRANSLATION_KEY_MIN_CO2,
    TRANSLATION_KEY_MIN_CONDUCTIVITY,
    TRANSLATION_KEY_MIN_DLI,
    TRANSLATION_KEY_MIN_HUMIDITY,
    TRANSLATION_KEY_MIN_ILLUMINANCE,
    TRANSLATION_KEY_MIN_MOISTURE,
    TRANSLATION_KEY_MIN_SOIL_TEMPERATURE,
    TRANSLATION_KEY_MIN_TEMPERATURE,
    UNIT_DLI,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> bool:
    """Set up Threshold from a config entry."""
    _LOGGER.debug(entry.data)
    plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]
    pmaxm = PlantMaxMoisture(hass, entry, plant)
    pminm = PlantMinMoisture(hass, entry, plant)
    pmaxt = PlantMaxTemperature(hass, entry, plant)
    pmint = PlantMinTemperature(hass, entry, plant)
    pmaxb = PlantMaxIlluminance(hass, entry, plant)
    pminb = PlantMinIlluminance(hass, entry, plant)
    pmaxc = PlantMaxConductivity(hass, entry, plant)
    pminc = PlantMinConductivity(hass, entry, plant)
    pmaxh = PlantMaxHumidity(hass, entry, plant)
    pminh = PlantMinHumidity(hass, entry, plant)
    pmaxco2 = PlantMaxCo2(hass, entry, plant)
    pminco2 = PlantMinCo2(hass, entry, plant)
    pmaxst = PlantMaxSoilTemperature(hass, entry, plant)
    pminst = PlantMinSoilTemperature(hass, entry, plant)
    pmaxmm = PlantMaxDli(hass, entry, plant)
    pminmm = PlantMinDli(hass, entry, plant)
    plux_ppfd = PlantLuxToPpfd(hass, entry, plant)

    number_entities = [
        pmaxm,
        pminm,
        pmaxt,
        pmint,
        pmaxb,
        pminb,
        pmaxc,
        pminc,
        pmaxh,
        pminh,
        pmaxco2,
        pminco2,
        pmaxst,
        pminst,
        pmaxmm,
        pminmm,
        plux_ppfd,
    ]
    async_add_entities(number_entities)

    hass.data[DOMAIN][entry.entry_id][ATTR_THRESHOLDS] = number_entities
    plant.add_lux_to_ppfd(plux_ppfd)
    plant.add_thresholds(
        max_moisture=pmaxm,
        min_moisture=pminm,
        max_temperature=pmaxt,
        min_temperature=pmint,
        max_illuminance=pmaxb,
        min_illuminance=pminb,
        max_conductivity=pmaxc,
        min_conductivity=pminc,
        max_humidity=pmaxh,
        min_humidity=pminh,
        max_co2=pmaxco2,
        min_co2=pminco2,
        max_soil_temperature=pmaxst,
        min_soil_temperature=pminst,
        max_dli=pmaxmm,
        min_dli=pminmm,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True


class PlantMinMax(RestoreNumber):
    """Parent class for the min/max classes below"""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    # Subclasses should override this for entity_id generation
    _entity_id_key: str | None = None

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._config = config
        self.hass = hass
        self._plant = plantdevice
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN}.{{}}",
            f"{self._plant.name} {self._entity_id_key}",
            current_ids={},
        )
        # pylint: disable=no-member
        if (
            not hasattr(self, "_attr_native_value")
            or self._attr_native_value is None
            or self._attr_native_value == STATE_UNKNOWN
        ):
            self._attr_native_value = self._default_value

    @property
    def device_info(self) -> DeviceInfo:
        """Device info for devices"""
        return DeviceInfo(
            identifiers={(DOMAIN, self._plant.unique_id)},
        )

    async def async_set_native_value(self, value: float) -> None:
        _LOGGER.debug("Setting value of %s to %s", self.entity_id, value)
        self._attr_native_value = value
        self.async_write_ha_state()

    def _state_changed_event(self, event: Event) -> None:
        if event.data.get("old_state") is None or event.data.get("new_state") is None:
            return
        if event.data.get("old_state").state == event.data.get("new_state").state:
            self.state_attributes_changed(
                old_attributes=event.data.get("old_state").attributes,
                new_attributes=event.data.get("new_state").attributes,
            )
            return
        self.state_changed(
            old_state=event.data.get("old_state").state,
            new_state=event.data.get("new_state").state,
        )

    def state_changed(self, old_state: str | None, new_state: str | None) -> None:
        """Store the state if changed from the UI."""
        _LOGGER.debug(
            "State of %s changed from %s to %s, native_value = %s",
            self.entity_id,
            old_state,
            new_state,
            self._attr_native_value,
        )
        self._attr_native_value = new_state

    def state_attributes_changed(
        self, old_attributes: dict[str, Any], new_attributes: dict[str, Any]
    ) -> None:
        """Handle attribute changes (placeholder for subclasses)."""

    def self_updated(self) -> None:
        """Allow the state to be changed from the UI and saved in restore_state."""
        if self._attr_state != self.hass.states.get(self.entity_id).state:
            _LOGGER.debug(
                "Updating state of %s from %s to %s",
                self.entity_id,
                self._attr_state,
                self.hass.states.get(self.entity_id).state,
            )
            self._attr_state = self.hass.states.get(self.entity_id).state
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore state of thresholds on startup."""
        await super().async_added_to_hass()
        state = await self.async_get_last_number_data()
        if not state:
            return
        self._attr_native_value = state.native_value
        self._attr_native_unit_of_measurement = state.native_unit_of_measurement
        # We track changes to our own state so we can update ourselves if state is changed
        # from the UI or by other means
        async_track_state_change_event(
            self.hass,
            [self.entity_id],
            self._state_changed_event,
        )

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)


class PlantMaxMoisture(PlantMinMax):
    """Entity class for max moisture threshold"""

    _attr_device_class = f"{ATTR_MOISTURE} threshold"
    _attr_icon = ICON_MOISTURE
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_max_value = 100
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_translation_key = TRANSLATION_KEY_MAX_MOISTURE
    _entity_id_key = f"{ATTR_MAX} {READING_MOISTURE}"

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._default_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_MOISTURE, DEFAULT_MAX_MOISTURE
        )
        self._attr_unique_id = f"{config.entry_id}-max-moisture"
        super().__init__(hass, config, plantdevice)


class PlantMinMoisture(PlantMinMax):
    """Entity class for min moisture threshold"""

    _attr_device_class = f"{ATTR_MOISTURE} threshold"
    _attr_icon = ICON_MOISTURE
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_max_value = 100
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_translation_key = TRANSLATION_KEY_MIN_MOISTURE
    _entity_id_key = f"{ATTR_MIN} {READING_MOISTURE}"

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._default_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_MOISTURE, DEFAULT_MIN_MOISTURE
        )
        self._attr_unique_id = f"{config.entry_id}-min-moisture"
        super().__init__(hass, config, plantdevice)


class PlantMaxTemperature(PlantMinMax):
    """Entity class for max temperature threshold"""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_icon = ICON_TEMPERATURE
    _attr_native_max_value = TEMPERATURE_MAX_VALUE
    _attr_native_min_value = TEMPERATURE_MIN_VALUE
    _attr_native_step = 1
    _attr_translation_key = TRANSLATION_KEY_MAX_TEMPERATURE
    _entity_id_key = f"{ATTR_MAX} {READING_TEMPERATURE}"

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._attr_unique_id = f"{config.entry_id}-max-temperature"
        self._default_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_TEMPERATURE, DEFAULT_MAX_TEMPERATURE
        )
        super().__init__(hass, config, plantdevice)
        self._attr_native_unit_of_measurement = self.hass.config.units.temperature_unit

    def state_attributes_changed(
        self, old_attributes: dict[str, Any], new_attributes: dict[str, Any]
    ) -> None:
        """Convert temperature between Celsius and Fahrenheit."""
        if new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) is None:
            return
        if old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) is None:
            return
        if new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == old_attributes.get(
            ATTR_UNIT_OF_MEASUREMENT
        ):
            return
        new_state = self._attr_state
        if (
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfTemperature.FAHRENHEIT
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfTemperature.CELSIUS
        ):
            new_state = round(
                TemperatureConverter.convert(
                    float(self.state),
                    UnitOfTemperature.FAHRENHEIT,
                    UnitOfTemperature.CELSIUS,
                )
            )
            _LOGGER.debug(
                "Changing from F to C measurement is %s new is %s",
                self.state,
                new_state,
            )

        if (
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfTemperature.CELSIUS
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfTemperature.FAHRENHEIT
        ):
            new_state = round(
                TemperatureConverter.convert(
                    float(self.state),
                    UnitOfTemperature.CELSIUS,
                    UnitOfTemperature.FAHRENHEIT,
                )
            )
            _LOGGER.debug(
                "Changing from C to F measurement is %s new is %s",
                self.state,
                new_state,
            )

        self.hass.states.async_set(self.entity_id, new_state, new_attributes)


class PlantMinTemperature(PlantMinMax):
    """Entity class for min temperature threshold"""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_icon = ICON_TEMPERATURE
    _attr_native_max_value = TEMPERATURE_MAX_VALUE
    _attr_native_min_value = TEMPERATURE_MIN_VALUE
    _attr_native_step = 1
    _attr_translation_key = TRANSLATION_KEY_MIN_TEMPERATURE
    _entity_id_key = f"{ATTR_MIN} {READING_TEMPERATURE}"

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._default_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_TEMPERATURE, DEFAULT_MIN_TEMPERATURE
        )
        self._attr_unique_id = f"{config.entry_id}-min-temperature"
        super().__init__(hass, config, plantdevice)
        self._attr_native_unit_of_measurement = self.hass.config.units.temperature_unit

    def state_attributes_changed(
        self, old_attributes: dict[str, Any], new_attributes: dict[str, Any]
    ) -> None:
        """Convert temperature between Celsius and Fahrenheit."""
        if new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) is None:
            return
        if old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) is None:
            return
        if new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == old_attributes.get(
            ATTR_UNIT_OF_MEASUREMENT
        ):
            return
        new_state = self._attr_state
        if (
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfTemperature.FAHRENHEIT
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfTemperature.CELSIUS
        ):
            new_state = round(
                TemperatureConverter.convert(
                    float(self.state),
                    UnitOfTemperature.FAHRENHEIT,
                    UnitOfTemperature.CELSIUS,
                )
            )
            _LOGGER.debug(
                "Changing from F to C measurement is %s new is %s",
                self.state,
                new_state,
            )

        if (
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfTemperature.CELSIUS
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfTemperature.FAHRENHEIT
        ):
            new_state = round(
                TemperatureConverter.convert(
                    float(self.state),
                    UnitOfTemperature.CELSIUS,
                    UnitOfTemperature.FAHRENHEIT,
                )
            )
            _LOGGER.debug(
                "Changing from C to F measurement is %s new is %s",
                self.state,
                new_state,
            )

        self.hass.states.async_set(self.entity_id, new_state, new_attributes)


class PlantMaxIlluminance(PlantMinMax):
    """Entity class for max illuminance threshold"""

    _attr_device_class = f"{SensorDeviceClass.ILLUMINANCE} threshold"
    _attr_icon = ICON_ILLUMINANCE
    _attr_native_unit_of_measurement = LIGHT_LUX
    _attr_native_max_value = 200000
    _attr_native_min_value = 0
    _attr_native_step = 500
    _attr_translation_key = TRANSLATION_KEY_MAX_ILLUMINANCE
    _entity_id_key = f"{ATTR_MAX} {READING_ILLUMINANCE}"

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._default_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_ILLUMINANCE, DEFAULT_MAX_ILLUMINANCE
        )
        self._attr_unique_id = f"{config.entry_id}-max-illuminance"
        super().__init__(hass, config, plantdevice)


class PlantMinIlluminance(PlantMinMax):
    """Entity class for min illuminance threshold"""

    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_icon = ICON_ILLUMINANCE
    _attr_native_unit_of_measurement = LIGHT_LUX
    _attr_native_max_value = 200000
    _attr_native_min_value = 0
    _attr_native_step = 500
    _attr_translation_key = TRANSLATION_KEY_MIN_ILLUMINANCE
    _entity_id_key = f"{ATTR_MIN} {READING_ILLUMINANCE}"

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._default_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_ILLUMINANCE, DEFAULT_MIN_ILLUMINANCE
        )
        self._attr_unique_id = f"{config.entry_id}-min-illuminance"
        super().__init__(hass, config, plantdevice)


class PlantMaxDli(PlantMinMax):
    """Entity class for max DLI threshold"""

    _attr_device_class = f"{ATTR_DLI} threshold"
    _attr_icon = ICON_DLI
    _attr_native_unit_of_measurement = UNIT_DLI
    _attr_native_max_value = 100
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_translation_key = TRANSLATION_KEY_MAX_DLI
    _entity_id_key = f"{ATTR_MAX} {READING_DLI}"

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._default_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_DLI, DEFAULT_MAX_DLI
        )
        self._attr_unique_id = f"{config.entry_id}-max-dli"
        super().__init__(hass, config, plantdevice)


class PlantMinDli(PlantMinMax):
    """Entity class for min DLI threshold"""

    _attr_device_class = f"{ATTR_DLI} threshold"
    _attr_icon = ICON_DLI
    _attr_native_unit_of_measurement = UNIT_DLI
    _attr_native_max_value = 100
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_translation_key = TRANSLATION_KEY_MIN_DLI
    _entity_id_key = f"{ATTR_MIN} {READING_DLI}"

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._default_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_DLI, DEFAULT_MIN_DLI
        )
        self._attr_unique_id = f"{config.entry_id}-min-dli"
        super().__init__(hass, config, plantdevice)


class PlantMaxConductivity(PlantMinMax):
    """Entity class for max conductivity threshold"""

    _attr_device_class = f"{ATTR_CONDUCTIVITY} threshold"
    _attr_icon = ICON_CONDUCTIVITY
    _attr_native_unit_of_measurement = UnitOfConductivity.MICROSIEMENS_PER_CM
    _attr_native_max_value = 3000
    _attr_native_min_value = 0
    _attr_native_step = 50
    _attr_translation_key = TRANSLATION_KEY_MAX_CONDUCTIVITY
    _entity_id_key = f"{ATTR_MAX} {READING_CONDUCTIVITY}"

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._default_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_CONDUCTIVITY, DEFAULT_MAX_CONDUCTIVITY
        )
        self._attr_unique_id = f"{config.entry_id}-max-conductivity"
        super().__init__(hass, config, plantdevice)


class PlantMinConductivity(PlantMinMax):
    """Entity class for min conductivity threshold"""

    _attr_device_class = f"{ATTR_CONDUCTIVITY} threshold"
    _attr_icon = ICON_CONDUCTIVITY
    _attr_native_unit_of_measurement = UnitOfConductivity.MICROSIEMENS_PER_CM
    _attr_native_max_value = 3000
    _attr_native_min_value = 0
    _attr_native_step = 50
    _attr_translation_key = TRANSLATION_KEY_MIN_CONDUCTIVITY
    _entity_id_key = f"{ATTR_MIN} {READING_CONDUCTIVITY}"

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._default_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_CONDUCTIVITY, DEFAULT_MIN_CONDUCTIVITY
        )
        self._attr_unique_id = f"{config.entry_id}-min-conductivity"
        super().__init__(hass, config, plantdevice)


class PlantMaxHumidity(PlantMinMax):
    """Entity class for max humidity threshold"""

    _attr_device_class = f"{SensorDeviceClass.HUMIDITY} threshold"
    _attr_icon = ICON_HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_max_value = 100
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_translation_key = TRANSLATION_KEY_MAX_HUMIDITY
    _entity_id_key = f"{ATTR_MAX} {READING_HUMIDITY}"

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._default_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_HUMIDITY, DEFAULT_MAX_HUMIDITY
        )
        self._attr_unique_id = f"{config.entry_id}-max-humidity"
        super().__init__(hass, config, plantdevice)


class PlantMinHumidity(PlantMinMax):
    """Entity class for min humidity threshold"""

    _attr_device_class = f"{SensorDeviceClass.HUMIDITY} threshold"
    _attr_icon = ICON_HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_max_value = 100
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_translation_key = TRANSLATION_KEY_MIN_HUMIDITY
    _entity_id_key = f"{ATTR_MIN} {READING_HUMIDITY}"

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._default_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_HUMIDITY, DEFAULT_MIN_HUMIDITY
        )
        self._attr_unique_id = f"{config.entry_id}-min-humidity"
        super().__init__(hass, config, plantdevice)


class PlantMaxCo2(PlantMinMax):
    """Entity class for max CO2 threshold"""

    _attr_device_class = f"{SensorDeviceClass.CO2} threshold"
    _attr_icon = ICON_CO2
    _attr_native_unit_of_measurement = "ppm"
    _attr_native_max_value = 5000
    _attr_native_min_value = 0
    _attr_native_step = 50
    _attr_translation_key = TRANSLATION_KEY_MAX_CO2
    _entity_id_key = f"{ATTR_MAX} {READING_CO2}"

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._default_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_CO2, DEFAULT_MAX_CO2
        )
        self._attr_unique_id = f"{config.entry_id}-max-co2"
        super().__init__(hass, config, plantdevice)


class PlantMinCo2(PlantMinMax):
    """Entity class for min CO2 threshold"""

    _attr_device_class = f"{SensorDeviceClass.CO2} threshold"
    _attr_icon = ICON_CO2
    _attr_native_unit_of_measurement = "ppm"
    _attr_native_max_value = 5000
    _attr_native_min_value = 0
    _attr_native_step = 50
    _attr_translation_key = TRANSLATION_KEY_MIN_CO2
    _entity_id_key = f"{ATTR_MIN} {READING_CO2}"

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._default_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_CO2, DEFAULT_MIN_CO2
        )
        self._attr_unique_id = f"{config.entry_id}-min-co2"
        super().__init__(hass, config, plantdevice)


class PlantMaxSoilTemperature(PlantMinMax):
    """Entity class for max soil temperature threshold"""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_icon = ICON_SOIL_TEMPERATURE
    _attr_native_max_value = TEMPERATURE_MAX_VALUE
    _attr_native_min_value = TEMPERATURE_MIN_VALUE
    _attr_native_step = 1
    _attr_translation_key = TRANSLATION_KEY_MAX_SOIL_TEMPERATURE
    _entity_id_key = f"{ATTR_MAX} {READING_SOIL_TEMPERATURE}"

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._attr_unique_id = f"{config.entry_id}-max-soil-temperature"
        self._default_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_SOIL_TEMPERATURE, DEFAULT_MAX_SOIL_TEMPERATURE
        )
        super().__init__(hass, config, plantdevice)
        self._attr_native_unit_of_measurement = self.hass.config.units.temperature_unit

    def state_attributes_changed(
        self, old_attributes: dict[str, Any], new_attributes: dict[str, Any]
    ) -> None:
        """Convert temperature between Celsius and Fahrenheit."""
        if new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) is None:
            return
        if old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) is None:
            return
        if new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == old_attributes.get(
            ATTR_UNIT_OF_MEASUREMENT
        ):
            return
        new_state = self._attr_state
        if (
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfTemperature.FAHRENHEIT
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfTemperature.CELSIUS
        ):
            new_state = round(
                TemperatureConverter.convert(
                    float(self.state),
                    UnitOfTemperature.FAHRENHEIT,
                    UnitOfTemperature.CELSIUS,
                )
            )

        if (
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfTemperature.CELSIUS
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfTemperature.FAHRENHEIT
        ):
            new_state = round(
                TemperatureConverter.convert(
                    float(self.state),
                    UnitOfTemperature.CELSIUS,
                    UnitOfTemperature.FAHRENHEIT,
                )
            )

        self._attr_native_value = new_state
        self._attr_native_unit_of_measurement = new_attributes.get(
            ATTR_UNIT_OF_MEASUREMENT
        )


class PlantMinSoilTemperature(PlantMinMax):
    """Entity class for min soil temperature threshold"""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_icon = ICON_SOIL_TEMPERATURE
    _attr_native_max_value = TEMPERATURE_MAX_VALUE
    _attr_native_min_value = TEMPERATURE_MIN_VALUE
    _attr_native_step = 1
    _attr_translation_key = TRANSLATION_KEY_MIN_SOIL_TEMPERATURE
    _entity_id_key = f"{ATTR_MIN} {READING_SOIL_TEMPERATURE}"

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._default_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_SOIL_TEMPERATURE, DEFAULT_MIN_SOIL_TEMPERATURE
        )
        self._attr_unique_id = f"{config.entry_id}-min-soil-temperature"
        super().__init__(hass, config, plantdevice)
        self._attr_native_unit_of_measurement = self.hass.config.units.temperature_unit

    def state_attributes_changed(
        self, old_attributes: dict[str, Any], new_attributes: dict[str, Any]
    ) -> None:
        """Convert temperature between Celsius and Fahrenheit."""
        if new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) is None:
            return
        if old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) is None:
            return
        if new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == old_attributes.get(
            ATTR_UNIT_OF_MEASUREMENT
        ):
            return
        new_state = self._attr_state
        if (
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfTemperature.FAHRENHEIT
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfTemperature.CELSIUS
        ):
            new_state = round(
                TemperatureConverter.convert(
                    float(self.state),
                    UnitOfTemperature.FAHRENHEIT,
                    UnitOfTemperature.CELSIUS,
                )
            )

        if (
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfTemperature.CELSIUS
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfTemperature.FAHRENHEIT
        ):
            new_state = round(
                TemperatureConverter.convert(
                    float(self.state),
                    UnitOfTemperature.CELSIUS,
                    UnitOfTemperature.FAHRENHEIT,
                )
            )

        self._attr_native_value = new_state
        self._attr_native_unit_of_measurement = new_attributes.get(
            ATTR_UNIT_OF_MEASUREMENT
        )


class PlantLuxToPpfd(PlantMinMax):
    """Entity class for lux to PPFD conversion factor.

    The conversion factor varies based on light source:
    - Sunlight: ~0.0185 (default)
    - LED grow lights: ~0.014-0.020 depending on spectrum
    - HPS lights: ~0.013
    - Fluorescent: ~0.013-0.014

    See https://www.apogeeinstruments.com/conversion-ppfd-to-lux/
    """

    _attr_device_class = None
    _attr_icon = ICON_PPFD
    _attr_native_unit_of_measurement = None
    _attr_native_max_value = 0.1
    _attr_native_min_value = 0.001
    _attr_native_step = 0.0001
    _attr_suggested_display_precision = 4
    _attr_translation_key = TRANSLATION_KEY_LUX_TO_PPFD
    _entity_id_key = "lux to ppfd"

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._default_value = config.data[FLOW_PLANT_INFO].get(
            CONF_LUX_TO_PPFD, DEFAULT_LUX_TO_PPFD
        )
        self._attr_unique_id = f"{config.entry_id}-lux-to-ppfd"
        super().__init__(hass, config, plantdevice)
