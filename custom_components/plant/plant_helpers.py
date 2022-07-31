"""Helper functions for the plant integration"""
from __future__ import annotations

import logging
from typing import Any

from slugify import slugify

from homeassistant.components.persistent_notification import (
    create as create_notification,
)
from homeassistant.const import ATTR_ENTITY_PICTURE, ATTR_NAME, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.temperature import display_temp

from .const import (
    ATTR_IMAGE,
    ATTR_LIMITS,
    ATTR_SENSORS,
    ATTR_SPECIES,
    CONF_MAX_CONDUCTIVITY,
    CONF_MAX_HUMIDITY,
    CONF_MAX_ILLUMINANCE,
    CONF_MAX_MMOL,
    CONF_MAX_MOISTURE,
    CONF_MAX_MOL,
    CONF_MAX_TEMPERATURE,
    CONF_MIN_CONDUCTIVITY,
    CONF_MIN_HUMIDITY,
    CONF_MIN_ILLUMINANCE,
    CONF_MIN_MMOL,
    CONF_MIN_MOISTURE,
    CONF_MIN_MOL,
    CONF_MIN_TEMPERATURE,
    CONF_PLANTBOOK_MAPPING,
    DATA_SOURCE,
    DATA_SOURCE_DEFAULT,
    DATA_SOURCE_PLANTBOOK,
    DEFAULT_MAX_CONDUCTIVITY,
    DEFAULT_MAX_HUMIDITY,
    DEFAULT_MAX_ILLUMINANCE,
    DEFAULT_MAX_MOISTURE,
    DEFAULT_MAX_MOL,
    DEFAULT_MAX_TEMPERATURE,
    DEFAULT_MIN_CONDUCTIVITY,
    DEFAULT_MIN_HUMIDITY,
    DEFAULT_MIN_ILLUMINANCE,
    DEFAULT_MIN_MOISTURE,
    DEFAULT_MIN_MOL,
    DEFAULT_MIN_TEMPERATURE,
    DOMAIN_PLANTBOOK,
    FLOW_PLANT_IMAGE,
    FLOW_PLANT_INFO,
    FLOW_SENSOR_CONDUCTIVITY,
    FLOW_SENSOR_ILLUMINANCE,
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_TEMPERATURE,
    OPB_DISPLAY_PID,
    OPB_GET,
    OPB_SEARCH,
    OPB_SEARCH_RESULT,
    PPFD_DLI_FACTOR,
    READING_CONDUCTIVITY,
    READING_MOISTURE,
    READING_TEMPERATURE,
)

_LOGGER = logging.getLogger(__name__)


class PlantHelper:
    """Helper functions for the plant integration"""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def openplantbook_search(self, species: str) -> dict[str:Any] | None:
        """Search OPB and return list of result"""

        if not DOMAIN_PLANTBOOK in self.hass.services.async_services():
            _LOGGER.info("%s not in services", DOMAIN_PLANTBOOK)
            return None

        try:
            plant_search = await self.hass.services.async_call(
                domain=DOMAIN_PLANTBOOK,
                service=OPB_SEARCH,
                service_data={"alias": species},
                blocking=True,
                limit=30,
            )
        except KeyError:
            _LOGGER.warning("Openplantook does not work")
            return None
        if plant_search:
            _LOGGER.info(
                "Result: %s",
                self.hass.states.get(f"{DOMAIN_PLANTBOOK}.{OPB_SEARCH_RESULT}"),
            )
            return self.hass.states.get(
                f"{DOMAIN_PLANTBOOK}.{OPB_SEARCH_RESULT}"
            ).attributes
        return None

    async def openplantbook_get(self, species: str) -> dict[str:Any] | None:
        """Get information about a plant species from OpenPlantbook"""
        if not DOMAIN_PLANTBOOK in self.hass.services.async_services():
            _LOGGER.info("%s not in services", DOMAIN_PLANTBOOK)
            return None

        plant_get = await self.hass.services.async_call(
            domain=DOMAIN_PLANTBOOK,
            service=OPB_GET,
            service_data={ATTR_SPECIES: species.lower()},
            blocking=True,
            limit=30,
        )
        if plant_get:
            opb_plant = self.hass.states.get(
                f"{DOMAIN_PLANTBOOK}.{slugify(species, separator='_')}"
            )
            _LOGGER.debug("Result for %s: %s", species, opb_plant)
            if opb_plant is not None:
                return opb_plant.attributes

        _LOGGER.info("Did not find '%s' in OpenPlantbook", species)
        create_notification(
            hass=self.hass,
            title="Species not found",
            message=f"Could not find «{species}» in OpenPlantbook.",
        )
        return None

    async def generate_configentry(self, config) -> dict[str:Any]:
        """Generates a config-entry dict from current data and/or OPB"""

        max_moisture = DEFAULT_MAX_MOISTURE
        min_moisture = DEFAULT_MIN_MOISTURE
        max_light_lx = DEFAULT_MAX_ILLUMINANCE
        min_light_lx = DEFAULT_MIN_ILLUMINANCE
        max_temp = display_temp(
            self.hass,
            DEFAULT_MAX_TEMPERATURE,
            TEMP_CELSIUS,
            0,
        )
        min_temp = display_temp(
            self.hass,
            DEFAULT_MIN_TEMPERATURE,
            TEMP_CELSIUS,
            0,
        )
        max_conductivity = DEFAULT_MAX_CONDUCTIVITY
        min_conductivity = DEFAULT_MIN_CONDUCTIVITY
        max_mol = DEFAULT_MAX_MOL
        min_mol = DEFAULT_MIN_MOL
        max_humidity = DEFAULT_MAX_HUMIDITY
        min_humidity = DEFAULT_MIN_HUMIDITY
        entity_picture = None
        display_species = None
        data_source = DATA_SOURCE_DEFAULT

        if ATTR_SENSORS not in config:
            config[ATTR_SENSORS] = {}

        opb_plant = await self.openplantbook_get(config["species"])
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
                TEMP_CELSIUS,
                0,
            )
            min_temp = display_temp(
                self.hass,
                opb_plant.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MIN_TEMPERATURE],
                    DEFAULT_MIN_TEMPERATURE,
                ),
                TEMP_CELSIUS,
                0,
            )
            opb_mmol = opb_plant.get(CONF_PLANTBOOK_MAPPING[CONF_MAX_MMOL])
            if opb_mmol:
                max_mol = round(opb_mmol * PPFD_DLI_FACTOR)
            else:
                max_mol = DEFAULT_MAX_MOL
            opb_mmol = opb_plant.get(CONF_PLANTBOOK_MAPPING[CONF_MIN_MMOL])
            if opb_mmol:
                min_mol = round(opb_mmol * PPFD_DLI_FACTOR)
            else:
                min_mol = DEFAULT_MIN_MOL
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
            entity_picture = opb_plant.get(FLOW_PLANT_IMAGE)
            display_species = opb_plant.get(OPB_DISPLAY_PID)

        return {
            DATA_SOURCE: data_source,
            FLOW_PLANT_INFO: {
                ATTR_NAME: config.get(ATTR_NAME),
                ATTR_SPECIES: config[ATTR_SPECIES],
                ATTR_ENTITY_PICTURE: config.get(
                    ATTR_ENTITY_PICTURE, config.get(ATTR_IMAGE, entity_picture)
                )
                or "",
                OPB_DISPLAY_PID: display_species or "",
                ATTR_LIMITS: {
                    CONF_MAX_ILLUMINANCE: config.get(
                        CONF_MAX_ILLUMINANCE, max_light_lx
                    ),
                    CONF_MIN_ILLUMINANCE: config.get(
                        CONF_MIN_ILLUMINANCE, min_light_lx
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
                    CONF_MAX_MOL: config.get(CONF_MAX_MOL, max_mol),
                    CONF_MIN_MOL: config.get(CONF_MIN_MOL, min_mol),
                },
                FLOW_SENSOR_TEMPERATURE: config[ATTR_SENSORS].get(READING_TEMPERATURE),
                FLOW_SENSOR_MOISTURE: config[ATTR_SENSORS].get(READING_MOISTURE),
                FLOW_SENSOR_CONDUCTIVITY: config[ATTR_SENSORS].get(
                    READING_CONDUCTIVITY
                ),
                FLOW_SENSOR_ILLUMINANCE: config[ATTR_SENSORS].get("brightness"),
            },
        }
