"""Support for monitoring plants."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.utility_meter.const import (
    DATA_TARIFF_SENSORS,
    DATA_UTILITY,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_PICTURE,
    ATTR_ICON,
    ATTR_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_OK,
    STATE_PROBLEM,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    Platform,
)
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.util import dt as dt_util

from . import group as group  # noqa: F401 - needed for HA group discovery
from .config_flow import update_plant_options
from .const import (
    ATTR_BRIGHTNESS,
    ATTR_CO2,
    ATTR_CONDUCTIVITY,
    ATTR_CURRENT,
    ATTR_DLI,
    ATTR_DLI_24H,
    ATTR_HUMIDITY,
    ATTR_ILLUMINANCE,
    ATTR_MAX,
    ATTR_METER_ENTITY,
    ATTR_MIN,
    ATTR_MOISTURE,
    ATTR_NEW_SENSOR,
    ATTR_PLANT,
    ATTR_SENSOR,
    ATTR_SENSORS,
    ATTR_SOIL_TEMPERATURE,
    ATTR_SPECIES,
    ATTR_TEMPERATURE,
    CONF_MAX_BRIGHTNESS,
    CONF_MAX_CONDUCTIVITY,
    CONF_MAX_MOISTURE,
    CONF_MAX_TEMPERATURE,
    CONF_MIN_BRIGHTNESS,
    CONF_MIN_CONDUCTIVITY,
    CONF_MIN_MOISTURE,
    CONF_MIN_TEMPERATURE,
    DATA_SOURCE,
    DEFAULT_MOISTURE_GRACE_PERIOD,
    DOMAIN,
    DOMAIN_PLANTBOOK,
    ENTITY_ID_PREFIX_SENSOR,
    FLOW_CO2_TRIGGER,
    FLOW_CONDUCTIVITY_TRIGGER,
    FLOW_DLI_TRIGGER,
    FLOW_HUMIDITY_TRIGGER,
    FLOW_ILLUMINANCE_TRIGGER,
    FLOW_MOISTURE_GRACE_PERIOD,
    FLOW_MOISTURE_TRIGGER,
    FLOW_PLANT_INFO,
    FLOW_SOIL_TEMPERATURE_TRIGGER,
    FLOW_TEMPERATURE_TRIGGER,
    HYSTERESIS_FRACTION,
    MOISTURE_INCREASE_THRESHOLD,
    OPB_DISPLAY_PID,
    SERVICE_REPLACE_SENSOR,
    STATE_HIGH,
    STATE_LOW,
)
from .plant_helpers import PlantHelper

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.NUMBER, Platform.SENSOR]

# Schema for native HA plant YAML configuration import
# Matches format from https://www.home-assistant.io/integrations/plant/
PLANT_SENSOR_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_MOISTURE): cv.entity_id,
        vol.Optional(ATTR_TEMPERATURE): cv.entity_id,
        vol.Optional(ATTR_CONDUCTIVITY): cv.entity_id,
        vol.Optional(ATTR_BRIGHTNESS): cv.entity_id,
        vol.Optional(ATTR_HUMIDITY): cv.entity_id,
        vol.Optional("battery"): cv.entity_id,  # Native HA has battery, we ignore it
    }
)

PLANT_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_SENSORS): PLANT_SENSOR_SCHEMA,
        vol.Optional(CONF_MIN_MOISTURE): cv.positive_int,
        vol.Optional(CONF_MAX_MOISTURE): cv.positive_int,
        vol.Optional(CONF_MIN_TEMPERATURE): vol.Coerce(float),
        vol.Optional(CONF_MAX_TEMPERATURE): vol.Coerce(float),
        vol.Optional(CONF_MIN_CONDUCTIVITY): cv.positive_int,
        vol.Optional(CONF_MAX_CONDUCTIVITY): cv.positive_int,
        vol.Optional(CONF_MIN_BRIGHTNESS): cv.positive_int,
        vol.Optional(CONF_MAX_BRIGHTNESS): cv.positive_int,
        vol.Optional("check_days"): cv.positive_int,  # Native HA option, we ignore it
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {cv.slug: vol.Any(PLANT_CONFIG_SCHEMA, None)},
        )
    },
    extra=vol.ALLOW_EXTRA,
)

SERVICE_REPLACE_SENSOR_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_METER_ENTITY): cv.entity_id,
        vol.Optional(ATTR_NEW_SENSOR): vol.Any(cv.entity_id, None, ""),
    }
)

# Use this during testing to generate some dummy-sensors
# to provide random readings for temperature, moisture etc.
#
SETUP_DUMMY_SENSORS = False
USE_DUMMY_SENSORS = False


@callback
def _async_find_matching_config_entry(hass: HomeAssistant) -> ConfigEntry | None:
    """Check if there are migrated entities"""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.source == SOURCE_IMPORT:
            return entry


async def async_migrate_plant(hass: HomeAssistant, plant_id: str, config: dict) -> None:
    """Try to migrate the config from yaml"""

    if ATTR_NAME not in config:
        config[ATTR_NAME] = plant_id.replace("_", " ").capitalize()
    plant_helper = PlantHelper(hass)
    plant_config = await plant_helper.generate_configentry(config=config)
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=plant_config
        )
    )


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the plant integration from YAML configuration.

    This function handles importing plants from the native Home Assistant
    plant integration's YAML configuration format.
    """
    if config.get(DOMAIN):
        # Only import if we haven't already imported
        config_entry = _async_find_matching_config_entry(hass)
        if not config_entry:
            _LOGGER.debug("Found YAML config: %s", config[DOMAIN])
            for plant_id in config[DOMAIN]:
                if plant_id != DOMAIN_PLANTBOOK:
                    _LOGGER.info("Importing plant from YAML: %s", plant_id)
                    await async_migrate_plant(hass, plant_id, config[DOMAIN][plant_id])
        else:
            _LOGGER.warning(
                "Plants have already been imported. "
                "Please remove the '%s:' section from configuration.yaml",
                DOMAIN,
            )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Plant from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    if FLOW_PLANT_INFO not in entry.data:
        return True

    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    _LOGGER.debug("Setting up config entry %s: %s", entry.entry_id, entry)

    plant = PlantDevice(hass, entry)
    hass.data[DOMAIN][entry.entry_id][ATTR_PLANT] = plant

    # Register update listener for options flow
    entry.async_on_unload(entry.add_update_listener(update_plant_options))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    plant_entities = [
        plant,
    ]

    # Add all the entities to Hass
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    await component.async_add_entities(plant_entities)
    hass.data[DOMAIN][entry.entry_id]["component"] = component

    # Add the entities to device registry and tie to config entry
    device_id = plant.device_id
    await _plant_add_to_device_registry(hass, plant_entities, device_id, entry)

    # Set up utility sensor
    hass.data.setdefault(DATA_UTILITY, {})
    hass.data[DATA_UTILITY].setdefault(entry.entry_id, {})
    hass.data[DATA_UTILITY][entry.entry_id].setdefault(DATA_TARIFF_SENSORS, [])
    hass.data[DATA_UTILITY][entry.entry_id][DATA_TARIFF_SENSORS].append(plant.dli)

    #
    # Service call to replace sensors
    async def replace_sensor(call: ServiceCall) -> None:
        """Replace a sensor entity within a plant device."""
        meter_entity = call.data[ATTR_METER_ENTITY]
        new_sensor = call.data.get(ATTR_NEW_SENSOR)

        # Find the meter entity across all plant config entries
        matched_meter = None
        for entry_id in hass.data[DOMAIN]:
            # Skip internal settings keys
            if entry_id.startswith("_") or entry_id.endswith("_store"):
                continue
            if ATTR_SENSORS in hass.data[DOMAIN][entry_id]:
                for sensor in hass.data[DOMAIN][entry_id][ATTR_SENSORS]:
                    if sensor.entity_id == meter_entity:
                        matched_meter = sensor
                        break
            if matched_meter:
                break
        if matched_meter is None:
            _LOGGER.warning(
                "Refuse to update non-%s entities: %s", DOMAIN, meter_entity
            )
            return False
        if (
            new_sensor
            and new_sensor != ""
            and not new_sensor.startswith(ENTITY_ID_PREFIX_SENSOR)
        ):
            _LOGGER.warning("%s is not a sensor", new_sensor)
            return False

        if new_sensor and new_sensor != "":
            try:
                test = hass.states.get(new_sensor)
            except AttributeError:
                _LOGGER.error("New sensor entity %s not found", new_sensor)
                return False
            if test is None:
                _LOGGER.error("New sensor entity %s not found", new_sensor)
                return False
        else:
            new_sensor = None

        _LOGGER.info(
            "Going to replace the external sensor for %s with %s",
            meter_entity,
            new_sensor,
        )
        matched_meter.replace_external_sensor(new_sensor)
        return

    hass.services.async_register(
        DOMAIN,
        SERVICE_REPLACE_SENSOR,
        replace_sensor,
        schema=SERVICE_REPLACE_SENSOR_SCHEMA,
    )
    websocket_api.async_register_command(hass, ws_get_info)

    if plant.hass is None:
        _LOGGER.error(
            "Plant entity %s was not added to Home Assistant "
            "(possible duplicate unique_id). Aborting setup for %s",
            plant.entity_id,
            entry.title,
        )
        return False

    plant.async_schedule_update_ha_state(True)

    # Lets add the dummy sensors automatically if we are testing stuff
    if USE_DUMMY_SENSORS is True:
        for sensor in plant.meter_entities:
            if sensor.external_sensor is None:
                await hass.services.async_call(
                    domain=DOMAIN,
                    service=SERVICE_REPLACE_SENSOR,
                    service_data={
                        "meter_entity": sensor.entity_id,
                        "new_sensor": sensor.entity_id.replace(
                            "sensor.", "sensor.dummy_"
                        ),
                    },
                    blocking=False,
                    limit=30,
                )

    return True


_REGISTRY_RETRY_DELAY = 1  # seconds between retries
_REGISTRY_MAX_RETRIES = 5


async def _plant_add_to_device_registry(
    hass: HomeAssistant,
    plant_entities: list[Entity],
    device_id: str,
    entry: ConfigEntry,
) -> None:
    """Add all related entities to the correct device and config entry."""

    # There must be a better way to do this, but I just can't find a way to set the
    # device_id when adding the entities.
    erreg = er.async_get(hass)
    for entity in plant_entities:
        registry_entry = entity.registry_entry or erreg.async_get(entity.entity_id)
        retries = 0
        while registry_entry is None and retries < _REGISTRY_MAX_RETRIES:
            retries += 1
            _LOGGER.debug(
                "Entity %s not yet in registry, retrying (%s/%s)",
                entity.entity_id,
                retries,
                _REGISTRY_MAX_RETRIES,
            )
            await asyncio.sleep(_REGISTRY_RETRY_DELAY)
            registry_entry = entity.registry_entry or erreg.async_get(entity.entity_id)

        if registry_entry is None:
            _LOGGER.warning(
                "Entity %s not found in registry after %s retries, "
                "skipping device assignment",
                entity.entity_id,
                retries,
            )
            continue

        erreg.async_update_entity(
            registry_entry.entity_id,
            device_id=device_id,
            config_entry_id=entry.entry_id,
        )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Prevent auto-disable from firing during unload teardown
    plant_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    if ATTR_PLANT in plant_data:
        plant_data[ATTR_PLANT].plant_complete = False

    # Remove the plant entity from the EntityComponent so reloads don't
    # hit a duplicate unique_id error
    plant = plant_data.get(ATTR_PLANT)
    component = plant_data.get("component")
    if component and plant and plant.entity_id:
        await component.async_remove_entity(plant.entity_id)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        hass.data[DATA_UTILITY].pop(entry.entry_id, None)
        _LOGGER.debug("Remaining domain data: %s", list(hass.data[DOMAIN].keys()))

        # Check for empty plant entries (skip settings keys)
        for entry_id in list(hass.data[DOMAIN].keys()):
            # Skip internal settings keys
            if entry_id.startswith("_") or entry_id.endswith("_store"):
                continue
            if isinstance(hass.data[DOMAIN][entry_id], dict):
                if len(hass.data[DOMAIN][entry_id]) == 0:
                    _LOGGER.debug("Removing empty entry %s", entry_id)
                    del hass.data[DOMAIN][entry_id]

        # Check if only settings keys remain (no actual plant entries)
        remaining_plant_entries = [
            k
            for k in hass.data[DOMAIN].keys()
            if not k.startswith("_") and not k.endswith("_store")
        ]
        if len(remaining_plant_entries) == 0:
            _LOGGER.debug("Removing domain %s (no more plants)", DOMAIN)
            hass.services.async_remove(DOMAIN, SERVICE_REPLACE_SENSOR)
            del hass.data[DOMAIN]
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of a config entry (permanent deletion).

    This is called when a config entry is permanently removed, not just unloaded.
    It ensures all entity and device registry entries are cleaned up properly.
    """
    _LOGGER.debug("Removing config entry %s permanently", entry.entry_id)

    # Remove all entity registry entries associated with this config entry
    ent_reg = er.async_get(hass)
    entities_to_remove = er.async_entries_for_config_entry(ent_reg, entry.entry_id)
    for entity_entry in entities_to_remove:
        _LOGGER.debug("Removing entity registry entry: %s", entity_entry.entity_id)
        ent_reg.async_remove(entity_entry.entity_id)

    # Remove device registry entry
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    if device:
        _LOGGER.debug("Removing device registry entry: %s", device.id)
        dev_reg.async_remove_device(device.id)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "plant/get_info",
        vol.Required("entity_id"): str,
    }
)
@callback
def ws_get_info(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle the websocket command."""
    if DOMAIN not in hass.data:
        connection.send_error(
            msg["id"], "domain_not_found", f"Domain {DOMAIN} not found"
        )
        return

    for key in hass.data[DOMAIN]:
        # Skip internal settings keys
        if key.startswith("_") or key.endswith("_store"):
            continue
        if ATTR_PLANT not in hass.data[DOMAIN][key]:
            continue
        plant_entity = hass.data[DOMAIN][key][ATTR_PLANT]
        if plant_entity.entity_id == msg["entity_id"]:
            try:
                connection.send_result(
                    msg["id"], {"result": plant_entity.websocket_info}
                )
            except Exception as e:
                _LOGGER.warning(
                    "Error getting plant info for %s: %s",
                    msg["entity_id"],
                    e,
                    exc_info=True,
                )
                connection.send_error(msg["id"], "plant_info_error", str(e))
            return
    connection.send_error(
        msg["id"], "entity_not_found", f"Entity {msg['entity_id']} not found"
    )
    return


class PlantDevice(Entity):
    """Base device for plants"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Initialize the Plant component."""
        self._config = config
        self.hass = hass
        self._attr_name = config.data[FLOW_PLANT_INFO][ATTR_NAME]
        self._config_entries = []
        self._data_source = config.data[FLOW_PLANT_INFO].get(DATA_SOURCE)

        # Get entity_picture from options or from initial config
        self._attr_entity_picture = self._config.options.get(
            ATTR_ENTITY_PICTURE,
            self._config.data[FLOW_PLANT_INFO].get(ATTR_ENTITY_PICTURE),
        )
        # Get species from options or from initial config
        self.species = self._config.options.get(
            ATTR_SPECIES, self._config.data[FLOW_PLANT_INFO].get(ATTR_SPECIES)
        )
        # Get display_species from options or from initial config
        # Capitalize first letter for proper binomial nomenclature (genus capitalized)
        raw_display_species = (
            self._config.options.get(
                OPB_DISPLAY_PID, self._config.data[FLOW_PLANT_INFO].get(OPB_DISPLAY_PID)
            )
            or self.species
        )
        self.display_species = (
            raw_display_species[0].upper() + raw_display_species[1:]
            if raw_display_species
            else ""
        )
        self._attr_unique_id = self._config.entry_id

        self.entity_id = async_generate_entity_id(
            f"{DOMAIN}.{{}}", self.name, current_ids={}
        )

        self.plant_complete = False
        self._device_id = None

        self._check_days = None

        self.max_moisture = None
        self.min_moisture = None
        self.max_temperature = None
        self.min_temperature = None
        self.max_conductivity = None
        self.min_conductivity = None
        self.max_illuminance = None
        self.min_illuminance = None
        self.max_humidity = None
        self.min_humidity = None
        self.max_co2 = None
        self.min_co2 = None
        self.max_soil_temperature = None
        self.min_soil_temperature = None
        self.max_dli = None
        self.min_dli = None

        self.sensor_moisture = None
        self.sensor_temperature = None
        self.sensor_conductivity = None
        self.sensor_illuminance = None
        self.sensor_humidity = None
        self.sensor_co2 = None
        self.sensor_soil_temperature = None

        self.dli = None
        self.dli_24h = None
        self.micro_dli = None
        self.ppfd = None
        self.total_integral = None
        self.lux_to_ppfd = None

        self.conductivity_status = None
        self.illuminance_status = None
        self.moisture_status = None
        self.temperature_status = None
        self.humidity_status = None
        self.co2_status = None
        self.soil_temperature_status = None
        self.dli_status = None

        # Moisture grace period tracking
        self._moisture_grace_end_time: datetime | None = None
        self._last_moisture_value: float | None = None

    def _is_ppfd_source(self) -> bool:
        """Check if illuminance source provides PPFD instead of lux.

        FYTA sensors and similar devices report light in PPFD (µmol/s⋅m²)
        instead of lux. When the source provides PPFD, the illuminance
        threshold comparison is meaningless (thresholds are in lux).
        """
        if not self.sensor_illuminance or not self.sensor_illuminance.external_sensor:
            return False
        ext_state = self.hass.states.get(self.sensor_illuminance.external_sensor)
        if not ext_state:
            return False
        unit = ext_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, "")
        return "mol" in unit.lower() if unit else False

    @property
    def entity_category(self) -> None:
        """The plant device itself does not have a category"""
        return None

    @property
    def device_class(self) -> str:
        """Return the device class for the plant entity."""
        return DOMAIN

    @property
    def device_id(self) -> str:
        """The device ID used for all the entities"""
        return self._device_id

    @property
    def device_info(self) -> DeviceInfo:
        """Device info for devices"""
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=self.name,
            model=self.display_species,
            manufacturer=self.data_source,
        )

    @property
    def illuminance_trigger(self) -> bool:
        """Whether we will generate alarms based on illuminance"""
        return self._config.options.get(FLOW_ILLUMINANCE_TRIGGER, True)

    @property
    def humidity_trigger(self) -> bool:
        """Whether we will generate alarms based on humidity"""
        return self._config.options.get(FLOW_HUMIDITY_TRIGGER, True)

    @property
    def co2_trigger(self) -> bool:
        """Whether we will generate alarms based on CO2"""
        return self._config.options.get(FLOW_CO2_TRIGGER, True)

    @property
    def soil_temperature_trigger(self) -> bool:
        """Whether we will generate alarms based on soil temperature"""
        return self._config.options.get(FLOW_SOIL_TEMPERATURE_TRIGGER, True)

    @property
    def temperature_trigger(self) -> bool:
        """Whether we will generate alarms based on temperature"""
        return self._config.options.get(FLOW_TEMPERATURE_TRIGGER, True)

    @property
    def dli_trigger(self) -> bool:
        """Whether we will generate alarms based on dli"""
        return self._config.options.get(FLOW_DLI_TRIGGER, True)

    @property
    def moisture_trigger(self) -> bool:
        """Whether we will generate alarms based on moisture"""
        return self._config.options.get(FLOW_MOISTURE_TRIGGER, True)

    @property
    def conductivity_trigger(self) -> bool:
        """Whether we will generate alarms based on conductivity"""
        return self._config.options.get(FLOW_CONDUCTIVITY_TRIGGER, True)

    @property
    def moisture_grace_period(self) -> int:
        """Grace period in seconds after watering before reporting high moisture"""
        return self._config.options.get(
            FLOW_MOISTURE_GRACE_PERIOD, DEFAULT_MOISTURE_GRACE_PERIOD
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Return the device specific state attributes."""
        if not self.plant_complete:
            # We are not fully set up, so we just return an empty dict for now
            return {}
        attributes = {
            ATTR_SPECIES: self.display_species,
            f"{ATTR_MOISTURE}_status": self.moisture_status,
            f"{ATTR_TEMPERATURE}_status": self.temperature_status,
            f"{ATTR_CONDUCTIVITY}_status": self.conductivity_status,
            f"{ATTR_ILLUMINANCE}_status": self.illuminance_status,
            f"{ATTR_HUMIDITY}_status": self.humidity_status,
            f"{ATTR_CO2}_status": self.co2_status,
            f"{ATTR_SOIL_TEMPERATURE}_status": self.soil_temperature_status,
            f"{ATTR_DLI}_status": self.dli_status,
            f"{ATTR_SPECIES}_original": self.species,
        }
        return attributes

    def _get_entity_icon(self, entity: Entity) -> str | None:
        """Get icon for entity, preferring user customization from entity registry."""
        entity_registry = er.async_get(self.hass)
        entry = entity_registry.async_get(entity.entity_id)
        if entry and entry.icon:
            return entry.icon
        return entity.icon

    def _sensor_available(self, sensor) -> bool:
        """Check if a sensor entity is available for websocket reporting."""
        if sensor is None:
            _LOGGER.debug("Sensor is None, skipping")
            return False
        try:
            has_state = self.hass.states.get(sensor.entity_id) is not None
            if not has_state:
                _LOGGER.debug(
                    "Sensor %s has no hass state (disabled or not loaded), skipping",
                    sensor.entity_id,
                )
            return has_state
        except (AttributeError, TypeError) as e:
            _LOGGER.debug("Error checking sensor availability for %s: %s", sensor, e)
            return False

    def _sensor_info(self, attr_name, sensor, max_entity, min_entity) -> dict | None:
        """Build websocket info dict for a single sensor, or None if unavailable."""
        if not self._sensor_available(sensor):
            _LOGGER.debug("Skipping %s: sensor %s not available", attr_name, sensor)
            return None
        try:
            max_val = self._safe_float(max_entity.state, max_entity.entity_id)
            min_val = self._safe_float(min_entity.state, min_entity.entity_id)
            return {
                ATTR_MAX: max_val if max_val is not None else max_entity._default_value,
                ATTR_MIN: min_val if min_val is not None else min_entity._default_value,
                ATTR_CURRENT: (
                    sensor.state if sensor.state is not None else STATE_UNAVAILABLE
                ),
                ATTR_ICON: self._get_entity_icon(sensor),
                ATTR_UNIT_OF_MEASUREMENT: sensor.unit_of_measurement,
                ATTR_SENSOR: sensor.entity_id,
            }
        except (AttributeError, TypeError) as e:
            _LOGGER.warning(
                "Error building websocket info for %s (sensor=%s, max=%s, min=%s): %s",
                attr_name,
                sensor,
                max_entity,
                min_entity,
                e,
            )
            return None

    @property
    def websocket_info(self) -> dict:
        """Websocket response"""
        if not self.plant_complete:
            # We are not fully set up, so we just return an empty dict for now
            return {}

        sensor_map = [
            (
                ATTR_TEMPERATURE,
                self.sensor_temperature,
                self.max_temperature,
                self.min_temperature,
            ),
            (
                ATTR_ILLUMINANCE,
                self.sensor_illuminance,
                self.max_illuminance,
                self.min_illuminance,
            ),
            (ATTR_MOISTURE, self.sensor_moisture, self.max_moisture, self.min_moisture),
            (
                ATTR_CONDUCTIVITY,
                self.sensor_conductivity,
                self.max_conductivity,
                self.min_conductivity,
            ),
            (ATTR_HUMIDITY, self.sensor_humidity, self.max_humidity, self.min_humidity),
            (ATTR_CO2, self.sensor_co2, self.max_co2, self.min_co2),
            (
                ATTR_SOIL_TEMPERATURE,
                self.sensor_soil_temperature,
                self.max_soil_temperature,
                self.min_soil_temperature,
            ),
        ]

        response = {}
        for attr_name, sensor, max_entity, min_entity in sensor_map:
            info = self._sensor_info(attr_name, sensor, max_entity, min_entity)
            if info is not None:
                response[attr_name] = info

        # DLI uses its own entity (not a meter sensor)
        if self._sensor_available(self.dli):
            response[ATTR_DLI] = {
                ATTR_MAX: self.max_dli.state,
                ATTR_MIN: self.min_dli.state,
                ATTR_CURRENT: STATE_UNAVAILABLE,
                ATTR_ICON: self._get_entity_icon(self.dli),
                ATTR_UNIT_OF_MEASUREMENT: self.dli.unit_of_measurement,
                ATTR_SENSOR: self.dli.entity_id,
            }
            dli_val = self._safe_float(self.dli.native_value, self.dli.entity_id)
            if dli_val is not None:
                response[ATTR_DLI][ATTR_CURRENT] = dli_val

        # Add rolling 24h DLI if available
        if self.dli_24h is not None and self._sensor_available(self.dli_24h):
            response[ATTR_DLI_24H] = {
                ATTR_MAX: self.max_dli.state,  # Same thresholds as regular DLI
                ATTR_MIN: self.min_dli.state,
                ATTR_CURRENT: STATE_UNAVAILABLE,
                ATTR_ICON: self._get_entity_icon(self.dli_24h),
                ATTR_UNIT_OF_MEASUREMENT: self.dli_24h.unit_of_measurement,
                ATTR_SENSOR: self.dli_24h.entity_id,
            }
            dli_24h_val = self._safe_float(
                self.dli_24h.native_value, self.dli_24h.entity_id
            )
            if dli_24h_val is not None:
                response[ATTR_DLI_24H][ATTR_CURRENT] = dli_24h_val

        return response

    @property
    def threshold_entities(self) -> list[Entity]:
        """List all threshold entities"""
        return [
            self.max_co2,
            self.max_conductivity,
            self.max_dli,
            self.max_humidity,
            self.max_illuminance,
            self.max_moisture,
            self.max_soil_temperature,
            self.max_temperature,
            self.min_co2,
            self.min_conductivity,
            self.min_dli,
            self.min_humidity,
            self.min_illuminance,
            self.min_moisture,
            self.min_soil_temperature,
            self.min_temperature,
        ]

    @property
    def meter_entities(self) -> list[Entity]:
        """List all meter (sensor) entities"""
        return [
            self.sensor_co2,
            self.sensor_conductivity,
            self.sensor_humidity,
            self.sensor_illuminance,
            self.sensor_moisture,
            self.sensor_soil_temperature,
            self.sensor_temperature,
        ]

    @property
    def integral_entities(self) -> list[Entity]:
        """List all integral entities"""
        return [
            self.dli,
            self.ppfd,
            self.total_integral,
        ]

    def add_image(self, image_url: str | None) -> None:
        """Set new entity_picture."""
        self._attr_entity_picture = image_url
        options = self._config.options.copy()
        options[ATTR_ENTITY_PICTURE] = image_url
        self.hass.config_entries.async_update_entry(self._config, options=options)

    def add_species(self, species: Entity | None) -> None:
        """Set new species"""
        self.species = species

    def add_thresholds(
        self,
        max_moisture: Entity | None,
        min_moisture: Entity | None,
        max_temperature: Entity | None,
        min_temperature: Entity | None,
        max_conductivity: Entity | None,
        min_conductivity: Entity | None,
        max_illuminance: Entity | None,
        min_illuminance: Entity | None,
        max_humidity: Entity | None,
        min_humidity: Entity | None,
        max_co2: Entity | None,
        min_co2: Entity | None,
        max_soil_temperature: Entity | None,
        min_soil_temperature: Entity | None,
        max_dli: Entity | None,
        min_dli: Entity | None,
    ) -> None:
        """Add the threshold entities"""
        self.max_moisture = max_moisture
        self.min_moisture = min_moisture
        self.max_temperature = max_temperature
        self.min_temperature = min_temperature
        self.max_conductivity = max_conductivity
        self.min_conductivity = min_conductivity
        self.max_illuminance = max_illuminance
        self.min_illuminance = min_illuminance
        self.max_humidity = max_humidity
        self.min_humidity = min_humidity
        self.max_co2 = max_co2
        self.min_co2 = min_co2
        self.max_soil_temperature = max_soil_temperature
        self.min_soil_temperature = min_soil_temperature
        self.max_dli = max_dli
        self.min_dli = min_dli

    def add_sensors(
        self,
        moisture: Entity | None,
        temperature: Entity | None,
        conductivity: Entity | None,
        illuminance: Entity | None,
        humidity: Entity | None,
        co2: Entity | None,
        soil_temperature: Entity | None,
    ) -> None:
        """Add the sensor entities"""
        self.sensor_moisture = moisture
        self.sensor_temperature = temperature
        self.sensor_conductivity = conductivity
        self.sensor_illuminance = illuminance
        self.sensor_humidity = humidity
        self.sensor_co2 = co2
        self.sensor_soil_temperature = soil_temperature

    def add_dli(
        self,
        dli: Entity | None,
        dli_24h: Entity | None = None,
    ) -> None:
        """Add the DLI-utility sensors"""
        self.dli = dli
        self.dli_24h = dli_24h
        self.plant_complete = True

    def add_calculations(self, ppfd: Entity, total_integral: Entity) -> None:
        """Add the intermediate calculation entities"""
        self.ppfd = ppfd
        self.total_integral = total_integral

    def add_lux_to_ppfd(self, lux_to_ppfd: Entity) -> None:
        """Add the lux to PPFD conversion factor entity"""
        self.lux_to_ppfd = lux_to_ppfd

    def _get_related_entities_for_sensor(self, meter_sensor) -> list:
        """Return the meter sensor and its related threshold/derived entities."""
        if meter_sensor is self.sensor_moisture:
            return [self.sensor_moisture, self.max_moisture, self.min_moisture]
        if meter_sensor is self.sensor_temperature:
            return [self.sensor_temperature, self.max_temperature, self.min_temperature]
        if meter_sensor is self.sensor_conductivity:
            return [
                self.sensor_conductivity,
                self.max_conductivity,
                self.min_conductivity,
            ]
        if meter_sensor is self.sensor_humidity:
            return [self.sensor_humidity, self.max_humidity, self.min_humidity]
        if meter_sensor is self.sensor_co2:
            return [self.sensor_co2, self.max_co2, self.min_co2]
        if meter_sensor is self.sensor_soil_temperature:
            return [
                self.sensor_soil_temperature,
                self.max_soil_temperature,
                self.min_soil_temperature,
            ]
        if meter_sensor is self.sensor_illuminance:
            return [
                self.sensor_illuminance,
                self.max_illuminance,
                self.min_illuminance,
                self.max_dli,
                self.min_dli,
                self.lux_to_ppfd,
                self.ppfd,
                self.total_integral,
                self.dli,
                self.dli_24h,
            ]
        return []

    def update_entity_disabled_state(self, meter_sensor) -> None:
        """Disable or enable entities based on whether an external sensor is configured."""
        ent_reg = er.async_get(self.hass)
        has_sensor = meter_sensor.external_sensor is not None
        _LOGGER.debug(
            "update_entity_disabled_state: meter=%s, has_sensor=%s, external=%s",
            meter_sensor.entity_id,
            has_sensor,
            meter_sensor.external_sensor,
        )
        for entity in self._get_related_entities_for_sensor(meter_sensor):
            if entity is None:
                continue
            entry = ent_reg.async_get(entity.entity_id)
            if entry is None:
                _LOGGER.warning(
                    "Entity %s not found in registry, skipping disable/enable",
                    entity.entity_id,
                )
                continue
            if has_sensor:
                if entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
                    _LOGGER.debug(
                        "Enabling %s (was disabled by integration)",
                        entry.entity_id,
                    )
                    ent_reg.async_update_entity(entry.entity_id, disabled_by=None)
                elif entry.disabled_by is not None:
                    _LOGGER.warning(
                        "Entity %s is disabled by %s (not by integration), "
                        "cannot auto-enable — please enable manually via the UI",
                        entry.entity_id,
                        entry.disabled_by,
                    )
            else:
                if entry.disabled_by is None:
                    ent_reg.async_update_entity(
                        entry.entity_id,
                        disabled_by=er.RegistryEntryDisabler.INTEGRATION,
                    )

    @staticmethod
    def _safe_float(value, entity_id: str) -> float | None:
        """Convert a sensor value to float, returning None on failure."""
        try:
            return float(value)
        except (ValueError, TypeError):
            _LOGGER.debug("Sensor %s has non-numeric value: %s", entity_id, value)
            return None

    def _check_threshold(self, value, min_entity, max_entity, current_status):
        """Check a value against min/max thresholds with hysteresis.

        Returns STATE_LOW, STATE_HIGH, or STATE_OK.
        When already in a problem state, require the value to cross back
        by a margin (hysteresis band) before clearing.
        """
        try:
            min_val = float(min_entity.state)
            max_val = float(max_entity.state)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Threshold entity has non-numeric state "
                "(min=%s [%s], max=%s [%s]) — skipping check",
                min_entity.entity_id,
                min_entity.state,
                max_entity.entity_id,
                max_entity.state,
            )
            return current_status
        band = (max_val - min_val) * HYSTERESIS_FRACTION

        if value < min_val:
            new_status = STATE_LOW
        elif value > max_val:
            new_status = STATE_HIGH
        elif current_status == STATE_LOW and value <= min_val + band:
            new_status = STATE_LOW
        elif current_status == STATE_HIGH and value >= max_val - band:
            new_status = STATE_HIGH
        else:
            new_status = STATE_OK

        if new_status != current_status:
            _LOGGER.debug(
                "Threshold %s/%s: value=%.1f, range=[%.1f, %.1f], " "status %s -> %s",
                min_entity.entity_id,
                max_entity.entity_id,
                value,
                min_val,
                max_val,
                current_status,
                new_status,
            )
        return new_status

    def update(self) -> None:
        """Run on every update of the entities"""

        new_state = STATE_OK
        known_state = False

        if self.sensor_moisture is not None:
            moisture = getattr(
                self.hass.states.get(self.sensor_moisture.entity_id), "state", None
            )
            moisture_val = self._safe_float(moisture, self.sensor_moisture.entity_id)
            if moisture_val is not None:
                known_state = True

                # Detect watering event (rapid moisture increase)
                if self._last_moisture_value is not None:
                    moisture_increase = moisture_val - self._last_moisture_value
                    if moisture_increase >= MOISTURE_INCREASE_THRESHOLD:
                        grace_period_seconds = self.moisture_grace_period
                        if grace_period_seconds > 0:
                            self._moisture_grace_end_time = dt_util.now() + timedelta(
                                seconds=grace_period_seconds
                            )
                            _LOGGER.debug(
                                "Watering detected for %s: moisture increased by %.1f%% "
                                "(from %.1f%% to %.1f%%). Grace period active until %s",
                                self.entity_id,
                                moisture_increase,
                                self._last_moisture_value,
                                moisture_val,
                                self._moisture_grace_end_time,
                            )

                self._last_moisture_value = moisture_val

                self.moisture_status = self._check_threshold(
                    moisture_val,
                    self.min_moisture,
                    self.max_moisture,
                    self.moisture_status,
                )

                # Apply grace period logic: only suppress "high" problems during grace period
                # Allow "low" problems (needs water) to trigger immediately
                if self.moisture_trigger:
                    if self.moisture_status == STATE_LOW:
                        new_state = STATE_PROBLEM
                    elif self.moisture_status == STATE_HIGH:
                        now = dt_util.now()
                        if (
                            self._moisture_grace_end_time is not None
                            and now < self._moisture_grace_end_time
                        ):
                            # Grace period active - suppress high moisture problem
                            remaining = (
                                self._moisture_grace_end_time - now
                            ).total_seconds()
                            _LOGGER.debug(
                                "Moisture high for %s but grace period active "
                                "(%.0f seconds remaining) - not reporting problem",
                                self.entity_id,
                                remaining,
                            )
                        else:
                            # Grace period expired or not active - report problem
                            new_state = STATE_PROBLEM
                            if self._moisture_grace_end_time is not None:
                                _LOGGER.debug(
                                    "Moisture grace period expired for %s - "
                                    "reporting high moisture problem",
                                    self.entity_id,
                                )
                                self._moisture_grace_end_time = None
            else:
                # Reset status and tracking when sensor is unavailable or non-numeric
                self.moisture_status = None
                self._last_moisture_value = None
                self._moisture_grace_end_time = None
        else:
            # Reset status and tracking when sensor is removed
            self.moisture_status = None
            self._last_moisture_value = None
            self._moisture_grace_end_time = None

        if self.sensor_conductivity is not None:
            conductivity = getattr(
                self.hass.states.get(self.sensor_conductivity.entity_id), "state", None
            )
            conductivity_val = self._safe_float(
                conductivity, self.sensor_conductivity.entity_id
            )
            if conductivity_val is not None:
                known_state = True
                self.conductivity_status = self._check_threshold(
                    conductivity_val,
                    self.min_conductivity,
                    self.max_conductivity,
                    self.conductivity_status,
                )
                if (
                    self.conductivity_status in (STATE_LOW, STATE_HIGH)
                    and self.conductivity_trigger
                ):
                    new_state = STATE_PROBLEM
            else:
                # Reset status when sensor is unavailable or non-numeric
                self.conductivity_status = None
        else:
            # Reset status when sensor is removed
            self.conductivity_status = None

        if self.sensor_temperature is not None:
            temperature = getattr(
                self.hass.states.get(self.sensor_temperature.entity_id), "state", None
            )
            temperature_val = self._safe_float(
                temperature, self.sensor_temperature.entity_id
            )
            if temperature_val is not None:
                known_state = True
                self.temperature_status = self._check_threshold(
                    temperature_val,
                    self.min_temperature,
                    self.max_temperature,
                    self.temperature_status,
                )
                if (
                    self.temperature_status in (STATE_LOW, STATE_HIGH)
                    and self.temperature_trigger
                ):
                    new_state = STATE_PROBLEM
            else:
                # Reset status when sensor is unavailable or non-numeric
                self.temperature_status = None
        else:
            # Reset status when sensor is removed
            self.temperature_status = None

        if self.sensor_humidity is not None:
            humidity = getattr(
                self.hass.states.get(self.sensor_humidity.entity_id), "state", None
            )
            humidity_val = self._safe_float(humidity, self.sensor_humidity.entity_id)
            if humidity_val is not None:
                known_state = True
                self.humidity_status = self._check_threshold(
                    humidity_val,
                    self.min_humidity,
                    self.max_humidity,
                    self.humidity_status,
                )
                if (
                    self.humidity_status in (STATE_LOW, STATE_HIGH)
                    and self.humidity_trigger
                ):
                    new_state = STATE_PROBLEM
            else:
                # Reset status when sensor is unavailable or non-numeric
                self.humidity_status = None
        else:
            # Reset status when sensor is removed
            self.humidity_status = None

        if self.sensor_co2 is not None:
            co2 = getattr(
                self.hass.states.get(self.sensor_co2.entity_id), "state", None
            )
            co2_val = self._safe_float(co2, self.sensor_co2.entity_id)
            if co2_val is not None:
                known_state = True
                self.co2_status = self._check_threshold(
                    co2_val, self.min_co2, self.max_co2, self.co2_status
                )
                if self.co2_status in (STATE_LOW, STATE_HIGH) and self.co2_trigger:
                    new_state = STATE_PROBLEM
            else:
                # Reset status when sensor is unavailable or non-numeric
                self.co2_status = None
        else:
            # Reset status when sensor is removed
            self.co2_status = None

        if self.sensor_soil_temperature is not None:
            soil_temp = getattr(
                self.hass.states.get(self.sensor_soil_temperature.entity_id),
                "state",
                None,
            )
            soil_temp_val = self._safe_float(
                soil_temp, self.sensor_soil_temperature.entity_id
            )
            if soil_temp_val is not None:
                known_state = True
                self.soil_temperature_status = self._check_threshold(
                    soil_temp_val,
                    self.min_soil_temperature,
                    self.max_soil_temperature,
                    self.soil_temperature_status,
                )
                if (
                    self.soil_temperature_status in (STATE_LOW, STATE_HIGH)
                    and self.soil_temperature_trigger
                ):
                    new_state = STATE_PROBLEM
            else:
                # Reset status when sensor is unavailable or non-numeric
                self.soil_temperature_status = None
        else:
            # Reset status when sensor is removed
            self.soil_temperature_status = None

        # Check the instant values for illuminance against "max"
        # Ignoring "min" value for illuminance as it would probably trigger every night
        # Skip if source provides PPFD (thresholds are in lux, not PPFD)
        if self.sensor_illuminance is not None:
            # Check if source is PPFD - skip threshold check if so
            if self._is_ppfd_source():
                # PPFD source - skip threshold check (thresholds are in lux)
                # DLI problem detection still works
                self.illuminance_status = None
            else:
                illuminance = getattr(
                    self.hass.states.get(self.sensor_illuminance.entity_id),
                    "state",
                    None,
                )
                illuminance_val = self._safe_float(
                    illuminance, self.sensor_illuminance.entity_id
                )
                if illuminance_val is not None:
                    known_state = True
                    self.illuminance_status = self._check_threshold(
                        illuminance_val,
                        self.min_illuminance,
                        self.max_illuminance,
                        self.illuminance_status,
                    )
                    if (
                        self.illuminance_status == STATE_HIGH
                        and self.illuminance_trigger
                    ):
                        new_state = STATE_PROBLEM
                else:
                    # Reset status when sensor is unavailable or non-numeric
                    self.illuminance_status = None
        else:
            # Reset status when sensor is removed
            self.illuminance_status = None

        # - Checking Low values would create "problem" every night...
        # Check DLI from the previous day against max/min DLI
        if (
            self.dli is not None
            and self.dli.native_value is not None
            and self.dli.native_value != STATE_UNKNOWN
            and self.dli.native_value != STATE_UNAVAILABLE
        ):
            known_state = True
            try:
                dli_value = float(self.dli.extra_state_attributes.get("last_period", 0))
            except (ValueError, TypeError):
                _LOGGER.debug(
                    "DLI last_period has non-numeric value: %s",
                    self.dli.extra_state_attributes.get("last_period"),
                )
                dli_value = 0
            if dli_value > 0:
                self.dli_status = self._check_threshold(
                    dli_value, self.min_dli, self.max_dli, self.dli_status
                )
            else:
                self.dli_status = STATE_OK
            if self.dli_status in (STATE_LOW, STATE_HIGH) and self.dli_trigger:
                new_state = STATE_PROBLEM
        else:
            # Reset DLI status when sensor is unavailable or removed
            self.dli_status = None

        if not known_state:
            new_state = STATE_UNKNOWN

        if new_state != self._attr_state:
            _LOGGER.debug(
                "Plant %s state changed: %s -> %s",
                self.entity_id,
                self._attr_state,
                new_state,
            )
        self._attr_state = new_state
        self.update_registry()

    @property
    def data_source(self) -> str | None:
        """Currently unused. For future use"""
        return None

    def update_registry(self) -> None:
        """Update registry with correct data"""
        # Is there a better way to add an entity to the device registry?

        device_registry = dr.async_get(self.hass)
        device_registry.async_get_or_create(
            config_entry_id=self._config.entry_id,
            identifiers={(DOMAIN, self.unique_id)},
            name=self.name,
            model=self.display_species,
            manufacturer=self.data_source,
        )
        if self._device_id is None:
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, self.unique_id)}
            )
            self._device_id = device.id

    async def async_added_to_hass(self) -> None:
        self.update_registry()
