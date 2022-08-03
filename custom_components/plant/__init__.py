"""Support for monitoring plants."""
from __future__ import annotations

import logging

from homeassistant.components.utility_meter.const import (
    DATA_TARIFF_SENSORS,
    DATA_UTILITY,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_PICTURE,
    ATTR_NAME,
    STATE_OK,
    STATE_PROBLEM,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.helpers.entity_component import EntityComponent

from .const import (
    ATTR_MAX,
    ATTR_METERS,
    ATTR_MIN,
    ATTR_PLANT,
    ATTR_SENSORS,
    ATTR_SPECIES,
    ATTR_THRESHOLDS,
    DATA_SOURCE,
    DOMAIN,
    FLOW_ILLUMINANCE_TRIGGER,
    FLOW_PLANT_INFO,
    OPB_DISPLAY_PID,
    READING_CONDUCTIVITY,
    READING_DLI,
    READING_HUMIDITY,
    READING_ILLUMINANCE,
    READING_MOISTURE,
    READING_TEMPERATURE,
    SERVICE_REPLACE_SENSOR,
    STATE_HIGH,
    STATE_LOW,
)
from .plant_helpers import PlantHelper
from .plant_meters import (
    PlantCurrentConductivity,
    PlantCurrentHumidity,
    PlantCurrentIlluminance,
    PlantCurrentMoisture,
    PlantCurrentPpfd,
    PlantCurrentTemperature,
    PlantDailyLightIntegral,
    PlantTotalLightIntegral,
)
from .plant_thresholds import (
    PlantMaxConductivity,
    PlantMaxDli,
    PlantMaxHumidity,
    PlantMaxIlluminance,
    PlantMaxMoisture,
    PlantMaxTemperature,
    PlantMinConductivity,
    PlantMinDli,
    PlantMinHumidity,
    PlantMinIlluminance,
    PlantMinMoisture,
    PlantMinTemperature,
)

_LOGGER = logging.getLogger(__name__)


# Use this during testing to generate some dummy-sensors
# to provide random readings for temperature, moisture etc.
#
USE_DUMMY_SENSORS = False


async def async_setup(hass: HomeAssistant, config: dict):
    """
    Set up the plant component

    Configuration.yaml is no longer used.
    This function only tries to migrate the legacy config.
    """
    if config.get(DOMAIN):
        # Only import if we haven't before.
        config_entry = _async_find_matching_config_entry(hass)
        if not config_entry:
            _LOGGER.debug("Old setup - with config: %s", config[DOMAIN])
            for plant in config[DOMAIN]:
                _LOGGER.warning("Migrating plant: %s", plant)
                await async_migrate_plant(hass, plant, config[DOMAIN][plant])
        else:
            _LOGGER.warning(
                "Config already imported. Please delete all your %s related config from configuration.yaml",
                DOMAIN,
            )
    return True


@callback
def _async_find_matching_config_entry(hass: HomeAssistant) -> ConfigEntry | None:
    """Check if there are migrated entities"""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.source == SOURCE_IMPORT:
            return entry


async def async_migrate_plant(hass: HomeAssistant, plant_id: str, config: dict) -> None:
    """Try to migrate the config from yaml"""

    plant_helper = PlantHelper(hass)
    plant_config = await plant_helper.generate_configentry(config=config)
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=plant_config
        )
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up Plant from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})

    # Set up utility sensor
    hass.data.setdefault(DATA_UTILITY, {})
    hass.data[DATA_UTILITY].setdefault(entry.entry_id, {})
    hass.data[DATA_UTILITY][entry.entry_id].setdefault(DATA_TARIFF_SENSORS, [])

    if FLOW_PLANT_INFO not in entry.data:
        return True

    if USE_DUMMY_SENSORS:
        # We are creating some dummy sensors to play with during testing
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    plant = PlantDevice(hass, entry)
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

    hass.data[DOMAIN][entry.entry_id][ATTR_PLANT] = plant

    plant_entities = [
        plant,
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

    # Add all the entities to Hass
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    await component.async_add_entities(plant_entities)

    # Store the entities for later
    hass.data[DOMAIN][entry.entry_id][ATTR_METERS] = plant_maxmin
    hass.data[DOMAIN][entry.entry_id][ATTR_SENSORS] = plant_sensors

    # Add the rest of the entities to device registry together with plant
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
        max_dli=pmaxmm,
        min_dli=pminmm,
    )

    # Crete and add the integral-entities
    # Must be run after the sensors are added to the plant
    integral_entities = []

    pcurppfd = PlantCurrentPpfd(hass, entry, plant)
    await component.async_add_entities([pcurppfd])
    integral_entities.append(pcurppfd)

    pintegral = PlantTotalLightIntegral(hass, entry, pcurppfd)
    await component.async_add_entities([pintegral])
    integral_entities.append(pintegral)

    pdli = PlantDailyLightIntegral(hass, entry, pintegral)
    await component.async_add_entities([pdli])
    integral_entities.append(pdli)

    plant.add_dli(dli=pdli)

    hass.data[DATA_UTILITY][entry.entry_id][DATA_TARIFF_SENSORS].append(pdli)
    await _plant_add_to_device_registry(hass, integral_entities, device_id)

    #
    # Service call to replace sensors
    #
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
            new_sensor = None

        _LOGGER.info(
            "Going to replace the external sensor for %s with %s",
            meter_entity,
            new_sensor,
        )
        for key in hass.data[DOMAIN]:
            meters = hass.data[DOMAIN][key]["sensors"]
            for meter in meters:
                if meter.entity_id == meter_entity:
                    meter.replace_external_sensor(new_sensor)
        return

    hass.services.async_register(DOMAIN, SERVICE_REPLACE_SENSOR, replace_sensor)

    # Lets add the dummy sensors automatically if we are testing stuff
    if USE_DUMMY_SENSORS is True:
        for sensor in plant_sensors:
            if sensor.external_sensor is None:
                await hass.services.async_call(
                    domain=DOMAIN,
                    service=SERVICE_REPLACE_SENSOR,
                    service_data={
                        "meter_entity": sensor.entity_id,
                        "new_sensor": sensor.entity_id.replace(
                            "plant.", "sensor."
                        ).replace("current", "dummy"),
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
        self.display_species = (
            self._config.options.get(
                OPB_DISPLAY_PID, self._config.data[FLOW_PLANT_INFO].get(OPB_DISPLAY_PID)
            )
            or self.species
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
        self.max_dli = None
        self.min_dli = None

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
        self.dli_status = None

    @property
    def entity_category(self) -> None:
        """The plant device itself does not have a category"""
        return None

    @property
    def device_class(self):
        return DOMAIN

    @property
    def device_id(self) -> str:
        """The device ID used for all the entities"""
        return self._device_id

    @property
    def device_info(self) -> dict:
        """Device info for devices"""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "config_entries": self._config_entries,
        }

    @property
    def illuminance_trigger(self) -> bool:
        """Whether we will generate alarms based on illuminance or dli"""
        return self._config.options.get(FLOW_ILLUMINANCE_TRIGGER, True)

    @property
    def extra_state_attributes(self) -> dict:
        """Return the device specific state attributes."""
        if not self.plant_complete:
            # We are not fully set up, so we just return an empty dict for now
            return {}
        attributes = {
            ATTR_SPECIES: self.display_species,
            f"{READING_MOISTURE}_status": self.moisture_status,
            f"{READING_TEMPERATURE}_status": self.temperature_status,
            f"{READING_CONDUCTIVITY}_status": self.conductivity_status,
            f"{READING_ILLUMINANCE}_status": self.illuminance_status,
            f"{READING_HUMIDITY}_status": self.humidity_status,
            f"{READING_DLI}_status": self.dli_status,
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
                READING_DLI: {
                    ATTR_MAX: self.max_dli.entity_id,
                    ATTR_MIN: self.min_dli.entity_id,
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
        self.max_dli = max_dli
        self.min_dli = min_dli

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
        self.plant_complete = True

    def update(self) -> None:
        """Run on every update of the entities"""

        new_state = STATE_OK

        if (
            self.sensor_moisture is not None
            and self.sensor_moisture.state != STATE_UNKNOWN
            and self.sensor_moisture.state != STATE_UNAVAILABLE
            and self.sensor_moisture.state is not None
        ):
            if float(self.sensor_moisture.state) < float(self.min_moisture.state):
                self.moisture_status = STATE_LOW
                new_state = STATE_PROBLEM
            elif float(self.sensor_moisture.state) > float(self.max_moisture.state):
                self.moisture_status = STATE_HIGH
                new_state = STATE_PROBLEM
            else:
                self.moisture_status = STATE_OK

        if (
            self.sensor_conductivity is not None
            and self.sensor_conductivity.state != STATE_UNKNOWN
            and self.sensor_conductivity.state != STATE_UNAVAILABLE
            and self.sensor_conductivity.state is not None
        ):
            if float(self.sensor_conductivity.state) < float(
                self.min_conductivity.state
            ):
                self.conductivity_status = STATE_LOW
                new_state = STATE_PROBLEM
            elif float(self.sensor_conductivity.state) > float(
                self.max_conductivity.state
            ):
                self.conductivity_status = STATE_HIGH
                new_state = STATE_PROBLEM
            else:
                self.conductivity_status = STATE_OK

        if (
            self.sensor_temperature is not None
            and self.sensor_temperature.state != STATE_UNKNOWN
            and self.sensor_temperature.state != STATE_UNAVAILABLE
            and self.sensor_temperature.state is not None
        ):
            if float(self.sensor_temperature.state) < float(self.min_temperature.state):
                self.temperature_status = STATE_LOW
                new_state = STATE_PROBLEM
            elif float(self.sensor_temperature.state) > float(
                self.max_temperature.state
            ):
                self.temperature_status = STATE_HIGH
                new_state = STATE_PROBLEM
            else:
                self.temperature_status = STATE_OK

        if (
            self.sensor_humidity is not None
            and self.sensor_humidity.state != STATE_UNKNOWN
            and self.sensor_humidity.state != STATE_UNAVAILABLE
            and self.sensor_humidity.state is not None
        ):
            if float(self.sensor_humidity.state) < float(self.min_humidity.state):
                self.humidity_status = STATE_LOW
                new_state = STATE_PROBLEM
            elif float(self.sensor_humidity.state) > float(self.max_humidity.state):
                self.humidity_status = STATE_HIGH
                new_state = STATE_PROBLEM
            else:
                self.humidity_status = STATE_OK

        # Check the instant values for illuminance against "max"

        if (
            self.illuminance_trigger is True
            and self.sensor_illuminance is not None
            and self.sensor_illuminance.state != STATE_UNKNOWN
            and self.sensor_illuminance.state != STATE_UNAVAILABLE
            and self.sensor_illuminance.state is not None
        ):
            if float(self.sensor_illuminance.state) > float(self.max_illuminance.state):
                self.illuminance_status = STATE_HIGH
                new_state = STATE_PROBLEM

        # - Checking Low values would create "problem" every night...
        # Check DLI from the previous day against max/min DLI
        if (
            self.illuminance_trigger is True
            and self.dli is not None
            and self.dli.state != STATE_UNKNOWN
            and self.dli.state != STATE_UNAVAILABLE
            and self.dli.state is not None
        ):
            if float(self.dli.extra_state_attributes["last_period"]) > 0 and float(
                self.dli.extra_state_attributes["last_period"]
            ) < float(self.min_dli.state):
                self.dli_status = STATE_LOW
                new_state = STATE_PROBLEM
            elif float(self.dli.extra_state_attributes["last_period"]) > 0 and float(
                self.dli.extra_state_attributes["last_period"]
            ) > float(self.max_dli.state):
                self.dli_status = STATE_HIGH
                new_state = STATE_PROBLEM
            else:
                self.illuminance_status = STATE_OK

        self._attr_state = new_state
        self.update_registry()

    @property
    def data_source(self) -> str | None:
        """Currently unused. For future use"""
        return None

    def update_registry(self) -> None:
        """Update registry with correct data"""
        # Is there a better way to add an entity to the device registry?

        device_registry = dr.async_get(self._hass)
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
