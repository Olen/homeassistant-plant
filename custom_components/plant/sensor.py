"""Meter entities for the plant integration"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta

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
    CONCENTRATION_PARTS_PER_MILLION,
    LIGHT_LUX,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfConductivity,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import (
    Entity,
    EntityCategory,
    async_generate_entity_id,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import (
    EVENT_ENTITY_REGISTRY_UPDATED,
    EventEntityRegistryUpdatedData,
)
from homeassistant.helpers.event import (
    async_track_state_change_event,
)

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
    FLOW_SENSOR_CO2,
    FLOW_SENSOR_CONDUCTIVITY,
    FLOW_SENSOR_HUMIDITY,
    FLOW_SENSOR_ILLUMINANCE,
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_SOIL_TEMPERATURE,
    FLOW_SENSOR_TEMPERATURE,
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
    READING_PPFD,
    READING_SOIL_TEMPERATURE,
    READING_TEMPERATURE,
    TRANSLATION_KEY_CO2,
    TRANSLATION_KEY_CONDUCTIVITY,
    TRANSLATION_KEY_DAILY_LIGHT_INTEGRAL,
    TRANSLATION_KEY_HUMIDITY,
    TRANSLATION_KEY_ILLUMINANCE,
    TRANSLATION_KEY_MOISTURE,
    TRANSLATION_KEY_PPFD,
    TRANSLATION_KEY_SOIL_TEMPERATURE,
    TRANSLATION_KEY_TEMPERATURE,
    TRANSLATION_KEY_TOTAL_LIGHT_INTEGRAL,
    UNIT_DLI,
    UNIT_PPFD,
    UNIT_TOTAL_LIGHT_INTEGRAL,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> bool:
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
    pcurco2 = PlantCurrentCo2(hass, entry, plant)
    pcurst = PlantCurrentSoilTemperature(hass, entry, plant)
    plant_sensors = [
        pcurb,
        pcurc,
        pcurm,
        pcurt,
        pcurh,
        pcurco2,
        pcurst,
    ]
    async_add_entities(plant_sensors)
    hass.data[DOMAIN][entry.entry_id][ATTR_SENSORS] = plant_sensors
    plant.add_sensors(
        temperature=pcurt,
        moisture=pcurm,
        conductivity=pcurc,
        illuminance=pcurb,
        humidity=pcurh,
        co2=pcurco2,
        soil_temperature=pcurst,
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

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    # Subclasses should override this with their FLOW_SENSOR_* constant
    _config_key: str | None = None

    # Subclasses should override this with their READING_* constant for entity_id generation
    _entity_id_key: str | None = None

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self.hass = hass
        self._config = config
        self._default_state = None
        self._plant = plantdevice
        self._tracker = []
        self._follow_external = True
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN}.{{}}", self._entity_id_key, current_ids={}
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
    def device_info(self) -> DeviceInfo:
        """Device info for devices"""
        return DeviceInfo(
            identifiers={(DOMAIN, self._plant.unique_id)},
        )

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
        """Modify the external sensor and persist to config entry."""
        _LOGGER.info("Setting %s external sensor to %s", self.entity_id, new_sensor)
        # pylint: disable=attribute-defined-outside-init
        self._external_sensor = new_sensor
        self.async_track_entity(self.entity_id)
        self.async_track_entity(self.external_sensor)

        # Persist the change to config entry if we have a config key
        if self._config_key:
            self._update_config_entry(new_sensor)

        self.async_write_ha_state()

    def _update_config_entry(self, new_sensor: str | None) -> None:
        """Update the config entry with the new sensor value."""
        if not self._config_key:
            return

        # Get current data and update the sensor assignment
        new_data = dict(self._config.data)
        new_plant_info = dict(new_data.get(FLOW_PLANT_INFO, {}))
        new_plant_info[self._config_key] = new_sensor
        new_data[FLOW_PLANT_INFO] = new_plant_info

        self.hass.config_entries.async_update_entry(self._config, data=new_data)
        _LOGGER.debug(
            "Updated config entry %s with %s=%s",
            self._config.entry_id,
            self._config_key,
            new_sensor,
        )

    def async_track_entity(self, entity_id: str) -> None:
        """Track state_changed of certain entities"""
        if entity_id and entity_id not in self._tracker:
            async_track_state_change_event(
                self.hass,
                [entity_id],
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
            self.hass, DATA_UPDATED, self._schedule_immediate_update
        )

        # Listen for entity registry updates to handle entity_id changes and deletions
        @callback
        def _handle_entity_registry_update(
            event: Event[EventEntityRegistryUpdatedData],
        ) -> None:
            """Handle entity registry updates."""
            action = event.data["action"]
            if action == "update":
                # Check if this is our external sensor being renamed
                if "old_entity_id" not in event.data:
                    return
                old_entity_id = event.data["old_entity_id"]
                new_entity_id = event.data["entity_id"]
                if self._external_sensor and old_entity_id == self._external_sensor:
                    _LOGGER.debug(
                        "External sensor renamed from %s to %s, updating tracking",
                        old_entity_id,
                        new_entity_id,
                    )
                    self.replace_external_sensor(new_entity_id)
            elif action == "remove":
                # Check if our external sensor was deleted
                entity_id = event.data["entity_id"]
                if self._external_sensor and entity_id == self._external_sensor:
                    _LOGGER.info(
                        "External sensor %s was deleted, clearing reference",
                        entity_id,
                    )
                    self.replace_external_sensor(None)

        self.async_on_remove(
            self.hass.bus.async_listen(
                EVENT_ENTITY_REGISTRY_UPDATED,
                _handle_entity_registry_update,
            )
        )

    async def async_update(self) -> None:
        """Set state and unit to the parent sensor state and unit"""
        if self.external_sensor:
            try:
                self._attr_native_value = float(
                    self.hass.states.get(self.external_sensor).state
                )
                if (
                    ATTR_UNIT_OF_MEASUREMENT
                    in self.hass.states.get(self.external_sensor).attributes
                ):
                    self._attr_native_unit_of_measurement = self.hass.states.get(
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
                    self.hass.states.get(self.external_sensor).state,
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
    def _schedule_immediate_update(self) -> None:
        """Schedule an immediate state update."""
        self.async_schedule_update_ha_state(True)

    @callback
    def _state_changed_event(self, event: Event) -> None:
        """Handle sensor state change event."""
        self.state_changed(event.data.get("entity_id"), event.data.get("new_state"))

    @callback
    def state_changed(self, entity_id: str | None, new_state: State | None) -> None:
        """Handle state changes from GUI and service calls."""
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

    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_icon = ICON_ILLUMINANCE
    _attr_native_unit_of_measurement = LIGHT_LUX
    _attr_suggested_display_precision = 1
    _attr_translation_key = TRANSLATION_KEY_ILLUMINANCE
    _config_key = FLOW_SENSOR_ILLUMINANCE
    _entity_id_key = READING_ILLUMINANCE

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_unique_id = f"{config.entry_id}-current-illuminance"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(
            FLOW_SENSOR_ILLUMINANCE
        )
        super().__init__(hass, config, plantdevice)


class PlantCurrentConductivity(PlantCurrentStatus):
    """Entity class for the current conductivity meter"""

    # No official device class for conductivity - use custom string for UI
    _attr_device_class = ATTR_CONDUCTIVITY
    _attr_icon = ICON_CONDUCTIVITY
    _attr_native_unit_of_measurement = UnitOfConductivity.MICROSIEMENS_PER_CM
    _attr_suggested_display_precision = 1
    _attr_translation_key = TRANSLATION_KEY_CONDUCTIVITY
    _config_key = FLOW_SENSOR_CONDUCTIVITY
    _entity_id_key = READING_CONDUCTIVITY

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_unique_id = f"{config.entry_id}-current-conductivity"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(
            FLOW_SENSOR_CONDUCTIVITY
        )
        super().__init__(hass, config, plantdevice)


class PlantCurrentMoisture(PlantCurrentStatus):
    """Entity class for the current moisture meter"""

    # No official device class for moisture - use custom string for UI
    _attr_device_class = ATTR_MOISTURE
    _attr_icon = ICON_MOISTURE
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 1
    _attr_translation_key = TRANSLATION_KEY_MOISTURE
    _config_key = FLOW_SENSOR_MOISTURE
    _entity_id_key = READING_MOISTURE

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_unique_id = f"{config.entry_id}-current-moisture"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_MOISTURE)
        super().__init__(hass, config, plantdevice)


class PlantCurrentTemperature(PlantCurrentStatus):
    """Entity class for the current temperature meter"""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_icon = ICON_TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1
    _attr_translation_key = TRANSLATION_KEY_TEMPERATURE
    _config_key = FLOW_SENSOR_TEMPERATURE
    _entity_id_key = READING_TEMPERATURE

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_unique_id = f"{config.entry_id}-current-temperature"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(
            FLOW_SENSOR_TEMPERATURE
        )
        super().__init__(hass, config, plantdevice)


class PlantCurrentHumidity(PlantCurrentStatus):
    """Entity class for the current humidity meter"""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_icon = ICON_HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 1
    _attr_translation_key = TRANSLATION_KEY_HUMIDITY
    _config_key = FLOW_SENSOR_HUMIDITY
    _entity_id_key = READING_HUMIDITY

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_unique_id = f"{config.entry_id}-current-humidity"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_HUMIDITY)
        super().__init__(hass, config, plantdevice)


class PlantCurrentCo2(PlantCurrentStatus):
    """Entity class for the current CO2 meter"""

    _attr_device_class = SensorDeviceClass.CO2
    _attr_icon = ICON_CO2
    _attr_native_unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION
    _attr_suggested_display_precision = 0
    _attr_translation_key = TRANSLATION_KEY_CO2
    _config_key = FLOW_SENSOR_CO2
    _entity_id_key = READING_CO2

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_unique_id = f"{config.entry_id}-current-co2"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_CO2)
        super().__init__(hass, config, plantdevice)


class PlantCurrentSoilTemperature(PlantCurrentStatus):
    """Entity class for the current soil temperature meter"""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_icon = ICON_SOIL_TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1
    _attr_translation_key = TRANSLATION_KEY_SOIL_TEMPERATURE
    _config_key = FLOW_SENSOR_SOIL_TEMPERATURE
    _entity_id_key = READING_SOIL_TEMPERATURE

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_unique_id = f"{config.entry_id}-current-soil-temperature"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(
            FLOW_SENSOR_SOIL_TEMPERATURE
        )
        super().__init__(hass, config, plantdevice)


class PlantCurrentPpfd(PlantCurrentStatus):
    """Entity reporting current PPFD calculated from LX"""

    _attr_device_class = None
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_visible_default = False
    _attr_icon = ICON_PPFD
    _attr_native_unit_of_measurement = UNIT_PPFD
    _attr_translation_key = TRANSLATION_KEY_PPFD
    _entity_id_key = READING_PPFD

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_unique_id = f"{config.entry_id}-current-ppfd"
        self._attr_unit_of_measurement = UNIT_PPFD
        self._plant = plantdevice
        self._external_sensor = self._plant.sensor_illuminance.entity_id
        super().__init__(hass, config, plantdevice)
        self._follow_unit = False
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN_SENSOR}.{{}}", self._entity_id_key, current_ids={}
        )

    def ppfd(self, value: float | int | str) -> float | str:
        """
        Returns a calculated PPFD-value from the lx-value

        See https://community.home-assistant.io/t/light-accumulation-for-xiaomi-flower-sensor/111180/3
        https://www.apogeeinstruments.com/conversion-ppfd-to-lux/
        μmol/m²/s

        The conversion factor is configurable per plant to account for different
        light sources (sunlight ~0.0185, LED grow lights ~0.014-0.020, HPS ~0.013).
        """
        if value is not None and value != STATE_UNAVAILABLE and value != STATE_UNKNOWN:
            # Use plant's configurable conversion factor, fallback to default
            lux_to_ppfd = DEFAULT_LUX_TO_PPFD
            if (
                self._plant.lux_to_ppfd is not None
                and self._plant.lux_to_ppfd.native_value is not None
            ):
                lux_to_ppfd = float(self._plant.lux_to_ppfd.native_value)
            value = float(value) * lux_to_ppfd / 1000000
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
    def state_changed(self, entity_id: str | None, new_state: State | None) -> None:
        """Handle state changes from GUI and service calls."""
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

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_visible_default = False
    _attr_icon = ICON_DLI
    _attr_translation_key = TRANSLATION_KEY_TOTAL_LIGHT_INTEGRAL

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        illuminance_ppfd_sensor: Entity,
        plantdevice: Entity,
    ) -> None:
        """Initialize the sensor"""
        self._plant = plantdevice
        # Store the source sensor's unique_id for tracking entity_id changes
        self._source_unique_id = illuminance_ppfd_sensor.unique_id
        self._state_change_unsub = None
        self._state_report_unsub = None
        super().__init__(
            hass,
            integration_method=METHOD_TRAPEZOIDAL,
            name=f"Total {READING_PPFD} Integral",
            round_digits=2,
            source_entity=illuminance_ppfd_sensor.entity_id,
            unique_id=f"{config.entry_id}-ppfd-integral",
            unit_prefix=None,
            unit_time=UnitOfTime.SECONDS,
            max_sub_interval=None,
        )
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN_SENSOR}.{{}}", f"Total {READING_PPFD} Integral", current_ids={}
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Device info for devices"""
        return DeviceInfo(
            identifiers={(DOMAIN, self._plant.unique_id)},
        )

    def _calculate_unit(self, source_unit: str) -> str:
        """Override unit calculation to return the correct integrated unit.

        The parent IntegrationSensor tries to derive the unit by appending
        the time unit to the source unit (e.g., "mol/s⋅m²" + "s" = "mol/s⋅m²s").
        We override this to return mol/m² (the seconds cancel out when
        integrating mol/s⋅m² over time).
        """
        return UNIT_TOTAL_LIGHT_INTEGRAL

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        # Listen for entity registry updates to handle entity_id changes
        @callback
        def _handle_entity_registry_update(
            event: Event[EventEntityRegistryUpdatedData],
        ) -> None:
            """Handle entity registry updates."""
            if event.data["action"] != "update":
                return
            # Check if this is our source entity being renamed
            if "old_entity_id" not in event.data:
                return
            old_entity_id = event.data["old_entity_id"]
            new_entity_id = event.data["entity_id"]
            if old_entity_id == self._source_entity:
                _LOGGER.debug(
                    "Source entity renamed from %s to %s, updating tracking",
                    old_entity_id,
                    new_entity_id,
                )
                self._update_source_entity(new_entity_id)

        self.async_on_remove(
            self.hass.bus.async_listen(
                EVENT_ENTITY_REGISTRY_UPDATED,
                _handle_entity_registry_update,
            )
        )

    @callback
    def _update_source_entity(self, new_entity_id: str) -> None:
        """Update the source entity when its entity_id changes."""
        self._source_entity = new_entity_id
        self._sensor_source_id = new_entity_id
        # Note: The state change tracking was set up by the parent class
        # and uses the old entity_id. We need to trigger a reload to
        # properly update the tracking, or the user needs to restart HA.
        _LOGGER.info(
            "Updated source entity to %s. A restart may be required for "
            "state tracking to work correctly.",
            new_entity_id,
        )


class PlantDailyLightIntegral(UtilityMeterSensor):
    """Entity class to calculate Daily Light Integral from PPFD"""

    _attr_has_entity_name = True
    # Custom device class for DLI (no official HA device class)
    _attr_device_class = ATTR_DLI
    _attr_icon = ICON_DLI
    _attr_suggested_display_precision = 2
    _attr_translation_key = TRANSLATION_KEY_DAILY_LIGHT_INTEGRAL

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        illuminance_integration_sensor: Entity,
        plantdevice: Entity,
    ) -> None:
        """Initialize the sensor"""
        self._plant = plantdevice
        # Store the source sensor's unique_id for tracking entity_id changes
        self._source_unique_id = illuminance_integration_sensor.unique_id

        super().__init__(
            hass,
            cron_pattern=None,
            delta_values=None,
            meter_offset=timedelta(seconds=0),
            meter_type=DAILY,
            name=READING_DLI,
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
            f"{DOMAIN_SENSOR}.{{}}", READING_DLI, current_ids={}
        )

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement.

        Override the parent class which copies the unit from the source sensor.
        The UtilityMeterSensor sets _attr_native_unit_of_measurement from the
        source sensor on every state change, so we must override the property
        to always return the correct DLI unit.
        """
        return UNIT_DLI

    @property
    def device_info(self) -> DeviceInfo:
        """Device info for devices"""
        return DeviceInfo(
            identifiers={(DOMAIN, self._plant.unique_id)},
        )

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        # Listen for entity registry updates to handle entity_id changes
        @callback
        def _handle_entity_registry_update(
            event: Event[EventEntityRegistryUpdatedData],
        ) -> None:
            """Handle entity registry updates."""
            if event.data["action"] != "update":
                return
            # Check if this is our source entity being renamed
            if "old_entity_id" not in event.data:
                return
            old_entity_id = event.data["old_entity_id"]
            new_entity_id = event.data["entity_id"]
            if old_entity_id == self._sensor_source_id:
                _LOGGER.debug(
                    "Source entity renamed from %s to %s, updating tracking",
                    old_entity_id,
                    new_entity_id,
                )
                self._update_source_entity(new_entity_id)

        self.async_on_remove(
            self.hass.bus.async_listen(
                EVENT_ENTITY_REGISTRY_UPDATED,
                _handle_entity_registry_update,
            )
        )

    @callback
    def _update_source_entity(self, new_entity_id: str) -> None:
        """Update the source entity when its entity_id changes."""
        self._sensor_source_id = new_entity_id
        # Note: The state change tracking was set up by the parent class
        # and uses the old entity_id. We need to trigger a reload to
        # properly update the tracking, or the user needs to restart HA.
        _LOGGER.info(
            "Updated source entity to %s. A restart may be required for "
            "state tracking to work correctly.",
            new_entity_id,
        )


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


class PlantDummyIlluminance(PlantDummyStatus):
    """Dummy sensor"""

    _attr_device_class = SensorDeviceClass.ILLUMINANCE

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

    async def async_update(self) -> None:
        """Give out a dummy value"""
        if datetime.now().hour < 5:
            self._attr_native_value = random.randint(1, 10) * 100
        elif datetime.now().hour < 15:
            self._attr_native_value = random.randint(20, 50) * 1000
        else:
            self._attr_native_value = random.randint(1, 10) * 100


class PlantDummyConductivity(PlantDummyStatus):
    """Dummy sensor"""

    _attr_device_class = ATTR_CONDUCTIVITY

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""
        self._attr_name = (
            f"Dummy {config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_CONDUCTIVITY}"
        )
        self._attr_unique_id = f"{config.entry_id}-dummy-conductivity"
        self._attr_icon = ICON_CONDUCTIVITY
        self._attr_native_unit_of_measurement = UnitOfConductivity.MICROSIEMENS_PER_CM
        self._attr_native_value = random.randint(40, 200) * 10

        super().__init__(hass, config, plantdevice)

    async def async_update(self) -> None:
        """Give out a dummy value"""
        self._attr_native_value = random.randint(40, 200) * 10


class PlantDummyMoisture(PlantDummyStatus):
    """Dummy sensor"""

    _attr_device_class = ATTR_MOISTURE

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


class PlantDummyTemperature(PlantDummyStatus):
    """Dummy sensor"""

    _attr_device_class = SensorDeviceClass.TEMPERATURE

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

    async def async_update(self) -> None:
        """Give out a dummy value"""
        self._attr_native_value = random.randint(15, 20)


class PlantDummyHumidity(PlantDummyStatus):
    """Dummy sensor"""

    _attr_device_class = SensorDeviceClass.HUMIDITY

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

    async def async_update(self) -> None:
        """Give out a dummy value"""
        test = random.randint(0, 100)
        if test > 50:
            self._attr_native_value = random.randint(25, 90)
