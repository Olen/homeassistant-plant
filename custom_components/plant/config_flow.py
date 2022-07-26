"""Config flow for Custom Plant integration."""

import logging

import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.sensor import (
    DEVICE_CLASSES,
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_DOMAIN, ATTR_ENTITY_PICTURE
from homeassistant.helpers.selector import selector

from .const import (
    CONF_CHECK_DAYS,
    CONF_IMAGE,
    CONF_MAX_BRIGHTNESS,
    CONF_MAX_CONDUCTIVITY,
    CONF_MAX_HUMIDITY,
    CONF_MAX_MOISTURE,
    CONF_MAX_TEMPERATURE,
    CONF_MIN_BATTERY_LEVEL,
    CONF_MIN_BRIGHTNESS,
    CONF_MIN_CONDUCTIVITY,
    CONF_MIN_HUMIDITY,
    CONF_MIN_MOISTURE,
    CONF_MIN_TEMPERATURE,
    CONF_PLANTBOOK,
    CONF_PLANTBOOK_MAPPING,
    CONF_SPECIES,
    DOMAIN,
    FLOW_PLANT_IMAGE,
    FLOW_PLANT_INFO,
    FLOW_PLANT_LIMITS,
    FLOW_PLANT_NAME,
    FLOW_PLANT_SPECIES,
    FLOW_SENSOR_BRIGHTNESS,
    FLOW_SENSOR_CONDUCTIVITY,
    FLOW_SENSOR_HUMIDITY,
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_TEMPERATURE,
    OPB_DISPLAY_PID,
    OPB_PID,
    OPB_SEARCH,
    OPB_SEARCH_RESULT,
    READING_BATTERY,
    READING_BRIGHTNESS,
    READING_CONDUCTIVITY,
    READING_MOISTURE,
    READING_TEMPERATURE,
)

FLOW_WRONG_PLANT = "wrong_plant"
FLOW_ERROR_NOTFOUND = "opb_notfound"
FLOW_STRING_DESCRIPTION = "desc"

ATTR_ENTITY = "entity"
ATTR_SELECT = "select"
ATTR_OPTIONS = "options"
DOMAIN_SENSOR = "sensor"
DOMAIN_PLANTBOOK = "openplantbook"


_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class PlantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Plants."""

    VERSION = 1

    def __init__(self):
        self.plant_info = {}
        self.error = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            _LOGGER.info("User Input %s", user_input)
            # Validate user input
            valid = await self.validate_step_1(user_input)
            if valid:
                # Store info to use in next step
                self.plant_info = user_input
                _LOGGER.info("Plant_info: %s", self.plant_info)

                # Return the form of the next step
                return await self.async_step_select_species()

        # Specify items in the order they are to be displayed in the UI
        if self.error == FLOW_ERROR_NOTFOUND:
            errors[FLOW_PLANT_SPECIES] = self.error
        data_schema = {
            vol.Required(
                FLOW_PLANT_NAME, default=self.plant_info.get(FLOW_PLANT_NAME)
            ): str,
            vol.Required(
                FLOW_PLANT_SPECIES, default=self.plant_info.get(FLOW_PLANT_SPECIES)
            ): str,
        }
        data_schema[FLOW_SENSOR_TEMPERATURE] = selector(
            {
                ATTR_ENTITY: {
                    ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                    ATTR_DOMAIN: DOMAIN_SENSOR,
                }
            }
        )
        data_schema[FLOW_SENSOR_MOISTURE] = selector(
            {
                ATTR_ENTITY: {
                    ATTR_DEVICE_CLASS: SensorDeviceClass.HUMIDITY,
                    ATTR_DOMAIN: "sensor",
                }
            }
        )
        data_schema[FLOW_SENSOR_CONDUCTIVITY] = selector(
            {ATTR_ENTITY: {ATTR_DOMAIN: DOMAIN_SENSOR}}
        )
        data_schema[FLOW_SENSOR_BRIGHTNESS] = selector(
            {
                ATTR_ENTITY: {
                    ATTR_DEVICE_CLASS: SensorDeviceClass.ILLUMINANCE,
                    ATTR_DOMAIN: DOMAIN_SENSOR,
                }
            }
        )
        data_schema[FLOW_SENSOR_HUMIDITY] = selector(
            {
                ATTR_ENTITY: {
                    ATTR_DEVICE_CLASS: SensorDeviceClass.HUMIDITY,
                    ATTR_DOMAIN: DOMAIN_SENSOR,
                }
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(data_schema),
            errors=errors,
            description_placeholders={
                "opb_search": self.plant_info.get(FLOW_PLANT_SPECIES)
            },
        )

    async def async_step_select_species(self, user_input=None):
        """Search the openplantbook"""
        errors = {}

        if user_input is not None:
            _LOGGER.info("User Input %s", user_input)
            # Validate user input
            valid = await self.validate_step_2(user_input)
            if valid:
                # Store info to use in next step
                self.plant_info[FLOW_PLANT_SPECIES] = user_input[FLOW_PLANT_SPECIES]

                # Return the form of the next step
                _LOGGER.info("Plant_info: %s", self.plant_info)
                return await self.async_step_limits()

        data_schema = {}
        if not DOMAIN_PLANTBOOK in self.hass.services.async_services():
            return await self.async_step_limits()

        _LOGGER.info("OPB in services")
        try:
            plant_search = await self.hass.services.async_call(
                domain=DOMAIN_PLANTBOOK,
                service=OPB_SEARCH,
                service_data={"alias": self.plant_info[FLOW_PLANT_SPECIES]},
                blocking=True,
                limit=30,
            )
        except KeyError:
            _LOGGER.warning("Openplantook does not work")
            return await self.async_step_limits()
        if plant_search:
            _LOGGER.info(
                "Result: %s",
                self.hass.states.get(f"{DOMAIN_PLANTBOOK}.{OPB_SEARCH_RESULT}"),
            )
            dropdown = list(
                self.hass.states.get(
                    f"{DOMAIN_PLANTBOOK}.{OPB_SEARCH_RESULT}"
                ).attributes.keys()
            )
            _LOGGER.info(dropdown)
            if len(dropdown) == 0:
                _LOGGER.info("Nothing found")
                self.error = FLOW_ERROR_NOTFOUND
                # self.error = f"Could not find '{self.plant_info['plant_species']}' in OpenPlantbook"

                return await self.async_step_user()

            data_schema[FLOW_PLANT_SPECIES] = selector(
                {ATTR_SELECT: {ATTR_OPTIONS: dropdown}}
            )
        else:
            _LOGGER.info("Found nothing...")
            self.error = FLOW_ERROR_NOTFOUND
            # self.error = f"Could not find '{self.plant_info['plant_species']}' in OpenPlantbook"
            return await self.async_step_user()

        return self.async_show_form(
            step_id="select_species",
            data_schema=vol.Schema(data_schema),
            errors=errors,
            description_placeholders={
                "opb_search": self.plant_info[FLOW_PLANT_SPECIES],
                FLOW_STRING_DESCRIPTION: "Results from OpenPlantbook",
            },
        )

    async def async_step_limits(self, user_input=None):
        """Handle max/min values"""

        if user_input is not None:
            _LOGGER.info("User Input %s", user_input)
            # Validate user input
            valid = await self.validate_step_1(user_input)
            if user_input.get(FLOW_WRONG_PLANT):
                return await self.async_step_select_species()
            if valid:
                # Store info to use in next step
                self.plant_info[FLOW_PLANT_LIMITS] = user_input
                _LOGGER.info("Plant_info: %s", self.plant_info)
                # Return the form of the next step
                return await self.async_step_limits_done()

        data_schema = {}
        max_moisture = 0
        min_moisture = 0
        max_light_lx = 0
        min_light_lx = 0
        max_temp = 0
        min_temp = 0
        max_conductivity = 0
        min_condictivity = 0
        opb_image = None
        # opb_species = None
        opb_name = self.plant_info[FLOW_PLANT_NAME]
        _LOGGER.info("User input: %s", user_input)

        if DOMAIN_PLANTBOOK in self.hass.services.async_services():
            logging.info("opb in services")
            plant_get = await self.hass.services.async_call(
                domain=DOMAIN_PLANTBOOK,
                service="get",
                service_data={"species": self.plant_info[FLOW_PLANT_SPECIES]},
                blocking=True,
                limit=30,
            )
            if plant_get:
                opb_plant = self.hass.states.get(
                    f"{DOMAIN_PLANTBOOK}."
                    + self.plant_info[FLOW_PLANT_SPECIES]
                    .replace("'", "")
                    .replace(" ", "_")
                )

                _LOGGER.info("Result: %s", opb_plant)
                _LOGGER.info("Result A: %s", opb_plant.attributes)

                max_moisture = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MAX_MOISTURE]
                )
                min_moisture = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MIN_MOISTURE]
                )
                max_light_lx = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MAX_BRIGHTNESS]
                )
                min_light_lx = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MIN_BRIGHTNESS]
                )
                max_temp = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MAX_TEMPERATURE]
                )
                min_temp = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MIN_TEMPERATURE]
                )
                max_conductivity = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MAX_CONDUCTIVITY]
                )
                min_condictivity = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MIN_CONDUCTIVITY]
                )
                max_humidity = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MAX_HUMIDITY]
                )
                min_humidity = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MIN_HUMIDITY]
                )

                opb_image = opb_plant.attributes.get(FLOW_PLANT_IMAGE)
                opb_name = opb_plant.attributes.get(OPB_DISPLAY_PID)

                data_schema[FLOW_WRONG_PLANT] = selector({"boolean": {}})
        data_schema[vol.Required(OPB_DISPLAY_PID, default=opb_name)] = str
        data_schema[vol.Required(CONF_MAX_MOISTURE, default=max_moisture)] = int
        data_schema[vol.Required(CONF_MIN_MOISTURE, default=min_moisture)] = int
        data_schema[vol.Required(CONF_MAX_BRIGHTNESS, default=max_light_lx)] = int
        data_schema[vol.Required(CONF_MIN_BRIGHTNESS, default=min_light_lx)] = int
        data_schema[vol.Required(CONF_MAX_TEMPERATURE, default=max_temp)] = int
        data_schema[vol.Required(CONF_MIN_TEMPERATURE, default=min_temp)] = int
        data_schema[vol.Required(CONF_MAX_CONDUCTIVITY, default=max_conductivity)] = int
        data_schema[vol.Required(CONF_MIN_CONDUCTIVITY, default=min_condictivity)] = int
        data_schema[vol.Required(CONF_MAX_HUMIDITY, default=max_humidity)] = int
        data_schema[vol.Required(CONF_MIN_HUMIDITY, default=min_humidity)] = int

        data_schema[vol.Optional(ATTR_ENTITY_PICTURE, default=opb_image)] = str

        return self.async_show_form(
            step_id="limits",
            data_schema=vol.Schema(data_schema),
            description_placeholders={
                ATTR_ENTITY_PICTURE: opb_image,
                FLOW_PLANT_NAME: opb_name,
            },
        )

    async def async_step_limits_done(self, user_input=None):
        """After limits are set"""
        return self.async_create_entry(
            title=self.plant_info[FLOW_PLANT_NAME],
            data={FLOW_PLANT_INFO: self.plant_info},
        )

    async def validate_step_1(self, user_input):
        """Validate step one"""
        return True

    async def validate_step_2(self, user_input):
        """Validate step two"""
        return True

    async def validate_step_3(self, user_input):
        """Validate step three"""
        return True

    async def validate_step_4(self, user_input):
        """Validate step four"""
        return True
