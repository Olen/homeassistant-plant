"""Support for monitoring plants."""

from __future__ import annotations

import logging

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
    DOMAIN,
    DOMAIN_PLANTBOOK,
    ENTITY_ID_PREFIX_SENSOR,
    FLOW_CO2_TRIGGER,
    FLOW_CONDUCTIVITY_TRIGGER,
    FLOW_DLI_TRIGGER,
    FLOW_HUMIDITY_TRIGGER,
    FLOW_ILLUMINANCE_TRIGGER,
    FLOW_MOISTURE_TRIGGER,
    FLOW_PLANT_INFO,
    FLOW_SOIL_TEMPERATURE_TRIGGER,
    FLOW_TEMPERATURE_TRIGGER,
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

    # Add the entities to device registry together with plant
    device_id = plant.device_id
    await _plant_add_to_device_registry(hass, plant_entities, device_id)

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
        found = False
        for entry_id in hass.data[DOMAIN]:
            # Skip internal settings keys
            if entry_id.startswith("_") or entry_id.endswith("_store"):
                continue
            if ATTR_SENSORS in hass.data[DOMAIN][entry_id]:
                for sensor in hass.data[DOMAIN][entry_id][ATTR_SENSORS]:
                    if sensor.entity_id == meter_entity:
                        found = True
                        break
        if not found:
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

        try:
            meter = hass.states.get(meter_entity)
        except AttributeError:
            _LOGGER.error("Meter entity %s not found", meter_entity)
            return False
        if meter is None:
            _LOGGER.error("Meter entity %s not found", meter_entity)
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
        for key in hass.data[DOMAIN]:
            # Skip internal settings keys
            if key.startswith("_") or key.endswith("_store"):
                continue
            if ATTR_SENSORS in hass.data[DOMAIN][key]:
                meters = hass.data[DOMAIN][key][ATTR_SENSORS]
                for meter in meters:
                    if meter.entity_id == meter_entity:
                        meter.replace_external_sensor(new_sensor)
        return

    hass.services.async_register(
        DOMAIN,
        SERVICE_REPLACE_SENSOR,
        replace_sensor,
        schema=SERVICE_REPLACE_SENSOR_SCHEMA,
    )
    websocket_api.async_register_command(hass, ws_get_info)
    plant.async_schedule_update_ha_state(True)

    # Disable entities that have no external sensor configured
    for meter_sensor in plant.meter_entities:
        plant.update_entity_disabled_state(meter_sensor)

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


async def _plant_add_to_device_registry(
    hass: HomeAssistant, plant_entities: list[Entity], device_id: str
) -> None:
    """Add all related entities to the correct device_id"""

    # There must be a better way to do this, but I just can't find a way to set the
    # device_id when adding the entities.
    erreg = er.async_get(hass)
    for entity in plant_entities:
        erreg.async_update_entity(entity.registry_entry.entity_id, device_id=device_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Prevent auto-disable from firing during unload teardown
    plant_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    if ATTR_PLANT in plant_data:
        plant_data[ATTR_PLANT].plant_complete = False

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
                connection.send_error(
                    msg["id"], "plant_info_error", str(e)
                )
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
            _LOGGER.debug(
                "Error checking sensor availability for %s: %s", sensor, e
            )
            return False

    def _sensor_info(self, attr_name, sensor, max_entity, min_entity) -> dict | None:
        """Build websocket info dict for a single sensor, or None if unavailable."""
        if not self._sensor_available(sensor):
            _LOGGER.debug(
                "Skipping %s: sensor %s not available", attr_name, sensor
            )
            return None
        try:
            return {
                ATTR_MAX: max_entity.state,
                ATTR_MIN: min_entity.state,
                ATTR_CURRENT: sensor.state or STATE_UNAVAILABLE,
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
            (ATTR_TEMPERATURE, self.sensor_temperature, self.max_temperature, self.min_temperature),
            (ATTR_ILLUMINANCE, self.sensor_illuminance, self.max_illuminance, self.min_illuminance),
            (ATTR_MOISTURE, self.sensor_moisture, self.max_moisture, self.min_moisture),
            (ATTR_CONDUCTIVITY, self.sensor_conductivity, self.max_conductivity, self.min_conductivity),
            (ATTR_HUMIDITY, self.sensor_humidity, self.max_humidity, self.min_humidity),
            (ATTR_CO2, self.sensor_co2, self.max_co2, self.min_co2),
            (ATTR_SOIL_TEMPERATURE, self.sensor_soil_temperature, self.max_soil_temperature, self.min_soil_temperature),
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
            if self.dli.native_value is not None and self.dli.native_value != STATE_UNKNOWN:
                response[ATTR_DLI][ATTR_CURRENT] = float(self.dli.native_value)

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
            if (
                self.dli_24h.native_value is not None
                and self.dli_24h.native_value != STATE_UNKNOWN
            ):
                response[ATTR_DLI_24H][ATTR_CURRENT] = float(self.dli_24h.native_value)

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
        for entity in self._get_related_entities_for_sensor(meter_sensor):
            if entity is None:
                continue
            entry = ent_reg.async_get(entity.entity_id)
            if entry is None:
                continue
            if has_sensor:
                if entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
                    ent_reg.async_update_entity(entry.entity_id, disabled_by=None)
            else:
                if entry.disabled_by is None:
                    ent_reg.async_update_entity(
                        entry.entity_id,
                        disabled_by=er.RegistryEntryDisabler.INTEGRATION,
                    )

    def update(self) -> None:
        """Run on every update of the entities"""

        new_state = STATE_OK
        known_state = False

        if self.sensor_moisture is not None:
            moisture = getattr(
                self.hass.states.get(self.sensor_moisture.entity_id), "state", None
            )
            if (
                moisture is not None
                and moisture != STATE_UNKNOWN
                and moisture != STATE_UNAVAILABLE
            ):
                known_state = True
                if float(moisture) < float(self.min_moisture.state):
                    self.moisture_status = STATE_LOW
                    if self.moisture_trigger:
                        new_state = STATE_PROBLEM
                elif float(moisture) > float(self.max_moisture.state):
                    self.moisture_status = STATE_HIGH
                    if self.moisture_trigger:
                        new_state = STATE_PROBLEM
                else:
                    self.moisture_status = STATE_OK
            else:
                # Reset status when sensor is unavailable
                self.moisture_status = None
        else:
            # Reset status when sensor is removed
            self.moisture_status = None

        if self.sensor_conductivity is not None:
            conductivity = getattr(
                self.hass.states.get(self.sensor_conductivity.entity_id), "state", None
            )
            if (
                conductivity is not None
                and conductivity != STATE_UNKNOWN
                and conductivity != STATE_UNAVAILABLE
            ):
                known_state = True
                if float(conductivity) < float(self.min_conductivity.state):
                    self.conductivity_status = STATE_LOW
                    if self.conductivity_trigger:
                        new_state = STATE_PROBLEM
                elif float(conductivity) > float(self.max_conductivity.state):
                    self.conductivity_status = STATE_HIGH
                    if self.conductivity_trigger:
                        new_state = STATE_PROBLEM
                else:
                    self.conductivity_status = STATE_OK
            else:
                # Reset status when sensor is unavailable
                self.conductivity_status = None
        else:
            # Reset status when sensor is removed
            self.conductivity_status = None

        if self.sensor_temperature is not None:
            temperature = getattr(
                self.hass.states.get(self.sensor_temperature.entity_id), "state", None
            )
            if (
                temperature is not None
                and temperature != STATE_UNKNOWN
                and temperature != STATE_UNAVAILABLE
            ):
                known_state = True
                if float(temperature) < float(self.min_temperature.state):
                    self.temperature_status = STATE_LOW
                    if self.temperature_trigger:
                        new_state = STATE_PROBLEM
                elif float(temperature) > float(self.max_temperature.state):
                    self.temperature_status = STATE_HIGH
                    if self.temperature_trigger:
                        new_state = STATE_PROBLEM
                else:
                    self.temperature_status = STATE_OK
            else:
                # Reset status when sensor is unavailable
                self.temperature_status = None
        else:
            # Reset status when sensor is removed
            self.temperature_status = None

        if self.sensor_humidity is not None:
            humidity = getattr(
                self.hass.states.get(self.sensor_humidity.entity_id), "state", None
            )
            if (
                humidity is not None
                and humidity != STATE_UNKNOWN
                and humidity != STATE_UNAVAILABLE
            ):
                known_state = True
                if float(humidity) < float(self.min_humidity.state):
                    self.humidity_status = STATE_LOW
                    if self.humidity_trigger:
                        new_state = STATE_PROBLEM
                elif float(humidity) > float(self.max_humidity.state):
                    self.humidity_status = STATE_HIGH
                    if self.humidity_trigger:
                        new_state = STATE_PROBLEM
                else:
                    self.humidity_status = STATE_OK
            else:
                # Reset status when sensor is unavailable
                self.humidity_status = None
        else:
            # Reset status when sensor is removed
            self.humidity_status = None

        if self.sensor_co2 is not None:
            co2 = getattr(
                self.hass.states.get(self.sensor_co2.entity_id), "state", None
            )
            if co2 is not None and co2 != STATE_UNKNOWN and co2 != STATE_UNAVAILABLE:
                known_state = True
                if float(co2) < float(self.min_co2.state):
                    self.co2_status = STATE_LOW
                    if self.co2_trigger:
                        new_state = STATE_PROBLEM
                elif float(co2) > float(self.max_co2.state):
                    self.co2_status = STATE_HIGH
                    if self.co2_trigger:
                        new_state = STATE_PROBLEM
                else:
                    self.co2_status = STATE_OK
            else:
                # Reset status when sensor is unavailable
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
            if (
                soil_temp is not None
                and soil_temp != STATE_UNKNOWN
                and soil_temp != STATE_UNAVAILABLE
            ):
                known_state = True
                if float(soil_temp) < float(self.min_soil_temperature.state):
                    self.soil_temperature_status = STATE_LOW
                    if self.soil_temperature_trigger:
                        new_state = STATE_PROBLEM
                elif float(soil_temp) > float(self.max_soil_temperature.state):
                    self.soil_temperature_status = STATE_HIGH
                    if self.soil_temperature_trigger:
                        new_state = STATE_PROBLEM
                else:
                    self.soil_temperature_status = STATE_OK
            else:
                # Reset status when sensor is unavailable
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
                if (
                    illuminance is not None
                    and illuminance != STATE_UNKNOWN
                    and illuminance != STATE_UNAVAILABLE
                ):
                    known_state = True
                    if float(illuminance) > float(self.max_illuminance.state):
                        self.illuminance_status = STATE_HIGH
                        if self.illuminance_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.illuminance_status = STATE_OK
                else:
                    # Reset status when sensor is unavailable
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
            if float(self.dli.extra_state_attributes["last_period"]) > 0 and float(
                self.dli.extra_state_attributes["last_period"]
            ) < float(self.min_dli.state):
                self.dli_status = STATE_LOW
                if self.dli_trigger:
                    new_state = STATE_PROBLEM
            elif float(self.dli.extra_state_attributes["last_period"]) > 0 and float(
                self.dli.extra_state_attributes["last_period"]
            ) > float(self.max_dli.state):
                self.dli_status = STATE_HIGH
                if self.dli_trigger:
                    new_state = STATE_PROBLEM
            else:
                self.dli_status = STATE_OK
        else:
            # Reset DLI status when sensor is unavailable or removed
            self.dli_status = None

        if not known_state:
            new_state = STATE_UNKNOWN

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
