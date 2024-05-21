"""Max/Min threshold classes for the plant device"""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    LIGHT_LUX,
    PERCENTAGE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import (
    Entity,
    EntityCategory,
    async_generate_entity_id,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import (
    ATTR_CONDUCTIVITY,
    ATTR_MAX,
    ATTR_MIN,
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
    DATA_UPDATED,
    DEFAULT_MAX_CONDUCTIVITY,
    DEFAULT_MAX_DLI,
    DEFAULT_MAX_HUMIDITY,
    DEFAULT_MAX_ILLUMINANCE,
    DEFAULT_MAX_MOISTURE,
    DEFAULT_MAX_TEMPERATURE,
    DEFAULT_MIN_CONDUCTIVITY,
    DEFAULT_MIN_DLI,
    DEFAULT_MIN_HUMIDITY,
    DEFAULT_MIN_ILLUMINANCE,
    DEFAULT_MIN_MOISTURE,
    DEFAULT_MIN_TEMPERATURE,
    DOMAIN,
    FLOW_PLANT_INFO,
    FLOW_PLANT_LIMITS,
    READING_CONDUCTIVITY,
    READING_DLI,
    READING_HUMIDITY,
    READING_ILLUMINANCE,
    READING_MOISTURE,
    READING_TEMPERATURE,
    UNIT_CONDUCTIVITY,
    UNIT_PPFD,
)

_LOGGER = logging.getLogger(__name__)


class PlantMinMax(NumberEntity):
    """Parent class for the min/max classes below"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._config = config
        self._hass = hass
        self._plant = plantdevice
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN}.{{}}", self.name, current_ids={}
        )
        # pylint: disable=no-member
        if not self._attr_value or self._attr_value == STATE_UNKNOWN:
            self._attr_value = self._default_value

    @property
    def entity_category(self) -> str:
        """The entity category"""
        return EntityCategory.CONFIG

    # @property
    # def unit_of_measurement(self) -> str | None:
    #     """The unit of measurement"""
    #     return self._attr_unit_of_measurement

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

    def state_changed(self, old_state, new_state):
        """Ensure that we store the state if changed from the UI"""
        _LOGGER.debug(
            "State of %s changed from %s to %s, attr_state = %s",
            self.entity_id,
            old_state,
            new_state,
            self._attr_state,
        )
        self._attr_state = new_state

    def state_attributes_changed(self, old_attributes, new_attributes):
        """Placeholder"""

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

    async def not_async_added_to_hass(self) -> None:
        """Restore state of thresholds on startup."""
        await super().async_added_to_hass()

        # We track changes to our own state so we can update ourselves if state si changed
        # from the UI or by other means
        async_track_state_change_event(
            self._hass,
            list([self.entity_id]),
            self._state_changed_event,
        )

        # Restore state and attributes from DB
        state = await self.async_get_last_state()
        if not state:
            return
        self._attr_state = state.state
        self._attr_native_unit_of_measurement = state.attributes.get(
            ATTR_UNIT_OF_MEASUREMENT
        )

        async_dispatcher_connect(
            self.hass, DATA_UPDATED, self._schedule_immediate_update
        )

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)


class PlantMaxMoisture(PlantMinMax):
    """Entity class for max moisture threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {ATTR_MAX} {READING_MOISTURE}"
        )
        self._attr_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_MOISTURE, DEFAULT_MAX_MOISTURE
        )
        self._attr_unique_id = f"{config.entry_id}-max-moisture"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_max_value = 100
        self._attr_native_min_value = 0
        self._attr_native_step = 1

        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return f"{SensorDeviceClass.HUMIDITY} threshold"


class PlantMinMoisture(PlantMinMax):
    """Entity class for min moisture threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {ATTR_MIN} {READING_MOISTURE}"
        )
        self._attr_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_MOISTURE, DEFAULT_MIN_MOISTURE
        )
        self._attr_unique_id = f"{config.entry_id}-min-moisture"
        super().__init__(hass, config, plantdevice)
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_max_value = 100
        self._attr_native_min_value = 0
        self._attr_native_step = 1

    @property
    def device_class(self):
        return f"{SensorDeviceClass.HUMIDITY} threshold"


class PlantMaxTemperature(PlantMinMax):
    """Entity class for max temperature threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._attr_name = f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {ATTR_MAX} {READING_TEMPERATURE}"
        self._attr_unique_id = f"{config.entry_id}-max-temperature"

        self._attr_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_TEMPERATURE, DEFAULT_MAX_TEMPERATURE
        )
        super().__init__(hass, config, plantdevice)
        self._attr_native_unit_of_measurement = self._hass.config.units.temperature_unit
        self._attr_native_max_value = 100
        self._attr_native_min_value = 0
        self._attr_native_step = 1

    @property
    def device_class(self):
        return f"{SensorDeviceClass.TEMPERATURE} threshold"

    @property
    def not_unit_of_measurement(self) -> str | None:
        """Get unit of measurement from the temperature meter"""
        if (
            not hasattr(self, "_attr_unit_of_measurement")
            or self._attr_native_unit_of_measurement is None
        ):
            self._attr_native_unit_of_measurement = self._default_unit_of_measurement

        if self._plant.sensor_temperature:
            if not self._plant.sensor_temperature.unit_of_measurement:
                return self._attr_native_unit_of_measurement
            if (
                self._attr_native_unit_of_measurement
                != self._plant.sensor_temperature.unit_of_measurement
            ):
                self._attr_native_unit_of_measurement = (
                    self._plant.sensor_temperature.unit_of_measurement
                )

        return self._attr_native_unit_of_measurement

    def state_attributes_changed(self, old_attributes, new_attributes):
        """Calculate C or F"""
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
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°F"
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°C"
        ):
            new_state = round(
                TemperatureConverter.convert(
                    temperature=float(self.state),
                    from_unit=UnitOfTemperature.FAHRENHEIT,
                    to_unit=UnitOfTemperature.CELSIUS,
                )
            )
            _LOGGER.debug(
                "Changing from F to C measurement is %s new is %s",
                self.state,
                new_state,
            )

        if (
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°C"
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°F"
        ):
            new_state = round(
                TemperatureConverter.convert(
                    temperature=float(self.state),
                    from_unit=UnitOfTemperature.CELSIUS,
                    to_unit=UnitOfTemperature.FAHRENHEIT,
                )
            )
            _LOGGER.debug(
                "Changing from C to F measurement is %s new is %s",
                self.state,
                new_state,
            )

        self._hass.states.set(self.entity_id, new_state, new_attributes)


class PlantMinTemperature(PlantMinMax):
    """Entity class for min temperature threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._attr_name = f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {ATTR_MIN} {READING_TEMPERATURE}"
        self._attr_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_TEMPERATURE, DEFAULT_MIN_TEMPERATURE
        )

        self._attr_unique_id = f"{config.entry_id}-min-temperature"
        super().__init__(hass, config, plantdevice)
        self._attr_native_unit_of_measurement = self._hass.config.units.temperature_unit
        self._attr_native_max_value = 100
        self._attr_native_min_value = 0
        self._attr_native_step = 1

    @property
    def device_class(self):
        return f"{SensorDeviceClass.TEMPERATURE} threshold"

    @property
    def not_unit_of_measurement(self) -> str | None:
        if (
            not hasattr(self, "_attr_native_unit_of_measurement")
            or self._attr_native_unit_of_measurement is None
        ):
            self._attr_native_unit_of_measurement = self._default_unit_of_measurement

        if self._plant.sensor_temperature:
            if not self._plant.sensor_temperature.unit_of_measurement:
                return self._attr_native_unit_of_measurement
            if (
                self._attr_native_unit_of_measurement
                != self._plant.sensor_temperature.unit_of_measurement
            ):
                self._attr_native_unit_of_measurement = (
                    self._plant.sensor_temperature.unit_of_measurement
                )

        return self._attr_native_unit_of_measurement

    def state_attributes_changed(self, old_attributes, new_attributes):
        """Calculate C or F"""
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
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°F"
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°C"
        ):
            new_state = round(
                TemperatureConverter.convert(
                    temperature=float(self.state),
                    from_unit=UnitOfTemperature.FAHRENHEIT,
                    to_unit=UnitOfTemperature.CELSIUS,
                )
            )
            _LOGGER.debug(
                "Changing from F to C measurement is %s new is %s",
                self.state,
                new_state,
            )

            # new_state = int(round((int(self.state) - 32) * 0.5556, 0))

        if (
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°C"
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°F"
        ):
            new_state = round(
                TemperatureConverter.convert(
                    temperature=float(self.state),
                    from_unit=UnitOfTemperature.CELSIUS,
                    to_unit=UnitOfTemperature.FAHRENHEIT,
                )
            )
            _LOGGER.debug(
                "Changing from C to F measurement is %s new is %s",
                self.state,
                new_state,
            )

        self._hass.states.set(self.entity_id, new_state, new_attributes)


class PlantMaxIlluminance(PlantMinMax):
    """Entity class for max illuminance threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._attr_name = f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {ATTR_MAX} {READING_ILLUMINANCE}"
        self._attr_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_ILLUMINANCE, DEFAULT_MAX_ILLUMINANCE
        )
        self._attr_unique_id = f"{config.entry_id}-max-illuminance"
        self._attr_native_unit_of_measurement = LIGHT_LUX
        super().__init__(hass, config, plantdevice)
        self._attr_native_max_value = 200000
        self._attr_native_min_value = 0
        self._attr_native_step = 500

    @property
    def device_class(self):
        return f"{SensorDeviceClass.ILLUMINANCE} threshold"


class PlantMinIlluminance(PlantMinMax):
    """Entity class for min illuminance threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._attr_name = f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {ATTR_MIN} {READING_ILLUMINANCE}"
        self._attr_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_ILLUMINANCE, DEFAULT_MIN_ILLUMINANCE
        )
        self._attr_unique_id = f"{config.entry_id}-min-illuminance"
        self._attr_native_unit_of_measurement = LIGHT_LUX
        super().__init__(hass, config, plantdevice)
        self._attr_native_max_value = 200000
        self._attr_native_min_value = 0
        self._attr_native_step = 500

    @property
    def device_class(self):
        return f"{SensorDeviceClass.ILLUMINANCE} threshold"


class PlantMaxDli(PlantMinMax):
    """Entity class for max illuminance threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {ATTR_MAX} {READING_DLI}"
        )
        self._attr_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_DLI, DEFAULT_MAX_DLI
        )
        self._attr_unique_id = f"{config.entry_id}-max-dli"
        self._attr_native_unit_of_measurement = UNIT_PPFD
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return f"{SensorDeviceClass.ILLUMINANCE} threshold"


class PlantMinDli(PlantMinMax):
    """Entity class for min illuminance threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {ATTR_MIN} {READING_DLI}"
        )
        self._attr_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_DLI, DEFAULT_MIN_DLI
        )
        self._attr_unique_id = f"{config.entry_id}-min-dli"
        self._attr_native_unit_of_measurement = UNIT_PPFD

        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return SensorDeviceClass.ILLUMINANCE


class PlantMaxConductivity(PlantMinMax):
    """Entity class for max conductivity threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._attr_name = f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {ATTR_MAX} {READING_CONDUCTIVITY}"
        self._attr_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_CONDUCTIVITY, DEFAULT_MAX_CONDUCTIVITY
        )
        self._attr_unique_id = f"{config.entry_id}-max-conductivity"
        self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return f"{ATTR_CONDUCTIVITY} threshold"


class PlantMinConductivity(PlantMinMax):
    """Entity class for min conductivity threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._attr_name = f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {ATTR_MIN} {READING_CONDUCTIVITY}"
        self._attr_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_CONDUCTIVITY, DEFAULT_MIN_CONDUCTIVITY
        )
        self._attr_unique_id = f"{config.entry_id}-min-conductivity"
        self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY

        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return f"{ATTR_CONDUCTIVITY} threshold"


class PlantMaxHumidity(PlantMinMax):
    """Entity class for max humidity threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {ATTR_MAX} {READING_HUMIDITY}"
        )
        self._attr_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_HUMIDITY, DEFAULT_MAX_HUMIDITY
        )
        self._attr_unique_id = f"{config.entry_id}-max-humidity"
        self._attr_native_unit_of_measurement = PERCENTAGE

        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return f"{SensorDeviceClass.HUMIDITY} threshold"


class PlantMinHumidity(PlantMinMax):
    """Entity class for min conductivity threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {ATTR_MIN} {READING_HUMIDITY}"
        )
        self._attr_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_HUMIDITY, DEFAULT_MIN_HUMIDITY
        )
        self._attr_unique_id = f"{config.entry_id}-min-humidity"
        self._attr_native_unit_of_measurement = PERCENTAGE
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return f"{SensorDeviceClass.HUMIDITY} threshold"
