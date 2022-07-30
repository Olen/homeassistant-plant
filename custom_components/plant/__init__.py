"""Support for monitoring plants."""
from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from contextlib import suppress
import copy
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from types import MethodDescriptorType
from typing import Any

import voluptuous as vol

from homeassistant.components.integration.const import METHOD_TRAPEZOIDAL
from homeassistant.components.integration.sensor import (
    UNIT_PREFIXES,
    UNIT_TIME,
    IntegrationSensor,
)
from homeassistant.components.recorder import get_instance, history
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.components.utility_meter.const import (
    DAILY,
    DATA_TARIFF_SENSORS,
    DATA_UTILITY,
)
from homeassistant.components.utility_meter.sensor import (
    PERIOD2CRON,
    UtilityMeterSensor,
)
from homeassistant.config_entries import ConfigEntries, ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_ENTITY_PICTURE,
    ATTR_NAME,
    ATTR_TEMPERATURE,
    ATTR_UNIT_OF_MEASUREMENT,
    CONDUCTIVITY,
    CONF_NAME,
    CONF_SENSORS,
    LIGHT_LUX,
    PERCENTAGE,
    STATE_OK,
    STATE_PROBLEM,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    TIME_DAYS,
    TIME_HOURS,
    TIME_SECONDS,
    URL_API_TEMPLATE,
)
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.config_validation import path as valid_path, url as valid_url
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import (
    Entity,
    EntityCategory,
    async_generate_entity_id,
    entity_sources,
)
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.temperature import display_temp
from homeassistant.util import dt as dt_util
from homeassistant.util.temperature import convert as convert_temperature

from .const import (
    ATTR_MAX,
    ATTR_METERS,
    ATTR_MIN,
    ATTR_THRESHOLDS,
    CONF_CHECK_DAYS,
    CONF_IMAGE,
    CONF_MAX_CONDUCTIVITY,
    CONF_MAX_HUMIDITY,
    CONF_MAX_ILLUMINANCE,
    CONF_MAX_MMOL,
    CONF_MAX_MOISTURE,
    CONF_MAX_MOL,
    CONF_MAX_TEMPERATURE,
    CONF_MIN_BATTERY_LEVEL,
    CONF_MIN_CONDUCTIVITY,
    CONF_MIN_HUMIDITY,
    CONF_MIN_ILLUMINANCE,
    CONF_MIN_MMOL,
    CONF_MIN_MOISTURE,
    CONF_MIN_MOL,
    CONF_MIN_TEMPERATURE,
    CONF_PLANTBOOK,
    CONF_PLANTBOOK_MAPPING,
    CONF_SPECIES,
    DOMAIN,
    FLOW_ILLUMINANCE_TRIGGER,
    FLOW_PLANT_IMAGE,
    FLOW_PLANT_INFO,
    FLOW_PLANT_LIMITS,
    FLOW_PLANT_NAME,
    FLOW_PLANT_SPECIES,
    FLOW_SENSOR_CONDUCTIVITY,
    FLOW_SENSOR_HUMIDITY,
    FLOW_SENSOR_ILLUMINANCE,
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_TEMPERATURE,
    OPB_DISPLAY_PID,
    OPB_PID,
    PPFD_DLI_FACTOR,
    READING_BATTERY,
    READING_CONDUCTIVITY,
    READING_DLI,
    READING_HUMIDITY,
    READING_ILLUMINANCE,
    READING_MMOL,
    READING_MOISTURE,
    READING_MOL,
    READING_TEMPERATURE,
    UNIT_CONDUCTIVITY,
    UNIT_DLI,
    UNIT_MICRO_DLI,
    UNIT_MICRO_PPFD,
    UNIT_PPFD,
)

CONF_SCALE_TEMPERATURE = "temp_scale"
_LOGGER = logging.getLogger(__name__)

DATA_UPDATED = "plant_data_updated"


DEFAULT_NAME = "plant"

ATTR_PROBLEM = "problem"
ATTR_SENSORS = "sensors"
PROBLEM_NONE = "none"
ATTR_MAX_ILLUMINANCE_HISTORY = "max_illuminance"
ATTR_SPECIES = "species"
ATTR_LIMITS = FLOW_PLANT_LIMITS
ATTR_IMAGE = "image"
ATTR_EXTERNAL_SENSOR = "external_sensor"

SERVICE_REPLACE_SENSOR = "replace_sensor"
SERVICE_REPLACE_IMAGE = "replace_image"

# we're not returning only one value, we're returning a dict here. So we need
# to have a separate literal for it to avoid confusion.
ATTR_DICT_OF_UNITS_OF_MEASUREMENT = "unit_of_measurement_dict"


CONF_SENSOR_BATTERY_LEVEL = READING_BATTERY
CONF_SENSOR_MOISTURE = READING_MOISTURE
CONF_SENSOR_CONDUCTIVITY = READING_CONDUCTIVITY
CONF_SENSOR_TEMPERATURE = READING_TEMPERATURE
CONF_SENSOR_ILLUMINANCE = READING_ILLUMINANCE

CONF_WARN_ILLUMINANCE = "warn_low_illuminance"

DEFAULT_MIN_BATTERY_LEVEL = 20
DEFAULT_MIN_TEMPERATURE = 10
DEFAULT_MAX_TEMPERATURE = 40
DEFAULT_MIN_MOISTURE = 20
DEFAULT_MAX_MOISTURE = 60
DEFAULT_MIN_CONDUCTIVITY = 500
DEFAULT_MAX_CONDUCTIVITY = 3000
DEFAULT_MIN_ILLUMINANCE = 0
DEFAULT_MAX_ILLUMINANCE = 100000
DEFAULT_MIN_HUMIDITY = 20
DEFAULT_MAX_HUMIDITY = 60
DEFAULT_MIN_MMOL = 2000
DEFAULT_MAX_MMOL = 20000
DEFAULT_MIN_MOL = 2
DEFAULT_MAX_MOL = 30


# See https://www.apogeeinstruments.com/conversion-ppfd-to-lux/
DEFAULT_LUX_TO_PPFD = 0.0185

DEFAULT_CHECK_DAYS = 3

STATE_LOW = "Low"
STATE_HIGH = "High"


# Flag for enabling/disabling the loading of the history from the database.
# This feature is turned off right now as its tests are not 100% stable.
ENABLE_LOAD_HISTORY = False

PLANTBOOK_TOKEN = None

# Override
# DATA_UTILITY = DOMAIN


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the OpenPlantBook component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up OpenPlantBook from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})

    # Set up utility sensor
    hass.data.setdefault(DATA_UTILITY, {})
    hass.data[DATA_UTILITY].setdefault(entry.entry_id, {})
    hass.data[DATA_UTILITY][entry.entry_id].setdefault(DATA_TARIFF_SENSORS, [])

    # We are creating some dummy sensors to play with
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    plant = PlantDevice(hass, entry)
    # pspieces = PlantSpecies(hass, entry, plant)
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
    pmaxmm = PlantMaxDli(hass, entry, plant)
    pminmm = PlantMinDli(hass, entry, plant)

    pcurb = PlantCurrentIlluminance(hass, entry, plant)
    pcurc = PlantCurrentConductivity(hass, entry, plant)
    pcurm = PlantCurrentMoisture(hass, entry, plant)
    pcurt = PlantCurrentTemperature(hass, entry, plant)
    pcurh = PlantCurrentHumidity(hass, entry, plant)

    hass.data[DOMAIN][entry.entry_id]["plant"] = plant

    component = EntityComponent(_LOGGER, DOMAIN, hass)

    plant_entities = [
        plant,
        # pspieces,
    ]
    plant_maxmin = [
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
        pmaxmm,
        pminmm,
    ]
    plant_sensors = [
        pcurb,
        pcurc,
        pcurm,
        pcurt,
        pcurh,
    ]
    plant_entities.extend(plant_maxmin)
    plant_entities.extend(plant_sensors)
    await component.async_add_entities(plant_entities)
    hass.data[DOMAIN][entry.entry_id][ATTR_METERS] = plant_maxmin
    hass.data[DOMAIN][entry.entry_id][ATTR_SENSORS] = plant_sensors
    device_id = plant.device_id

    await _plant_add_to_device_registry(hass, plant_entities, device_id)
    plant.add_sensors(
        temperature=pcurt,
        moisture=pcurm,
        conductivity=pcurc,
        illuminance=pcurb,
        humidity=pcurh,
    )

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
        max_mol=pmaxmm,
        min_mol=pminmm,
    )
    # plant.add_species(species=pspieces)

    integral_entities = []
    # Must be run after the sensors are added to the plant
    pcurppfd = PlantCurrentPpfd(hass, entry, plant)
    await component.async_add_entities([pcurppfd])
    integral_entities.append(pcurppfd)

    pintegral = PlantTotalLightIntegral(hass, entry, pcurppfd)
    await component.async_add_entities([pintegral])
    integral_entities.append(pintegral)

    pdli = PlantDailyLightIntegral(hass, entry, pintegral)
    await component.async_add_entities([pdli])
    integral_entities.append(pdli)

    # pcurppfdm = PlantCurrentPpfd(hass, entry, plant, micro=True)
    # await component.async_add_entities([pcurppfdm])
    # integral_entities.append(pcurppfdm)

    # pintegralm = PlantTotalLightIntegral(hass, entry, pcurppfdm)
    # await component.async_add_entities([pintegralm])
    # integral_entities.append(pintegralm)

    # pdlim = PlantDailyLightIntegral(hass, entry, pintegralm)
    # await component.async_add_entities([pdlim])
    # integral_entities.append(pdlim)

    plant.add_dli(dli=pdli)

    hass.data[DATA_UTILITY][entry.entry_id][DATA_TARIFF_SENSORS].append(pdli)
    await _plant_add_to_device_registry(hass, integral_entities, device_id)

    async def replace_sensor(call: ServiceCall) -> None:
        """Replace a sensor entity within a plant device"""
        meter_entity = call.data.get("meter_entity")
        new_sensor = call.data.get("new_sensor")
        if not meter_entity.startswith(DOMAIN + "."):
            _LOGGER.warning(
                "Refuse to update non-%s entities: %s", DOMAIN, meter_entity
            )
            return False
        if not new_sensor.startswith("sensor.") and new_sensor != "":
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

        if new_sensor != "":
            try:
                test = hass.states.get(new_sensor)
            except AttributeError:
                _LOGGER.error("New sensor entity %s not found", meter_entity)
                return False
            if test is None:
                _LOGGER.error("New sensor entity %s not found", meter_entity)
                return False
        else:
            _LOGGER.info("New sensor is blank, removing current value")
            new_sensor = None

        _LOGGER.info(
            "Going to replace the external sensor for %s with %s",
            meter_entity,
            new_sensor,
        )
        for key in hass.data[DOMAIN]:
            meters = hass.data[DOMAIN][key]["sensors"]
            _LOGGER.info(
                "Entry: %s",
                entry,
            )
            for meter in meters:
                if meter.entity_id == meter_entity:
                    _LOGGER.info("Sensor: %s", meter)
                    meter.replace_external_sensor(new_sensor)
        return

    # if not DOMAIN in hass.services.async_services():
    hass.services.async_register(DOMAIN, SERVICE_REPLACE_SENSOR, replace_sensor)
    # Lets add the dummy sensors automatically

    for sensor in plant_sensors:
        await hass.services.async_call(
            domain=DOMAIN,
            service=SERVICE_REPLACE_SENSOR,
            service_data={
                "meter_entity": sensor.entity_id,
                "new_sensor": sensor.entity_id.replace("plant.", "sensor.").replace(
                    "current", "dummy"
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
    for entity in plant_entities:
        erreg = er.async_get(hass)
        erreg.async_update_entity(entity.registry_entry.entity_id, device_id=device_id)


class PlantDevice(Entity):
    """Base device for plants"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Initialize the Plant component."""
        self._config = config
        self._hass = hass
        self._attr_name = config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]
        self._config_entries = []

        # Get entity_picture from options or from initial config
        self._attr_entity_picture = self._config.options.get(
            ATTR_ENTITY_PICTURE,
            self._config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
                ATTR_ENTITY_PICTURE
            ),
        )
        # Get species from options or from initial config
        self.species = self._config.options.get(
            FLOW_PLANT_SPECIES, self._config.data[FLOW_PLANT_INFO][FLOW_PLANT_SPECIES]
        )
        # Get display_species from options or from initial config
        self.display_species = self._config.options.get(
            OPB_DISPLAY_PID,
            self._config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS][OPB_DISPLAY_PID],
        )
        self._attr_unique_id = self._config.entry_id

        self.entity_id = async_generate_entity_id(
            f"{DOMAIN}.{{}}", self.name, current_ids={}
        )

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
        self.max_mol = None
        self.min_mol = None

        self.sensor_moisture = None
        self.sensor_temperature = None
        self.sensor_conductivity = None
        self.sensor_illuminance = None
        self.sensor_humidity = None

        self.dli = None
        self.micro_dli = None

        self.conductivity_status = None
        self.illuminance_status = None
        self.moisture_status = None
        self.temperature_status = None
        self.humidity_status = None

    @property
    def entity_category(self):
        return None

    @property
    def device_id(self):
        """The device ID used for all the entities"""
        return self._device_id

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "config_entries": self._config_entries,
        }

    @property
    def illuminance_trigger(self) -> bool:
        return self._config.options.get(FLOW_ILLUMINANCE_TRIGGER, True)

    @property
    def check_days(self) -> int:
        """Number of days to use for monitoring"""
        return self._config.options.get(CONF_CHECK_DAYS) or DEFAULT_CHECK_DAYS

    @property
    def extra_state_attributes(self) -> dict:
        """Return the device specific state attributes."""
        if not self.max_temperature:
            return {}
        attributes = {
            ATTR_SPECIES: self.display_species,
            CONF_CHECK_DAYS: self.check_days,
            f"{READING_MOISTURE}_status": self.moisture_status,
            f"{READING_TEMPERATURE}_status": self.temperature_status,
            f"{READING_CONDUCTIVITY}_status": self.conductivity_status,
            f"{READING_ILLUMINANCE}_status": self.illuminance_status,
            f"{READING_HUMIDITY}_status": self.humidity_status,
            ATTR_METERS: {
                READING_MOISTURE: None,
                READING_TEMPERATURE: None,
                READING_HUMIDITY: None,
                READING_CONDUCTIVITY: None,
                READING_ILLUMINANCE: None,
                READING_DLI: None,
            },
            ATTR_THRESHOLDS: {
                READING_TEMPERATURE: {
                    ATTR_MAX: self.max_temperature.entity_id,
                    ATTR_MIN: self.min_temperature.entity_id,
                },
                READING_ILLUMINANCE: {
                    ATTR_MAX: self.max_illuminance.entity_id,
                    ATTR_MIN: self.min_illuminance.entity_id,
                },
                READING_MOISTURE: {
                    ATTR_MAX: self.max_moisture.entity_id,
                    ATTR_MIN: self.min_moisture.entity_id,
                },
                READING_CONDUCTIVITY: {
                    ATTR_MAX: self.max_conductivity.entity_id,
                    ATTR_MIN: self.min_conductivity.entity_id,
                },
                READING_HUMIDITY: {
                    ATTR_MAX: self.max_humidity.entity_id,
                    ATTR_MIN: self.min_humidity.entity_id,
                },
                READING_MOL: {
                    ATTR_MAX: self.max_mol.entity_id,
                    ATTR_MIN: self.min_mol.entity_id,
                },
            },
        }
        if self.sensor_moisture is not None:
            attributes[ATTR_METERS][READING_MOISTURE] = self.sensor_moisture.entity_id
        if self.sensor_conductivity is not None:
            attributes[ATTR_METERS][
                READING_CONDUCTIVITY
            ] = self.sensor_conductivity.entity_id
        if self.sensor_illuminance is not None:
            attributes[ATTR_METERS][
                READING_ILLUMINANCE
            ] = self.sensor_illuminance.entity_id
        if self.sensor_temperature is not None:
            attributes[ATTR_METERS][
                READING_TEMPERATURE
            ] = self.sensor_temperature.entity_id
        if self.sensor_humidity is not None:
            attributes[ATTR_METERS][READING_HUMIDITY] = self.sensor_humidity.entity_id
        if self.dli is not None:
            attributes[ATTR_METERS][READING_DLI] = self.dli.entity_id

        return attributes

    def add_image(self, image_url: str | None) -> None:
        """Set new entity_picture"""
        self._attr_entity_picture = image_url
        options = self._config.options.copy()
        options[ATTR_ENTITY_PICTURE] = image_url
        self._hass.config_entries.async_update_entry(self._config, options=options)

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
        max_mol: Entity | None,
        min_mol: Entity | None,
    ) -> None:
        """Add the threshold entities"""
        _LOGGER.info("Adding thresholds")
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
        self.max_mol = max_mol
        self.min_mol = min_mol

    def add_sensors(
        self,
        moisture: Entity | None,
        temperature: Entity | None,
        conductivity: Entity | None,
        illuminance: Entity | None,
        humidity: Entity | None,
    ) -> None:
        """Add the sensor entities"""
        self.sensor_moisture = moisture
        self.sensor_temperature = temperature
        self.sensor_conductivity = conductivity
        self.sensor_illuminance = illuminance
        self.sensor_humidity = humidity

    def add_dli(
        self,
        dli: Entity | None,
    ) -> None:
        """Add the DLI-utility sensors"""
        self.dli = dli

    def update(self) -> None:
        """Run on every update of the entities"""

        state = STATE_OK

        if (
            self.sensor_moisture is not None
            and self.sensor_moisture.state != STATE_UNKNOWN
            and self.sensor_moisture.state != STATE_UNAVAILABLE
            and self.sensor_moisture.state is not None
        ):
            if int(self.sensor_moisture.state) < int(self.min_moisture.state):
                self.moisture_status = STATE_LOW
                state = STATE_PROBLEM
            elif int(self.sensor_moisture.state) > int(self.max_moisture.state):
                self.moisture_status = STATE_HIGH
                state = STATE_PROBLEM
            else:
                self.moisture_status = STATE_OK

        if (
            self.sensor_conductivity is not None
            and self.sensor_conductivity.state != STATE_UNKNOWN
            and self.sensor_conductivity.state != STATE_UNAVAILABLE
            and self.sensor_conductivity.state is not None
        ):
            if int(self.sensor_conductivity.state) < int(self.min_conductivity.state):
                self.conductivity_status = STATE_LOW
                state = STATE_PROBLEM
            elif int(self.sensor_conductivity.state) > int(self.max_conductivity.state):
                self.conductivity_status = STATE_HIGH
                state = STATE_PROBLEM
            else:
                self.conductivity_status = STATE_OK

        if (
            self.sensor_temperature is not None
            and self.sensor_temperature.state != STATE_UNKNOWN
            and self.sensor_temperature.state != STATE_UNAVAILABLE
            and self.sensor_temperature.state is not None
        ):
            if int(self.sensor_temperature.state) < int(self.min_temperature.state):
                self.temperature_status = STATE_LOW
                state = STATE_PROBLEM
            elif int(self.sensor_temperature.state) > int(self.max_temperature.state):
                self.temperature_status = STATE_HIGH
                state = STATE_PROBLEM
            else:
                self.temperature_status = STATE_OK

        if (
            self.sensor_humidity is not None
            and self.sensor_humidity.state != STATE_UNKNOWN
            and self.sensor_humidity.state != STATE_UNAVAILABLE
            and self.sensor_humidity.state is not None
        ):
            if int(self.sensor_humidity.state) < int(self.min_humidity.state):
                self.humidity_status = STATE_LOW
                state = STATE_PROBLEM
            elif int(self.sensor_humidity.state) > int(self.max_humidity.state):
                self.humidity_status = STATE_HIGH
                state = STATE_PROBLEM
            else:
                self.humidity_status = STATE_OK

        # TODO
        # better handlng of illuminance

        # Check the instant values for illuminance, but only high values
        # Checking Low values would create "problem" every night...
        _LOGGER.info(
            "S0: %s S1: %s S2: %s, M1: %s M2: %s",
            self.dli.state,
            self.dli.extra_state_attributes["last_period"],
            float(self.dli.extra_state_attributes["last_period"]) / PPFD_DLI_FACTOR,
            self.min_mol.state,
            self.max_mol.state,
        )
        if not self.illuminance_trigger:
            _LOGGER.info("Illuinance trigger is turned off")
        elif (
            self.illuminance_trigger is True
            and self.sensor_illuminance is not None
            and self.sensor_illuminance.state != STATE_UNKNOWN
            and self.sensor_illuminance.state != STATE_UNAVAILABLE
            and self.sensor_illuminance.state is not None
            and self.dli is not None
            and self.dli.state != STATE_UNKNOWN
            and self.dli.state != STATE_UNAVAILABLE
            and self.dli.state is not None
        ):
            if int(self.sensor_illuminance.state) > int(self.max_illuminance.state):
                self.illuminance_status = STATE_HIGH
                state = STATE_PROBLEM
                _LOGGER.warning(
                    "Current illuminance for %s to high: %s",
                    self.entity_id,
                    self.sensor_illuminance.state,
                )
            # check dli against max/min mol
            elif float(self.dli.extra_state_attributes["last_period"]) > 0 and float(
                self.dli.extra_state_attributes["last_period"]
            ) < int(self.min_mol.state):
                _LOGGER.warning(
                    "Yesterdays DLI for %s to low: %s",
                    self.entity_id,
                    self.dli.extra_state_attributes["last_period"],
                )
                self.illuminance_status = STATE_LOW
                state = STATE_PROBLEM
            elif float(self.dli.extra_state_attributes["last_period"]) > 0 and float(
                self.dli.extra_state_attributes["last_period"]
            ) > int(self.max_mol.state):
                _LOGGER.warning(
                    "Yesterdays DLI for %s to high: %s",
                    self.entity_id,
                    self.dli.extra_state_attributes["last_period"],
                )
                self.illuminance_status = STATE_HIGH
                state = STATE_PROBLEM
            else:
                self.illuminance_status = STATE_OK

        self._attr_state = state
        self.update_registry()

    def update_registry(self) -> None:
        """Update registry with correct data"""
        # Is there a better way to add an entity to the device registry?

        device_registry = dr.async_get(self._hass)
        device_registry.async_get_or_create(
            config_entry_id=self._config.entry_id,
            identifiers={(DOMAIN, self.unique_id)},
            name=self.name,
            model=self.display_species,
        )
        if self._device_id is None:
            _LOGGER.info("Getting device for %s entity id %s", DOMAIN, self.unique_id)
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, self.unique_id)}
            )
            self._device_id = device.id

    async def async_added_to_hass(self) -> None:
        _LOGGER.info("Plant added to hass, updating registry")
        self.update_registry()


class PlantSpecies(RestoreEntity):
    """The species entity"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._config = config
        self._hass = hass
        self._attr_name = f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Species"
        self._attr_state = config.data[FLOW_PLANT_INFO][FLOW_PLANT_SPECIES]
        self._display_species = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS][
            OPB_DISPLAY_PID
        ]
        self._plant = plantdevice
        self._attr_unique_id = f"{self._config.entry_id}-species"
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN}.{{}}", self.name, current_ids={}
        )

    @property
    def entity_category(self):
        """The category of the entity"""
        return EntityCategory.CONFIG

    @property
    def device_info(self):
        """Device info for the entity"""
        return {
            "identifiers": {(DOMAIN, self._plant.unique_id)},
            "name": self.name,
        }

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        return {"display_species": self._display_species}

    async def _state_changed_event(self, event):
        _LOGGER.info(event.data)
        if event.data.get("old_state") is None or event.data.get("new_state") is None:
            # _LOGGER.info("Nothing changed")
            return
        if event.data.get("old_state").state == event.data.get("new_state").state:
            # _LOGGER.info("Only attributes changed for %s", event.data.get("entity_id"))
            await self.state_attributes_changed(
                old_attributes=event.data.get("old_state").attributes,
                new_attributes=event.data.get("new_state").attributes,
            )
            return
        await self.state_changed(
            old_state=event.data.get("old_state").state,
            new_state=event.data.get("new_state").state,
        )

    async def state_attributes_changed(self, old_attributes, new_attributes) -> None:
        """Placeholder"""

    async def state_changed(self, old_state, new_state):
        """Run on every update"""

        # Here we ensure that you can change the species from the GUI, and we update
        # all parameters to match the new species
        new_species = new_state
        if new_species != self._attr_state and self._attr_state != STATE_UNKNOWN:
            opb_plant = None
            opb_ok = False
            _LOGGER.info(
                "Species changed from '%s' to '%s'", self._attr_state, new_species
            )

            if "openplantbook" in self.hass.services.async_services():
                _LOGGER.info("We have OpenPlantbook configured")
                await self.hass.services.async_call(
                    domain="openplantbook",
                    service="get",
                    service_data={"species": new_species},
                    blocking=True,
                    limit=30,
                )
                try:
                    opb_plant = self.hass.states.get(
                        "openplantbook."
                        + new_species.replace("'", "").replace(" ", "_")
                    )

                    _LOGGER.info("Result: %s", opb_plant)
                    opb_ok = True
                except AttributeError:
                    _LOGGER.warning("Did not find '%s' in OpenPlantbook", new_species)
                    await self.hass.services.async_call(
                        domain="persistent_notification",
                        service="create",
                        service_data={
                            "title": "Species not found",
                            "message": f"Could not find '{new_species}' in OpenPlantbook",
                        },
                    )
                    return True
            if opb_plant:
                _LOGGER.info(
                    "Setting entity_image to %s", opb_plant.attributes[FLOW_PLANT_IMAGE]
                )
                self._plant.add_image(opb_plant.attributes[FLOW_PLANT_IMAGE])

                for (ha_attribute, opb_attribute) in CONF_PLANTBOOK_MAPPING.items():

                    set_entity = getattr(self._plant, ha_attribute)

                    set_entity_id = set_entity.entity_id
                    _LOGGER.info(
                        "Setting %s to %s",
                        set_entity_id,
                        opb_plant.attributes[opb_attribute],
                    )
                    self.hass.states.async_set(
                        set_entity_id, opb_plant.attributes[opb_attribute]
                    )
                self._attr_state = opb_plant.attributes[OPB_PID]
                _LOGGER.info(
                    "Setting display_species to %s",
                    opb_plant.attributes[OPB_DISPLAY_PID],
                )

                self._display_species = opb_plant.attributes[OPB_DISPLAY_PID]
                self.async_write_ha_state()

            else:
                if opb_ok:
                    _LOGGER.warning("Did not find '%s' in OpenPlantbook", new_species)
                    await self.hass.services.async_call(
                        domain="persistent_notification",
                        service="create",
                        service_data={
                            "title": "Species not found",
                            "message": f"Could not find '{new_species}' in OpenPlantbook. See the state of openplantbook.search_result for suggestions",
                        },
                    )
                    # Just do a plantbook search to allow the user to find a better result
                    await self.hass.services.async_call(
                        domain="openplantbook",
                        service="search",
                        service_data={"alias": new_species},
                        blocking=False,
                        limit=30,
                    )
                else:
                    # We just accept whatever species the user sets.
                    # They can always change it later

                    self._display_species = new_species
                    self.async_write_ha_state()

                return True

            self._plant.update_registry()

    async def async_added_to_hass(self) -> None:
        """Restore state of species on startup."""
        async_track_state_change_event(
            self._hass,
            list([self.entity_id]),
            self._state_changed_event,
        )

        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if not state:
            return
        self._attr_state = state.state
        _LOGGER.info("Restoring for %s: %s", self.entity_id, state.attributes)
        if "display_species" in state.attributes:
            self._display_species = state.attributes["display_species"]
        _LOGGER.info(
            "Species added to hass - updating registry: %s", self.state_attributes
        )

        async_dispatcher_connect(
            self.hass, DATA_UPDATED, self._schedule_immediate_update
        )

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)


class PlantMinMax(RestoreEntity):
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
        if not self._attr_state or self._attr_state == STATE_UNKNOWN:
            self._attr_state = self._default_state

    @property
    def entity_category(self):
        return EntityCategory.CONFIG

    @property
    def unit_of_measurement(self) -> str | None:
        return self._attr_unit_of_measurement

    def _state_changed_event(self, event):
        if event.data.get("old_state") is None or event.data.get("new_state") is None:
            return
        if event.data.get("old_state").state == event.data.get("new_state").state:
            _LOGGER.info("Only attributes changed for %s", event.data.get("entity_id"))
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
        _LOGGER.info(
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
            _LOGGER.info(
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
        async_track_state_change_event(
            self._hass,
            list([self.entity_id]),
            self._state_changed_event,
        )

        state = await self.async_get_last_state()
        if not state:
            return
        self._attr_state = state.state
        _LOGGER.info("Restoring unit for %s: %s", self.entity_id, state.attributes)
        self._attr_unit_of_measurement = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)

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
        """Initialize the Plant component."""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Max Moisture"
        )
        self._default_state = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_MOISTURE, STATE_UNKNOWN
        )
        self._attr_unique_id = f"{config.entry_id}-max-moisture"
        self._attr_unit_of_measurement = PERCENTAGE

        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return SensorDeviceClass.HUMIDITY


class PlantMinMoisture(PlantMinMax):
    """Entity class for min moisture threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Min Moisture"
        )
        self._default_state = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_MOISTURE, STATE_UNKNOWN
        )
        self._attr_unique_id = f"{config.entry_id}-min-moisture"
        self._attr_unit_of_measurement = PERCENTAGE

        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return SensorDeviceClass.HUMIDITY


class PlantMaxTemperature(PlantMinMax):
    """Entity class for max temperature threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Max Temperature"
        )
        self._attr_unique_id = f"{config.entry_id}-max-temperature"

        self._default_state = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_TEMPERATURE, DEFAULT_MAX_TEMPERATURE
        )
        super().__init__(hass, config, plantdevice)
        self._default_unit_of_measurement = self._hass.config.units.temperature_unit

    @property
    def device_class(self):
        return SensorDeviceClass.TEMPERATURE

    @property
    def unit_of_measurement(self) -> str | None:
        """Get unit of measurement from the temperature meter"""
        if not hasattr(self, "_attr_unit_of_measurement"):
            _LOGGER.info("UoM is Unset")
            self._attr_unit_of_measurement = self._default_unit_of_measurement
        if self._attr_unit_of_measurement is None:
            _LOGGER.info("UoM is set but None")
            self._attr_unit_of_measurement = self._default_unit_of_measurement

        if (
            "meters" in self._plant.extra_state_attributes
            and "temperature" in self._plant.extra_state_attributes["meters"]
        ):
            meter = self._hass.states.get(
                self._plant.extra_state_attributes["meters"]["temperature"]
            )
            if not ATTR_UNIT_OF_MEASUREMENT in meter.attributes:
                return self._attr_unit_of_measurement

            # _LOGGER.debug(
            #    "Default: %s, Mine: %s, Parent: %s",
            #    self._default_unit_of_measurement,
            #    self._attr_unit_of_measurement,
            #    meter.attributes[ATTR_UNIT_OF_MEASUREMENT],
            # )
            if (
                self._attr_unit_of_measurement
                != meter.attributes[ATTR_UNIT_OF_MEASUREMENT]
            ):
                self._attr_unit_of_measurement = meter.attributes[
                    ATTR_UNIT_OF_MEASUREMENT
                ]

            return self._attr_unit_of_measurement

    def state_attributes_changed(self, old_attributes, new_attributes):
        """Calculate C or F"""
        _LOGGER.debug("Old attributes: %s", old_attributes)
        _LOGGER.debug("New attributes: %s", new_attributes)
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
            _LOGGER.debug("Changing from F to C measurement is %s", self.state)
            # new_state = int(round((int(self.state) - 32) * 0.5556, 0))
            new_state = round(
                convert_temperature(
                    temperature=float(self.state),
                    from_unit=TEMP_FAHRENHEIT,
                    to_unit=TEMP_CELSIUS,
                )
            )

        if (
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°C"
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°F"
        ):
            _LOGGER.debug("Changing from C to F measurement is %s", self.state)
            new_state = round(
                convert_temperature(
                    temperature=float(self.state),
                    from_unit=TEMP_CELSIUS,
                    to_unit=TEMP_FAHRENHEIT,
                )
            )

        _LOGGER.debug("New state = %s", new_state)
        self._hass.states.set(self.entity_id, new_state, new_attributes)


class PlantMinTemperature(PlantMinMax):
    """Entity class for min temperature threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Min Temperature"
        )
        self._default_state = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_TEMPERATURE, DEFAULT_MIN_TEMPERATURE
        )

        self._attr_unique_id = f"{config.entry_id}-min-temperature"
        super().__init__(hass, config, plantdevice)
        self._default_unit_of_measurement = self._hass.config.units.temperature_unit

    @property
    def device_class(self):
        return SensorDeviceClass.TEMPERATURE

    @property
    def unit_of_measurement(self) -> str | None:
        if not hasattr(self, "_attr_unit_of_measurement"):
            self._attr_unit_of_measurement = self._default_unit_of_measurement
        if self._attr_unit_of_measurement is None:
            self._attr_unit_of_measurement = self._default_unit_of_measurement

        if (
            "meters" in self._plant.extra_state_attributes
            and "temperature" in self._plant.extra_state_attributes["meters"]
        ):
            meter = self._hass.states.get(
                self._plant.extra_state_attributes["meters"]["temperature"]
            )
            if not ATTR_UNIT_OF_MEASUREMENT in meter.attributes:
                return self._attr_unit_of_measurement
            # _LOGGER.info(
            #     "Default: %s, Mine: %s, Parent: %s",
            #     self._default_unit_of_measurement,
            #     self._attr_unit_of_measurement,
            #     meter.attributes[ATTR_UNIT_OF_MEASUREMENT],
            # )
            if (
                self._attr_unit_of_measurement
                != meter.attributes[ATTR_UNIT_OF_MEASUREMENT]
            ):
                self._attr_unit_of_measurement = meter.attributes[
                    ATTR_UNIT_OF_MEASUREMENT
                ]

            return self._attr_unit_of_measurement

    def state_attributes_changed(self, old_attributes, new_attributes):
        """Calculate C or F"""
        # _LOGGER.debug("Old attributes: %s", old_attributes)
        # _LOGGER.debug("New attributes: %s", new_attributes)
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
            _LOGGER.debug("Changing from F to C measurement is %s", self.state)
            new_state = round(
                convert_temperature(
                    temperature=float(self.state),
                    from_unit=TEMP_FAHRENHEIT,
                    to_unit=TEMP_CELSIUS,
                )
            )

            # new_state = int(round((int(self.state) - 32) * 0.5556, 0))

        if (
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°C"
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°F"
        ):
            _LOGGER.debug("Changing from C to F measurement is %s", self.state)
            new_state = round(
                convert_temperature(
                    temperature=float(self.state),
                    from_unit=TEMP_CELSIUS,
                    to_unit=TEMP_FAHRENHEIT,
                )
            )

        _LOGGER.debug("New state = %s", new_state)
        self._hass.states.set(self.entity_id, new_state, new_attributes)


class PlantMaxIlluminance(PlantMinMax):
    """Entity class for max illuminance threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Max Illuminance"
        )
        self._default_state = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_ILLUMINANCE, STATE_UNKNOWN
        )
        self._attr_unique_id = f"{config.entry_id}-max-illuminance"
        self._attr_unit_of_measurement = LIGHT_LUX
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return SensorDeviceClass.ILLUMINANCE


class PlantMinIlluminance(PlantMinMax):
    """Entity class for min illuminance threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Min Brghtness"
        )
        self._default_state = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_ILLUMINANCE, STATE_UNKNOWN
        )
        self._attr_unique_id = f"{config.entry_id}-min-illuminance"
        self._attr_unit_of_measurement = LIGHT_LUX
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return SensorDeviceClass.ILLUMINANCE


class PlantMaxDli(PlantMinMax):
    """Entity class for max illuminance threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._attr_name = f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Max DLI"
        self._default_state = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_MOL, STATE_UNKNOWN
        )
        self._attr_unique_id = f"{config.entry_id}-max-dli"
        self._attr_unit_of_measurement = UNIT_MICRO_PPFD
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return SensorDeviceClass.ILLUMINANCE


class PlantMinDli(PlantMinMax):
    """Entity class for min illuminance threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._attr_name = f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Min DLI"
        self._default_state = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_MOL, STATE_UNKNOWN
        )
        self._attr_unique_id = f"{config.entry_id}-min-dli"
        self._attr_unit_of_measurement = UNIT_MICRO_PPFD

        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return SensorDeviceClass.ILLUMINANCE


class PlantMaxConductivity(PlantMinMax):
    """Entity class for max conductivity threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Max Condctivity"
        )
        self._default_state = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_CONDUCTIVITY, STATE_UNKNOWN
        )
        self._attr_unique_id = f"{config.entry_id}-max-conductivity"
        self._attr_unit_of_measurement = UNIT_CONDUCTIVITY
        super().__init__(hass, config, plantdevice)


class PlantMinConductivity(PlantMinMax):
    """Entity class for min conductivity threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Min Conductivity"
        )
        self._default_state = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_CONDUCTIVITY, STATE_UNKNOWN
        )
        self._attr_unique_id = f"{config.entry_id}-min-conductivity"
        self._attr_unit_of_measurement = UNIT_CONDUCTIVITY

        super().__init__(hass, config, plantdevice)


class PlantMaxHumidity(PlantMinMax):
    """Entity class for max humidity threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Max Humidity"
        )
        self._default_state = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_HUMIDITY, STATE_UNKNOWN
        )
        self._attr_unique_id = f"{config.entry_id}-max-humidity"
        self._attr_unit_of_measurement = PERCENTAGE

        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return SensorDeviceClass.HUMIDITY


class PlantMinHumidity(PlantMinMax):
    """Entity class for min conductivity threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Min Humidity"
        )
        self._default_state = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_HUMIDITY, STATE_UNKNOWN
        )
        self._attr_unique_id = f"{config.entry_id}-min-humidity"
        self._attr_unit_of_measurement = PERCENTAGE
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return SensorDeviceClass.HUMIDITY


class PlantCurrentStatus(RestoreSensor):
    """Parent class for the meter classes below"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._hass = hass
        self._config = config
        self._default_state = 0
        self._plant = plantdevice
        self._conf_check_days = self._plant.check_days
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN}.{{}}", self.name, current_ids={}
        )
        if not self._attr_native_value or self._attr_native_value == STATE_UNKNOWN:
            self._attr_native_value = self._default_state
        self._history = DailyHistory(self._conf_check_days)

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    @property
    def extra_state_attributes(self) -> dict:
        if self._external_sensor:
            attributes = {
                "external_sensor": self._external_sensor,
                "history_max": self._history.max,
                "history_min": self._history.min,
            }
            return attributes

    def replace_external_sensor(self, new_sensor: str | None) -> None:
        """Modify the external sensor"""
        _LOGGER.info("Setting %s external sensor to %s", self.entity_id, new_sensor)
        self._external_sensor = new_sensor
        async_track_state_change_event(
            self._hass,
            list([self.entity_id, self._external_sensor]),
            self._state_changed_event,
        )

        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()

        # We do not restore the state for these they are red from the external sensor anyway
        # self._attr_state = state.state
        self._attr_native_value = STATE_UNKNOWN
        if state:
            if "external_sensor" in state.attributes:
                _LOGGER.info(
                    "External sensor for %s in state-attributes: %s",
                    self.entity_id,
                    state.attributes["external_sensor"],
                )
                self.replace_external_sensor(state.attributes["external_sensor"])
        if "recorder" in self.hass.config.components:
            # only use the database if it's configured
            await get_instance(self.hass).async_add_executor_job(
                self._load_history_from_db
            )
        tracker = [self.entity_id]
        if self._external_sensor:
            tracker.append(self._external_sensor)
        async_track_state_change_event(
            self._hass,
            tracker,
            self._state_changed_event,
        )
        async_dispatcher_connect(
            self._hass, DATA_UPDATED, self._schedule_immediate_update
        )

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)

    @callback
    def _state_changed_event(self, event):
        """Sensor state change event."""
        # _LOGGER.info(event.data.get("entity_id"))
        self.state_changed(event.data.get("entity_id"), event.data.get("new_state"))

    @callback
    def state_changed(self, entity_id, new_state):
        """Run on every update to allow for changes from the GUI and service call"""
        # _LOGGER.info(
        #     "Running state-changed for %s entity_id_changed: %s, new_state: %s",
        #     self.entity_id,
        #     entity_id,
        #     new_state,
        # )
        if not self.hass.states.get(self.entity_id):
            return
        current_attrs = self.hass.states.get(self.entity_id).attributes
        if current_attrs.get("external_sensor") != self._external_sensor:
            self.replace_external_sensor(current_attrs.get("external_sensor"))
        if self._external_sensor:
            external_sensor = self.hass.states.get(self._external_sensor)
            if external_sensor:
                self._attr_native_value = external_sensor.state
                self._attr_native_unit_of_measurement = external_sensor.attributes[
                    ATTR_UNIT_OF_MEASUREMENT
                ]
            else:
                self._attr_native_value = STATE_UNKNOWN
        else:
            self._attr_native_value = STATE_UNKNOWN

        if self.state == STATE_UNKNOWN or self.state is None:
            return
        # _LOGGER.info("Adding measurement to the db for %s: %s", entity_id, self.state)
        self._history.add_measurement(self.state, new_state.last_updated)

        return

    def _load_history_from_db(self):
        """Load the history of the illuminance values from the database.
        This only needs to be done once during startup.
        """

        if self._external_sensor is None:
            _LOGGER.debug(
                "Not reading the history from the database as "
                "there is no external sensor configured"
            )
            return
        start_date = dt_util.utcnow() - timedelta(days=self._conf_check_days)
        entity_id = self.entity_id

        _LOGGER.debug(
            "Initializing values for %s days for %s from the database",
            self._conf_check_days,
            self.name,
        )
        lower_entity_id = entity_id.lower()
        history_list = history.state_changes_during_period(
            self.hass,
            start_date,
            entity_id=lower_entity_id,
            no_attributes=True,
        )
        for state in history_list.get(lower_entity_id, []):
            # filter out all None, NaN and "unknown" states
            # only keep real values
            with suppress(ValueError):
                self._history.add_measurement(int(state.state), state.last_updated)

        _LOGGER.debug("Initializing from database completed")


class PlantCurrentIlluminance(PlantCurrentStatus):
    """Entity class for the current illuminance meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Current Illuminance"
        )
        self._attr_unique_id = f"{config.entry_id}-current-illuminance"
        self._attr_icon = "mdi:brightness-6"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(
            FLOW_SENSOR_ILLUMINANCE
        )
        _LOGGER.info(
            "Added external sensor for %s %s", self.entity_id, self._external_sensor
        )
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return SensorDeviceClass.ILLUMINANCE

    # @property
    # def native_unit_of_measurement(self):
    #     return "lx"

    # @property
    # def extra_state_attributes(self) -> dict:
    #     if self._external_sensor:
    #         attributes = {
    #             "external_sensor": self._external_sensor,
    #             "history_max": self._history.max,
    #             "history_min": self._history.min,
    #         }
    #         return attributes


class PlantCurrentConductivity(PlantCurrentStatus):
    """Entity class for the current conductivity meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Current Conductivity"
        )
        self._attr_unique_id = f"{config.entry_id}-current-conductivity"
        self._attr_icon = "mdi:spa-outline"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(
            FLOW_SENSOR_CONDUCTIVITY
        )

        super().__init__(hass, config, plantdevice)

    # @property
    # def native_unit_of_measurement(self):
    #     return "uS/cm"

    @property
    def device_class(self):
        return None


class PlantCurrentMoisture(PlantCurrentStatus):
    """Entity class for the current moisture meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Current Moisture Level"
        )
        self._attr_unique_id = f"{config.entry_id}-current-moisture"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_MOISTURE)
        self._attr_icon = "mdi:water"

        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return SensorDeviceClass.HUMIDITY

    # @property
    # def native_unit_of_measurement(self):
    #     return PERCENTAGE


class PlantCurrentTemperature(PlantCurrentStatus):
    """Entity class for the current temperature meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Current Temperature"
        )
        self._attr_unique_id = f"{config.entry_id}-current-temperature"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(
            FLOW_SENSOR_TEMPERATURE
        )
        self._attr_icon = "mdi:thermometer"
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return SensorDeviceClass.TEMPERATURE

    # @property
    # def native_unit_of_measurement(self):
    #     return TEMP_CELSIUS


class PlantCurrentHumidity(PlantCurrentStatus):
    """Entity class for the current humidity meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Current Humidity"
        )
        self._attr_unique_id = f"{config.entry_id}-current-humidity"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_HUMIDITY)
        self._attr_icon = "mdi:water-percent"
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return SensorDeviceClass.HUMIDITY

    # @property
    # def native_unit_of_measurement(self):
    #     return PERCENTAGE


class PlantCurrentPpfd(PlantCurrentStatus):
    """Entity reporting current PPFD calculated from LX"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        #     If we work with micro-units, the measurement is mol
        #     If we work with whole units, the measurement is i mmol
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Current PPFD (mol)"
        )

        self._attr_unique_id = f"{config.entry_id}-current-ppfd"
        self._attr_unit_of_measurement = UNIT_PPFD
        self._attr_native_unit_of_measurement = UNIT_PPFD

        self._plant = plantdevice

        self._external_sensor = self._plant.sensor_illuminance.entity_id
        self._attr_icon = "mdi:white-balance-sunny"
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return SensorDeviceClass.ILLUMINANCE

    # @property
    # def extra_state_attributes(self) -> dict:
    #     if self._external_sensor:
    #         attributes = {
    #             "external_sensor": self._external_sensor,
    #             "history_max": self._history.max,
    #             "history_min": self._history.min,
    #         }
    #         if (
    #             self.state
    #             and self.state != STATE_UNKNOWN
    #             and self.state != STATE_UNAVAILABLE
    #         ):
    #             attributes["ppfd_mmol"] = round(float(self.state) / PPFD_DLI_FACTOR, 2)
    #
    #         return attributes

    def ppfd(self, value) -> float:
        """
        Returns a calculated PPFD-value from the lx-value

        See https://community.home-assistant.io/t/light-accumulation-for-xiaomi-flower-sensor/111180/3
        https://www.apogeeinstruments.com/conversion-ppfd-to-lux/
        μmol/m²/s
        """
        if value is not None and value != STATE_UNAVAILABLE and value != STATE_UNKNOWN:
            value = float(value) * DEFAULT_LUX_TO_PPFD / 1000000
            # if self._micro:
            #     value = value / 1000000

        return value

    @callback
    def state_changed(self, entity_id, new_state):
        """Run on every update to allow for changes from the GUI and service call"""
        _LOGGER.info("Updating PPFD-sensor: %s %s", entity_id, new_state)
        if not self.hass.states.get(self.entity_id):
            return
        if self._external_sensor != self._plant.sensor_illuminance.entity_id:
            self.replace_external_sensor(self._plant.sensor_illuminance.entity_id)
        if self._external_sensor:
            external_sensor = self.hass.states.get(self._external_sensor)
            if external_sensor:
                self._attr_native_value = self.ppfd(external_sensor.state)
            else:
                self._attr_native_value = STATE_UNKNOWN
        else:
            self._attr_native_value = STATE_UNKNOWN

        if self.state == STATE_UNKNOWN or self.state is None:
            return
        # _LOGGER.info("Adding measurement to the db for %s: %s", entity_id, self.state)
        self._history.add_measurement(self.state, new_state.last_updated)

        return


class PlantTotalLightIntegral(IntegrationSensor):
    """Entity class to calculate PPFD from LX"""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        illuminance_ppfd_sensor: Entity,
    ) -> None:
        self._method = METHOD_TRAPEZOIDAL
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Total PPFD (mol) Integral"
        )

        self._attr_unique_id = f"{config.entry_id}-ppfd-integral"
        self._unit_of_measurement = UNIT_PPFD
        self._unit_time_str = TIME_SECONDS
        self._round_digits = 2
        self._sensor_source_id = illuminance_ppfd_sensor.entity_id
        self._unit_time = UNIT_TIME[self._unit_time_str]
        self._unit_prefix = 1
        self._unit_template = f"{''}{{}}"
        self._state = None
        self._attr_icon = "mdi:math-integral"


class PlantDailyLightIntegral(UtilityMeterSensor):
    """Entity class to calculate Daily Light Integral from PPDF"""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        illuminance_integration_sensor: Entity,
    ):
        self._name = (
            f"{config.data[FLOW_PLANT_INFO][FLOW_PLANT_NAME]} Daily Light Integral"
        )

        self._attr_unique_id = f"{config.entry_id}-ppfd-integral"

        self._attr_unique_id = self._attr_unique_id + "-micro"
        self._unit_of_measurement = UNIT_DLI
        self._sensor_source_id = illuminance_integration_sensor.entity_id
        self._period = DAILY
        self._meter_offset = timedelta(seconds=0)
        self._cron_pattern = PERIOD2CRON[self._period].format(
            minute=self._meter_offset.seconds % 3600 // 60,
            hour=self._meter_offset.seconds // 3600,
            day=self._meter_offset.days + 1,
        )

        self._last_period = Decimal(0)
        self._last_reset = dt_util.utcnow()
        self._sensor_delta_values = None
        self._sensor_net_consumption = None
        self._parent_meter = config.entry_id
        self._tariff = None
        self._tariff_entity = None
        self._state = 0
        self._collecting = None


class DailyHistory:
    """Stores one measurement per day for a maximum number of days.
    At the moment only the maximum value per day is kept.
    """

    def __init__(self, max_length):
        """Create new DailyHistory with a maximum length of the history."""
        _LOGGER.info("Creating DailyHistory database")
        self.max_length = max_length
        self._days = None
        self._max_dict = {}
        self._min_dict = {}
        self.max = 0
        self.min = 0

    def add_measurement(self, value, timestamp=None):
        """Add a new measurement for a certain day."""
        # _LOGGER.info("Updating DailyHistory database with %s", value)
        day = (timestamp or datetime.now()).date()
        if not isinstance(value, (int, float)):
            return
        if self._days is None:
            self._days = deque()
            self._add_day(day, value)
        else:
            current_day = self._days[-1]
            if day == current_day:
                self._max_dict[day] = max(value, self._max_dict[day])
                self._min_dict[day] = min(value, self._min_dict[day])
            elif day > current_day:
                self._add_day(day, value)
            else:
                _LOGGER.warning("Received old measurement, not storing it")

        self.max = max(self._max_dict.values())
        self.min = min(self._min_dict.values())

    def _add_day(self, day, value):
        """Add a new day to the history.
        Deletes the oldest day, if the queue becomes too long.
        """
        if len(self._days) == self.max_length:
            oldest = self._days.popleft()
            del self._max_dict[oldest]
            del self._min_dict[oldest]
        self._days.append(day)
        if not isinstance(value, (int, float)):
            return
        self._max_dict[day] = value
        self._min_dict[day] = value
