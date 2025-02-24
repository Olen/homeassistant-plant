"""Helper functions for the plant integration"""

from __future__ import annotations

import logging
from typing import Any

from async_timeout import timeout
import voluptuous as vol

from homeassistant.components.persistent_notification import (
    create as create_notification,
)
from homeassistant.const import ATTR_ENTITY_PICTURE, ATTR_NAME, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.temperature import display_temp

from .const import (
    ATTR_BRIGHTNESS,
    ATTR_CONDUCTIVITY,
    ATTR_ILLUMINANCE,
    ATTR_IMAGE,
    ATTR_LIMITS,
    ATTR_MOISTURE,
    ATTR_SENSORS,
    ATTR_SPECIES,
    ATTR_TEMPERATURE,
    CONF_MAX_BRIGHTNESS,
    CONF_MAX_CONDUCTIVITY,
    CONF_MAX_DLI,
    CONF_MAX_HUMIDITY,
    CONF_MAX_ILLUMINANCE,
    CONF_MAX_MMOL,
    CONF_MAX_MOISTURE,
    CONF_MAX_TEMPERATURE,
    CONF_MIN_BRIGHTNESS,
    CONF_MIN_CONDUCTIVITY,
    CONF_MIN_DLI,
    CONF_MIN_HUMIDITY,
    CONF_MIN_ILLUMINANCE,
    CONF_MIN_MMOL,
    CONF_MIN_MOISTURE,
    CONF_MIN_TEMPERATURE,
    CONF_PLANTBOOK_MAPPING,
    DATA_SOURCE,
    DATA_SOURCE_DEFAULT,
    DATA_SOURCE_PLANTBOOK,
    DEFAULT_IMAGE_LOCAL_URL,
    DEFAULT_IMAGE_PATH,
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
    DOMAIN_PLANTBOOK,
    FLOW_FORCE_SPECIES_UPDATE,
    FLOW_PLANT_IMAGE,
    FLOW_PLANT_INFO,
    FLOW_SENSOR_CONDUCTIVITY,
    FLOW_SENSOR_ILLUMINANCE,
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_TEMPERATURE,
    OPB_DISPLAY_PID,
    OPB_GET,
    OPB_SEARCH,
    PPFD_DLI_FACTOR,
    REQUEST_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class PlantHelper:
    """Helper functions for the plant integration"""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    @property
    def has_openplantbook(self) -> bool:
        """Helper function to check if openplantbook is available"""
        _LOGGER.debug(
            "%s in services? %s",
            DOMAIN_PLANTBOOK,
            DOMAIN_PLANTBOOK in self.hass.services.async_services(),
        )
        return DOMAIN_PLANTBOOK in self.hass.services.async_services()

    async def openplantbook_search(self, species: str) -> dict[str:Any] | None:
        """Search OPB and return list of result"""

        if not self.has_openplantbook:
            return None
        if not species or species == "":
            return None

        try:
            async with timeout(REQUEST_TIMEOUT):
                plant_search_result = await self.hass.services.async_call(
                    domain=DOMAIN_PLANTBOOK,
                    service=OPB_SEARCH,
                    service_data={"alias": species},
                    blocking=True,
                    return_response=True,
                )
        except TimeoutError:
            _LOGGER.warning("Openplantbook request timed out")
            return None
        except Exception as ex:
            _LOGGER.warning("Openplantbook does not work, error: %s", ex)
            return None
        if bool(plant_search_result):
            _LOGGER.info("Result: %s", plant_search_result)

            return plant_search_result
        return None

    async def openplantbook_get(self, species: str) -> dict[str:Any] | None:
        """Get information about a plant species from OpenPlantbook"""
        if not self.has_openplantbook:
            return None
        if not species or species == "":
            return None

        try:
            async with timeout(REQUEST_TIMEOUT):
                plant_get_result = await self.hass.services.async_call(
                    domain=DOMAIN_PLANTBOOK,
                    service=OPB_GET,
                    service_data={ATTR_SPECIES: species.lower()},
                    blocking=True,
                    return_response=True,
                )
        except TimeoutError:
            _LOGGER.warning("Openplantook request timed out")
        except Exception as ex:
            _LOGGER.warning("Openplantook does not work, error: %s", ex)
            return None
        if bool(plant_get_result):
            _LOGGER.debug("Result for %s: %s", species, plant_get_result)
            return plant_get_result

        _LOGGER.info("Did not find '%s' in OpenPlantbook", species)
        create_notification(
            hass=self.hass,
            title="Species not found",
            message=f"Could not find «{species}» in OpenPlantbook.",
        )
        return None

    async def generate_configentry(self, config: dict) -> dict[str:Any]:
        """Generates a config-entry dict from current data and/or OPB"""

        max_moisture = DEFAULT_MAX_MOISTURE
        min_moisture = DEFAULT_MIN_MOISTURE
        max_light_lx = DEFAULT_MAX_ILLUMINANCE
        min_light_lx = DEFAULT_MIN_ILLUMINANCE
        max_temp = display_temp(
            self.hass,
            DEFAULT_MAX_TEMPERATURE,
            UnitOfTemperature.CELSIUS,
            0,
        )
        min_temp = display_temp(
            self.hass,
            DEFAULT_MIN_TEMPERATURE,
            UnitOfTemperature.CELSIUS,
            0,
        )
        max_conductivity = DEFAULT_MAX_CONDUCTIVITY
        min_conductivity = DEFAULT_MIN_CONDUCTIVITY
        max_dli = DEFAULT_MAX_DLI
        min_dli = DEFAULT_MIN_DLI
        max_humidity = DEFAULT_MAX_HUMIDITY
        min_humidity = DEFAULT_MIN_HUMIDITY
        entity_picture = None
        display_species = None
        data_source = DATA_SOURCE_DEFAULT

        # If we have image defined in the config, or a local file
        # prefer that.  If neither, image will be set to openplantbook
        jpeg_exists = None
        png_exists = None

        if ATTR_SPECIES in config:
            try:
                jpeg_exists = cv.isfile(
                    f"{DEFAULT_IMAGE_PATH}{config[ATTR_SPECIES]}.jpg"
                )
            except vol.Invalid:
                jpeg_exists = None
            try:
                png_exists = cv.isfile(
                    f"{DEFAULT_IMAGE_PATH}{config[ATTR_SPECIES]}.png"
                )
            except vol.Invalid:
                png_exists = None

        if ATTR_ENTITY_PICTURE in config:
            entity_picture = config[ATTR_ENTITY_PICTURE]
        elif ATTR_IMAGE in config and config[ATTR_IMAGE] != DOMAIN_PLANTBOOK:
            entity_picture = config[ATTR_IMAGE]
        elif jpeg_exists:
            entity_picture = f"{DEFAULT_IMAGE_LOCAL_URL}{config[ATTR_SPECIES]}.jpg"
        elif png_exists:
            entity_picture = f"{DEFAULT_IMAGE_LOCAL_URL}{config[ATTR_SPECIES]}.png"

        if ATTR_SENSORS not in config:
            config[ATTR_SENSORS] = {}

        if config.get(OPB_DISPLAY_PID, "") == "":
            config[OPB_DISPLAY_PID] = None
        opb_plant = await self.openplantbook_get(config.get(ATTR_SPECIES))
        if opb_plant:
            data_source = DATA_SOURCE_PLANTBOOK
            max_moisture = opb_plant.get(
                CONF_PLANTBOOK_MAPPING[CONF_MAX_MOISTURE], DEFAULT_MAX_MOISTURE
            )
            min_moisture = opb_plant.get(
                CONF_PLANTBOOK_MAPPING[CONF_MIN_MOISTURE], DEFAULT_MIN_MOISTURE
            )
            max_light_lx = opb_plant.get(
                CONF_PLANTBOOK_MAPPING[CONF_MAX_ILLUMINANCE],
                DEFAULT_MAX_ILLUMINANCE,
            )
            min_light_lx = opb_plant.get(
                CONF_PLANTBOOK_MAPPING[CONF_MIN_ILLUMINANCE],
                DEFAULT_MIN_ILLUMINANCE,
            )
            max_temp = display_temp(
                self.hass,
                opb_plant.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MAX_TEMPERATURE],
                    DEFAULT_MAX_TEMPERATURE,
                ),
                UnitOfTemperature.CELSIUS,
                0,
            )
            min_temp = display_temp(
                self.hass,
                opb_plant.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MIN_TEMPERATURE],
                    DEFAULT_MIN_TEMPERATURE,
                ),
                UnitOfTemperature.CELSIUS,
                0,
            )
            opb_mmol = opb_plant.get(CONF_PLANTBOOK_MAPPING[CONF_MAX_MMOL])
            if opb_mmol:
                max_dli = round(opb_mmol * PPFD_DLI_FACTOR)
            else:
                max_dli = DEFAULT_MAX_DLI
            opb_mmol = opb_plant.get(CONF_PLANTBOOK_MAPPING[CONF_MIN_MMOL])
            if opb_mmol:
                min_dli = round(opb_mmol * PPFD_DLI_FACTOR)
            else:
                min_dli = DEFAULT_MIN_DLI
            max_conductivity = opb_plant.get(
                CONF_PLANTBOOK_MAPPING[CONF_MAX_CONDUCTIVITY],
                DEFAULT_MAX_CONDUCTIVITY,
            )
            min_conductivity = opb_plant.get(
                CONF_PLANTBOOK_MAPPING[CONF_MIN_CONDUCTIVITY],
                DEFAULT_MIN_CONDUCTIVITY,
            )
            max_humidity = opb_plant.get(
                CONF_PLANTBOOK_MAPPING[CONF_MAX_HUMIDITY], DEFAULT_MAX_HUMIDITY
            )
            min_humidity = opb_plant.get(
                CONF_PLANTBOOK_MAPPING[CONF_MIN_HUMIDITY], DEFAULT_MIN_HUMIDITY
            )
            _LOGGER.info("Picture: %s", entity_picture)
            if (
                entity_picture is None
                or entity_picture == ""
                or "plantbook.io" in entity_picture
                or (
                    FLOW_FORCE_SPECIES_UPDATE in config
                    and config[FLOW_FORCE_SPECIES_UPDATE] is True
                )
            ):
                entity_picture = opb_plant.get(FLOW_PLANT_IMAGE)
            if (
                FLOW_FORCE_SPECIES_UPDATE in config
                and config[FLOW_FORCE_SPECIES_UPDATE] is True
            ):
                display_species = opb_plant.get(OPB_DISPLAY_PID, "")
            else:
                _LOGGER.debug(
                    "Setting display_pid to %s",
                    config.get(OPB_DISPLAY_PID) or opb_plant.get(OPB_DISPLAY_PID, ""),
                )
                display_species = config.get(OPB_DISPLAY_PID) or opb_plant.get(
                    OPB_DISPLAY_PID, ""
                )

        _LOGGER.debug("Parsing input config: %s", config)
        _LOGGER.debug("Display pid: %s", display_species)

        ret = {
            DATA_SOURCE: data_source,
            FLOW_PLANT_INFO: {
                ATTR_NAME: config.get(ATTR_NAME),
                ATTR_SPECIES: config.get(ATTR_SPECIES) or "",
                ATTR_ENTITY_PICTURE: entity_picture or "",
                OPB_DISPLAY_PID: display_species or "",
                ATTR_LIMITS: {
                    CONF_MAX_ILLUMINANCE: config.get(
                        CONF_MAX_BRIGHTNESS,
                        config.get(CONF_MAX_ILLUMINANCE, max_light_lx),
                    ),
                    CONF_MIN_ILLUMINANCE: config.get(
                        CONF_MIN_BRIGHTNESS,
                        config.get(CONF_MIN_ILLUMINANCE, min_light_lx),
                    ),
                    CONF_MAX_CONDUCTIVITY: config.get(
                        CONF_MAX_CONDUCTIVITY, max_conductivity
                    ),
                    CONF_MIN_CONDUCTIVITY: config.get(
                        CONF_MIN_CONDUCTIVITY, min_conductivity
                    ),
                    CONF_MAX_MOISTURE: config.get(CONF_MAX_MOISTURE, max_moisture),
                    CONF_MIN_MOISTURE: config.get(CONF_MIN_MOISTURE, min_moisture),
                    CONF_MAX_TEMPERATURE: config.get(CONF_MAX_TEMPERATURE, max_temp),
                    CONF_MIN_TEMPERATURE: config.get(CONF_MIN_TEMPERATURE, min_temp),
                    CONF_MAX_HUMIDITY: config.get(CONF_MAX_HUMIDITY, max_humidity),
                    CONF_MIN_HUMIDITY: config.get(CONF_MIN_HUMIDITY, min_humidity),
                    CONF_MAX_DLI: config.get(CONF_MAX_DLI, max_dli),
                    CONF_MIN_DLI: config.get(CONF_MIN_DLI, min_dli),
                },
                FLOW_SENSOR_TEMPERATURE: config[ATTR_SENSORS].get(ATTR_TEMPERATURE),
                FLOW_SENSOR_MOISTURE: config[ATTR_SENSORS].get(ATTR_MOISTURE),
                FLOW_SENSOR_CONDUCTIVITY: config[ATTR_SENSORS].get(ATTR_CONDUCTIVITY),
                FLOW_SENSOR_ILLUMINANCE: config[ATTR_SENSORS].get(ATTR_ILLUMINANCE)
                or config[ATTR_SENSORS].get(ATTR_BRIGHTNESS),
            },
        }
        _LOGGER.debug("Resulting config: %s", ret)
        return ret
