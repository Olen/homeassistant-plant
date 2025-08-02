"""Meter entities for the plant integration"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import random

from homeassistant.components.integration.const import METHOD_TRAPEZOIDAL
from homeassistant.components.integration.sensor import IntegrationSensor
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.components.utility_meter.const import DAILY
from homeassistant.components.utility_meter.sensor import UtilityMeterSensor
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ICON,
    ATTR_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    LIGHT_LUX,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfConductivity,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import (
    Entity,
    EntityCategory,
    async_generate_entity_id,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from . import SETUP_DUMMY_SENSORS
from .const import (
    ATTR_CONDUCTIVITY,
    ATTR_DLI,
    ATTR_MOISTURE,
    ATTR_PLANT,
    ATTR_SENSORS,
    DATA_UPDATED,
    DEFAULT_LUX_TO_PPFD,
    DOMAIN,
    DOMAIN_SENSOR,
    FLOW_PLANT_INFO,
    FLOW_SENSOR_CONDUCTIVITY,
    FLOW_SENSOR_HUMIDITY,
    FLOW_SENSOR_ILLUMINANCE,
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_TEMPERATURE,
    ICON_CONDUCTIVITY,
    ICON_DLI,
    ICON_HUMIDITY,
    ICON_ILLUMINANCE,
    ICON_MOISTURE,
    ICON_PPFD,
    ICON_TEMPERATURE,
    READING_CONDUCTIVITY,
    READING_DLI,
    READING_HUMIDITY,
    READING_ILLUMINANCE,
    READING_MOISTURE,
    READING_PPFD,
    READING_TEMPERATURE,
    UNIT_CONDUCTIVITY,
    UNIT_DLI,
    UNIT_PPFD,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up Plant Sensors from a config entry."""
    _LOGGER.debug(entry.data)
    plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]

    if SETUP_DUMMY_SENSORS:
        sensor_entities = [
            PlantDummyMoisture(hass, entry, plant),
            PlantDummyTemperature(hass, entry, plant),
            PlantDummyIlluminance(hass, entry, plant),
            PlantDummyConductivity(hass, entry, plant),
            PlantDummyHumidity(hass, entry, plant),
        ]
        async_add_entities(sensor_entities)

    pcurb = PlantCurrentIlluminance(hass, entry, plant)
    pcurc = PlantCurrentConductivity(hass, entry, plant)
    pcurm = PlantCurrentMoisture(hass, entry, plant)
    pcurt = PlantCurrentTemperature(hass, entry, plant)
    pcurh = PlantCurrentHumidity(hass, entry, plant)
    plant_sensors = [
        pcurb,
        pcurc,
        pcurm,
        pcurt,
        pcurh,
    ]
    async_add_entities(plant_sensors)
    hass.data[DOMAIN][entry.entry_id][ATTR_SENSORS] = plant_sensors
    plant.add_sensors(
        temperature=pcurt,
        moisture=pcurm,
        conductivity=pcurc,
        illuminance=pcurb,
        humidity=pcurh,
    )

    # Create and add the integral-entities
    # Must be run after the sensors are added to the plant

    pcurppfd = PlantCurrentPpfd(hass, entry, plant)
    async_add_entities([pcurppfd])

    pintegral = PlantTotalLightIntegral(hass, entry, pcurppfd, plant)
    async_add_entities([pintegral], update_before_add=True)

    plant.add_calculations(pcurppfd, pintegral)

    pdli = PlantDailyLightIntegral(hass, entry, pintegral, plant)
    async_add_entities(new_entities=[pdli], update_before_add=True)

    plant.add_dli(dli=pdli)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True


class PlantCurrentStatus(RestoreSensor):
    """Parent class for the meter classes below"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._hass = hass
        self._config = config
        self._default_state = None
        self._plant = plantdevice
        self._tracker = []
        self._follow_external = True
        # self._conf_check_days = self._plant.check_days
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN}.{{}}", self.name, current_ids={}
        )
        if (
            not self._attr_native_value
            or self._attr_native_value == STATE_UNKNOWN
            or self._attr_native_value == STATE_UNAVAILABLE
        ):
            _LOGGER.debug(
                "Unknown native value for %s, setting to default: %s",
                self.entity_id,
                self._default_state,
            )
            self._attr_native_value = self._default_state

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    @property
    def device_info(self) -> dict:
        """Device info for devices"""
        return {
            "identifiers": {(DOMAIN, self._plant.unique_id)},
        }

    @property
    def extra_state_attributes(self) -> dict:
        if self._external_sensor:
            attributes = {
                "external_sensor": self.external_sensor,
                # "history_max": self._history.max,
                # "history_min": self._history.min,
            }
            return attributes

    @property
    def external_sensor(self) -> str:
        """The external sensor we are tracking"""
        return self._external_sensor

    def replace_external_sensor(self, new_sensor: str | None) -> None:
        """Modify the external sensor"""
        _LOGGER.info("Setting %s external sensor to %s", self.entity_id, new_sensor)
        # pylint: disable=attribute-defined-outside-init
        self._external_sensor = new_sensor
        self.async_track_entity(self.entity_id)
        self.async_track_entity(self.external_sensor)

        self.async_write_ha_state()

    def async_track_entity(self, entity_id: str) -> None:
        """Track state_changed of certain entities"""
        if entity_id and entity_id not in self._tracker:
            async_track_state_change_event(
                self._hass,
                list([entity_id]),
                self._state_changed_event,
            )
            self._tracker.append(entity_id)

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()

        # We do not restore the state for these.
        # They are read from the external sensor anyway
        self._attr_native_value = None
        if state:
            if "external_sensor" in state.attributes:
                self.replace_external_sensor(state.attributes["external_sensor"])
        self.async_track_entity(self.entity_id)
        if self.external_sensor:
            self.async_track_entity(self.external_sensor)

        async_dispatcher_connect(
            self._hass, DATA_UPDATED, self._schedule_immediate_update
        )

    async def async_update(self) -> None:
        """Set state and unit to the parent sensor state and unit"""
        if self.external_sensor:
            try:
                self._attr_native_value = float(
                    self._hass.states.get(self.external_sensor).state
                )
                if (
                    ATTR_UNIT_OF_MEASUREMENT
                    in self._hass.states.get(self.external_sensor).attributes
                ):
                    self._attr_native_unit_of_measurement = self._hass.states.get(
                        self.external_sensor
                    ).attributes[ATTR_UNIT_OF_MEASUREMENT]
            except AttributeError:
                _LOGGER.debug(
                    "Unknown external sensor for %s: %s, setting to default: %s",
                    self.entity_id,
                    self.external_sensor,
                    self._default_state,
                )
                self._attr_native_value = self._default_state
            except ValueError:
                _LOGGER.debug(
                    "Unknown external value for %s: %s = %s, setting to default: %s",
                    self.entity_id,
                    self.external_sensor,
                    self._hass.states.get(self.external_sensor).state,
                    self._default_state,
                )
                self._attr_native_value = self._default_state

        else:
            _LOGGER.debug(
                "External sensor not set for %s, setting to default: %s",
                self.entity_id,
                self._default_state,
            )
            self._attr_native_value = self._default_state

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)

    @callback
    def _state_changed_event(self, event):
        """Sensor state change event."""
        self.state_changed(event.data.get("entity_id"), event.data.get("new_state"))

    @callback
    def state_changed(self, entity_id, new_state):
        """Run on every update to allow for changes from the GUI and service call"""
        if not self.hass.states.get(self.entity_id):
            return
        if entity_id == self.entity_id:
            current_attrs = self.hass.states.get(self.entity_id).attributes
            if current_attrs.get("external_sensor") != self.external_sensor:
                self.replace_external_sensor(current_attrs.get("external_sensor"))

            if (
                ATTR_ICON in new_state.attributes
                and self.icon != new_state.attributes[ATTR_ICON]
            ):
                self._attr_icon = new_state.attributes[ATTR_ICON]

        if (
            self.external_sensor
            and new_state
            and new_state.state != STATE_UNKNOWN
            and new_state.state != STATE_UNAVAILABLE
        ):
            self._attr_native_value = new_state.state
            if ATTR_UNIT_OF_MEASUREMENT in new_state.attributes:
                self._attr_native_unit_of_measurement = new_state.attributes[
                    ATTR_UNIT_OF_MEASUREMENT
                ]
        else:
            self._attr_native_value = self._default_state


class PlantCurrentIlluminance(PlantCurrentStatus):
    """Entity class for the current illuminance meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_ILLUMINANCE}"
        )
        self._attr_unique_id = f"{config.entry_id}-current-illuminance"
        self._attr_icon = ICON_ILLUMINANCE
        self._attr_suggested_display_precision = 1
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(
            FLOW_SENSOR_ILLUMINANCE
        )
        self._attr_native_unit_of_measurement = LIGHT_LUX
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.ILLUMINANCE


class PlantCurrentConductivity(PlantCurrentStatus):
    """Entity class for the current conductivity meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_CONDUCTIVITY}"
        )
        self._attr_unique_id = f"{config.entry_id}-current-conductivity"
        self._attr_icon = ICON_CONDUCTIVITY
        self._attr_suggested_display_precision = 1
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(
            FLOW_SENSOR_CONDUCTIVITY
        )
        self._attr_native_unit_of_measurement = UnitOfConductivity.MICROSIEMENS_PER_CM

        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self) -> None:
        """Device class - not defined for conductivity"""
        return ATTR_CONDUCTIVITY


class PlantCurrentMoisture(PlantCurrentStatus):
    """Entity class for the current moisture meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_MOISTURE}"
        )
        self._attr_unique_id = f"{config.entry_id}-current-moisture"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_MOISTURE)
        self._attr_icon = ICON_MOISTURE
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_suggested_display_precision = 1

        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self) -> str:
        """Device class"""
        return ATTR_MOISTURE


class PlantCurrentTemperature(PlantCurrentStatus):
    """Entity class for the current temperature meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_TEMPERATURE}"
        )
        self._attr_unique_id = f"{config.entry_id}-current-temperature"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(
            FLOW_SENSOR_TEMPERATURE
        )
        self._attr_icon = ICON_TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_suggested_display_precision = 1
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.TEMPERATURE


class PlantCurrentHumidity(PlantCurrentStatus):
    """Entity class for the current humidity meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_HUMIDITY}"
        )
        self._attr_unique_id = f"{config.entry_id}-current-humidity"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_HUMIDITY)
        self._attr_icon = ICON_HUMIDITY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_suggested_display_precision = 1
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.HUMIDITY


class PlantCurrentPpfd(PlantCurrentStatus):
    """Entity reporting current PPFD calculated from LX"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_PPFD}"

        self._attr_unique_id = f"{config.entry_id}-current-ppfd"
        self._attr_unit_of_measurement = UNIT_PPFD
        self._attr_native_unit_of_measurement = UNIT_PPFD

        self._plant = plantdevice

        self._external_sensor = self._plant.sensor_illuminance.entity_id
        self._attr_icon = ICON_PPFD
        super().__init__(hass, config, plantdevice)
        self._follow_unit = False
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN_SENSOR}.{{}}", self.name, current_ids={}
        )

    @property
    def device_class(self) -> str:
        """Device class"""
        return None

    @property
    def entity_category(self) -> str:
        """The entity category"""
        return EntityCategory.DIAGNOSTIC

    @property
    def entity_registry_visible_default(self) -> str:
        return False

    def ppfd(self, value: float | int | str) -> float | str:
        """
        Returns a calculated PPFD-value from the lx-value

        See https://community.home-assistant.io/t/light-accumulation-for-xiaomi-flower-sensor/111180/3
        https://www.apogeeinstruments.com/conversion-ppfd-to-lux/
        μmol/m²/s
        """
        if value is not None and value != STATE_UNAVAILABLE and value != STATE_UNKNOWN:
            value = float(value) * DEFAULT_LUX_TO_PPFD / 1000000
        else:
            value = None

        return value

    async def async_update(self) -> None:
        """Run on every update to allow for changes from the GUI and service call"""
        if not self.hass.states.get(self.entity_id):
            return
        if self.external_sensor != self._plant.sensor_illuminance.entity_id:
            self.replace_external_sensor(self._plant.sensor_illuminance.entity_id)
        if self.external_sensor:
            external_sensor = self.hass.states.get(self.external_sensor)
            if external_sensor:
                self._attr_native_value = self.ppfd(external_sensor.state)
            else:
                self._attr_native_value = None
        else:
            self._attr_native_value = None

    @callback
    def state_changed(self, entity_id: str, new_state: str) -> None:
        """Run on every update to allow for changes from the GUI and service call"""
        if not self.hass.states.get(self.entity_id):
            return
        if self._external_sensor != self._plant.sensor_illuminance.entity_id:
            self.replace_external_sensor(self._plant.sensor_illuminance.entity_id)
        if self.external_sensor:
            external_sensor = self.hass.states.get(self.external_sensor)
            if external_sensor:
                self._attr_native_value = self.ppfd(external_sensor.state)
            else:
                self._attr_native_value = None
        else:
            self._attr_native_value = None


class PlantTotalLightIntegral(IntegrationSensor):
    """Entity class to calculate PPFD from LX"""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        illuminance_ppfd_sensor: Entity,
        plantdevice: Entity,
    ) -> None:
        """Initialize the sensor"""
        super().__init__(
            hass,
            integration_method=METHOD_TRAPEZOIDAL,
            name=f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} Total {READING_PPFD} Integral",
            round_digits=2,
            source_entity=illuminance_ppfd_sensor.entity_id,
            unique_id=f"{config.entry_id}-ppfd-integral",
            unit_prefix=None,
            unit_time=UnitOfTime.SECONDS,
            max_sub_interval=None,
        )
        self._unit_of_measurement = UNIT_DLI
        self._attr_icon = ICON_DLI
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN_SENSOR}.{{}}", self.name, current_ids={}
        )
        self._plant = plantdevice

    @property
    def entity_category(self) -> str:
        """The entity category"""
        return EntityCategory.DIAGNOSTIC

    @property
    def device_info(self) -> dict:
        """Device info for devices"""
        return {
            "identifiers": {(DOMAIN, self._plant.unique_id)},
        }

    @property
    def entity_registry_visible_default(self) -> str:
        return False

    def _unit(self, source_unit: str) -> str:
        """Override unit"""
        return self._unit_of_measurement


class PlantDailyLightIntegral(UtilityMeterSensor):
    """Entity class to calculate Daily Light Integral from PPDF"""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        illuminance_integration_sensor: Entity,
        plantdevice: Entity,
    ) -> None:
        """Initialize the sensor"""

        super().__init__(
            hass,
            cron_pattern=None,
            delta_values=None,
            meter_offset=timedelta(seconds=0),
            meter_type=DAILY,
            name=f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_DLI}",
            net_consumption=None,
            parent_meter=config.entry_id,
            source_entity=illuminance_integration_sensor.entity_id,
            tariff_entity=None,
            tariff=None,
            unique_id=f"{config.entry_id}-dli",
            sensor_always_available=True,
            suggested_entity_id=None,
            periodically_resetting=True,
        )
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN_SENSOR}.{{}}", self.name, current_ids={}
        )

        self._unit_of_measurement = UNIT_DLI
        self._attr_icon = ICON_DLI
        self._attr_suggested_display_precision = 2
        self._plant = plantdevice

    @property
    def device_class(self) -> str:
        return ATTR_DLI

    @property
    def device_info(self) -> dict:
        """Device info for devices"""
        return {
            "identifiers": {(DOMAIN, self._plant.unique_id)},
        }


class PlantDummyStatus(SensorEntity):
    """Simple dummy sensors. Parent class"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the dummy sensor."""
        self._config = config
        self._default_state = STATE_UNKNOWN
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN}.{{}}", self.name, current_ids={}
        )
        self._plant = plantdevice

        if not self._attr_native_value or self._attr_native_value == STATE_UNKNOWN:
            self._attr_native_value = self._default_state

    # @property
    # def device_info(self) -> dict:
    #     """Device info for devices"""
    #     return {
    #         "identifiers": {(DOMAIN, self._plant.unique_id)},
    #     }


class PlantDummyIlluminance(PlantDummyStatus):
    """Dummy sensor"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""
        self._attr_name = (
            f"Dummy {config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_ILLUMINANCE}"
        )
        self._attr_unique_id = f"{config.entry_id}-dummy-illuminance"
        self._attr_icon = ICON_ILLUMINANCE
        self._attr_native_unit_of_measurement = LIGHT_LUX
        self._attr_native_value = random.randint(20, 50) * 1000

        super().__init__(hass, config, plantdevice)

    async def async_update(self) -> int:
        """Give out a dummy value"""
        if datetime.now().hour < 5:
            self._attr_native_value = random.randint(1, 10) * 100
        elif datetime.now().hour < 15:
            self._attr_native_value = random.randint(20, 50) * 1000
        else:
            self._attr_native_value = random.randint(1, 10) * 100

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.ILLUMINANCE


class PlantDummyConductivity(PlantDummyStatus):
    """Dummy sensor"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""
        self._attr_name = (
            f"Dummy {config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_CONDUCTIVITY}"
        )
        self._attr_unique_id = f"{config.entry_id}-dummy-conductivity"
        self._attr_icon = ICON_CONDUCTIVITY
        self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY
        self._attr_native_value = random.randint(40, 200) * 10

        super().__init__(hass, config, plantdevice)

    async def async_update(self) -> int:
        """Give out a dummy value"""
        self._attr_native_value = random.randint(40, 200) * 10

    @property
    def device_class(self) -> str:
        """Device class"""
        return ATTR_CONDUCTIVITY


class PlantDummyMoisture(PlantDummyStatus):
    """Dummy sensor"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""
        self._attr_name = (
            f"Dummy {config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_MOISTURE}"
        )
        self._attr_unique_id = f"{config.entry_id}-dummy-moisture"
        self._attr_icon = ICON_MOISTURE
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_value = random.randint(10, 70)

        super().__init__(hass, config, plantdevice)

    async def async_update(self) -> None:
        """Give out a dummy value"""
        self._attr_native_value = random.randint(10, 70)

    @property
    def device_class(self) -> str:
        """Device class"""
        return ATTR_MOISTURE


class PlantDummyTemperature(PlantDummyStatus):
    """Dummy sensor"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""

        self._attr_name = (
            f"Dummy {config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_TEMPERATURE}"
        )
        self._attr_unique_id = f"{config.entry_id}-dummy-temperature"
        self._attr_icon = ICON_TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_native_value = random.randint(15, 20)

        super().__init__(hass, config, plantdevice)

    async def async_update(self) -> int:
        """Give out a dummy value"""
        self._attr_native_value = random.randint(15, 20)

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.TEMPERATURE


class PlantDummyHumidity(PlantDummyStatus):
    """Dummy sensor"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""
        self._attr_name = (
            f"Dummy {config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_HUMIDITY}"
        )
        self._attr_unique_id = f"{config.entry_id}-dummy-humidity"
        self._attr_icon = ICON_HUMIDITY
        self._attr_native_unit_of_measurement = PERCENTAGE
        super().__init__(hass, config, plantdevice)
        self._attr_native_value = random.randint(25, 90)

    async def async_update(self) -> int:
        """Give out a dummy value"""
        test = random.randint(0, 100)
        if test > 50:
            self._attr_native_value = random.randint(25, 90)

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.HUMIDITY
