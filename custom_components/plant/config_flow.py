"""Config flow for Custom Plant integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_DOMAIN,
    ATTR_ENTITY_PICTURE,
    ATTR_NAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import selector

from .const import (
    ATTR_ENTITY,
    ATTR_LIMITS,
    ATTR_OPTIONS,
    ATTR_SELECT,
    ATTR_SENSORS,
    ATTR_SPECIES,
    CONF_MAX_CONDUCTIVITY,
    CONF_MAX_HUMIDITY,
    CONF_MAX_ILLUMINANCE,
    CONF_MAX_MOISTURE,
    CONF_MAX_MOL,
    CONF_MAX_TEMPERATURE,
    CONF_MIN_CONDUCTIVITY,
    CONF_MIN_HUMIDITY,
    CONF_MIN_ILLUMINANCE,
    CONF_MIN_MOISTURE,
    CONF_MIN_MOL,
    CONF_MIN_TEMPERATURE,
    DATA_SOURCE,
    DATA_SOURCE_PLANTBOOK,
    DOMAIN,
    DOMAIN_SENSOR,
    FLOW_ERROR_NOTFOUND,
    FLOW_ILLUMINANCE_TRIGGER,
    FLOW_PLANT_INFO,
    FLOW_PLANT_LIMITS,
    FLOW_RIGHT_PLANT,
    FLOW_SENSOR_CONDUCTIVITY,
    FLOW_SENSOR_HUMIDITY,
    FLOW_SENSOR_ILLUMINANCE,
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_TEMPERATURE,
    FLOW_STRING_DESCRIPTION,
    FLOW_TEMP_UNIT,
    OPB_DISPLAY_PID,
)
from .plant_helpers import PlantHelper

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class PlantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Plants."""

    VERSION = 1

    def __init__(self):
        self.plant_info = {}
        self.error = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_import(self, import_input):
        """Importing config from configuration.yaml"""
        _LOGGER.error(import_input)
        # return FlowResultType.ABORT
        return self.async_create_entry(
            title=import_input[FLOW_PLANT_INFO][ATTR_NAME],
            data=import_input,
        )

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
            errors[ATTR_SPECIES] = self.error
        data_schema = {
            vol.Required(ATTR_NAME, default=self.plant_info.get(ATTR_NAME)): str,
            vol.Required(ATTR_SPECIES, default=self.plant_info.get(ATTR_SPECIES)): str,
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
                    ATTR_DOMAIN: DOMAIN_SENSOR,
                }
            }
        )
        data_schema[FLOW_SENSOR_CONDUCTIVITY] = selector(
            {ATTR_ENTITY: {ATTR_DOMAIN: DOMAIN_SENSOR}}
        )
        data_schema[FLOW_SENSOR_ILLUMINANCE] = selector(
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
            description_placeholders={"opb_search": self.plant_info.get(ATTR_SPECIES)},
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
                self.plant_info[ATTR_SPECIES] = user_input[ATTR_SPECIES]

                # Return the form of the next step
                _LOGGER.info("Plant_info: %s", self.plant_info)
                return await self.async_step_limits()
        ph = PlantHelper(self.hass)
        search_result = await ph.openplantbook_search(
            species=self.plant_info[ATTR_SPECIES]
        )
        if search_result is None:
            return await self.async_step_limits()
        dropdown = []
        for (pid, display_pid) in search_result.items():
            dropdown.append({"label": display_pid, "value": pid})
        _LOGGER.info("Dropdown: %s", dropdown)
        data_schema = {}
        data_schema[ATTR_SPECIES] = selector({ATTR_SELECT: {ATTR_OPTIONS: dropdown}})

        return self.async_show_form(
            step_id="select_species",
            data_schema=vol.Schema(data_schema),
            errors=errors,
            description_placeholders={
                "opb_search": self.plant_info[ATTR_SPECIES],
                FLOW_STRING_DESCRIPTION: "Results from OpenPlantbook",
            },
        )

    async def async_step_limits(self, user_input=None):
        """Handle max/min values"""

        if user_input is not None:
            _LOGGER.info("User Input %s", user_input)
            # Validate user input
            valid = await self.validate_step_1(user_input)
            if not user_input.get(FLOW_RIGHT_PLANT):
                return await self.async_step_select_species()
            if valid:
                self.plant_info[ATTR_ENTITY_PICTURE] = user_input.get[
                    ATTR_ENTITY_PICTURE
                ]
                self.plant_info[OPB_DISPLAY_PID] = user_input.get(OPB_DISPLAY_PID)
                user_input.pop(ATTR_ENTITY_PICTURE)
                user_input.pop(OPB_DISPLAY_PID)
                user_input.pop(FLOW_RIGHT_PLANT)
                self.plant_info[FLOW_PLANT_LIMITS] = user_input
                _LOGGER.info("Plant_info: %s", self.plant_info)
                # Return the form of the next step
                return await self.async_step_limits_done()

        data_schema = {}
        ph = PlantHelper(self.hass)
        plant_config = await ph.generate_configentry(
            config={
                ATTR_NAME: self.plant_info[ATTR_NAME],
                ATTR_SPECIES: self.plant_info[ATTR_SPECIES],
                ATTR_SENSORS: {},
            }
        )

        if plant_config[FLOW_PLANT_INFO].get(OPB_DISPLAY_PID):
            # We got data from OPB.  Display a "wrong plant" switch
            data_schema[vol.Optional(FLOW_RIGHT_PLANT, default=True)] = cv.boolean

        data_schema[
            vol.Required(
                OPB_DISPLAY_PID,
                default=plant_config[FLOW_PLANT_INFO].get(OPB_DISPLAY_PID, ""),
            )
        ] = str
        data_schema[
            vol.Required(
                CONF_MAX_MOISTURE,
                default=plant_config[FLOW_PLANT_INFO][ATTR_LIMITS].get(
                    CONF_MAX_MOISTURE
                ),
            )
        ] = int
        data_schema[
            vol.Required(
                CONF_MIN_MOISTURE,
                default=plant_config[FLOW_PLANT_INFO][ATTR_LIMITS].get(
                    CONF_MIN_MOISTURE
                ),
            )
        ] = int
        data_schema[
            vol.Required(
                CONF_MAX_ILLUMINANCE,
                default=plant_config[FLOW_PLANT_INFO][ATTR_LIMITS].get(
                    CONF_MAX_ILLUMINANCE
                ),
            )
        ] = int
        data_schema[
            vol.Required(
                CONF_MIN_ILLUMINANCE,
                default=plant_config[FLOW_PLANT_INFO][ATTR_LIMITS].get(
                    CONF_MIN_ILLUMINANCE
                ),
            )
        ] = int
        data_schema[
            vol.Required(
                CONF_MAX_MOL,
                default=plant_config[FLOW_PLANT_INFO][ATTR_LIMITS].get(CONF_MAX_MOL),
            )
        ] = int
        data_schema[
            vol.Required(
                CONF_MIN_MOL,
                default=plant_config[FLOW_PLANT_INFO][ATTR_LIMITS].get(CONF_MIN_MOL),
            )
        ] = int
        data_schema[
            vol.Required(
                CONF_MAX_TEMPERATURE,
                default=plant_config[FLOW_PLANT_INFO][ATTR_LIMITS].get(
                    CONF_MAX_TEMPERATURE
                ),
            )
        ] = int
        data_schema[
            vol.Required(
                CONF_MIN_TEMPERATURE,
                default=plant_config[FLOW_PLANT_INFO][ATTR_LIMITS].get(
                    CONF_MIN_TEMPERATURE
                ),
            )
        ] = int
        data_schema[
            vol.Required(
                CONF_MAX_CONDUCTIVITY,
                default=plant_config[FLOW_PLANT_INFO][ATTR_LIMITS].get(
                    CONF_MAX_CONDUCTIVITY
                ),
            )
        ] = int
        data_schema[
            vol.Required(
                CONF_MIN_CONDUCTIVITY,
                default=plant_config[FLOW_PLANT_INFO][ATTR_LIMITS].get(
                    CONF_MIN_CONDUCTIVITY
                ),
            )
        ] = int
        data_schema[
            vol.Required(
                CONF_MAX_HUMIDITY,
                default=plant_config[FLOW_PLANT_INFO][ATTR_LIMITS].get(
                    CONF_MAX_HUMIDITY
                ),
            )
        ] = int
        data_schema[
            vol.Required(
                CONF_MIN_HUMIDITY,
                default=plant_config[FLOW_PLANT_INFO][ATTR_LIMITS].get(
                    CONF_MIN_HUMIDITY
                ),
            )
        ] = int

        data_schema[
            vol.Optional(
                ATTR_ENTITY_PICTURE,
                default=plant_config[FLOW_PLANT_INFO].get(ATTR_ENTITY_PICTURE),
            )
        ] = str

        return self.async_show_form(
            step_id="limits",
            data_schema=vol.Schema(data_schema),
            description_placeholders={
                ATTR_ENTITY_PICTURE: plant_config[FLOW_PLANT_INFO].get(
                    ATTR_ENTITY_PICTURE
                ),
                ATTR_NAME: plant_config[FLOW_PLANT_INFO].get(ATTR_NAME),
                FLOW_TEMP_UNIT: self.hass.config.units.temperature_unit,
            },
        )

    async def async_step_limits_done(self, user_input=None):
        """After limits are set"""
        return self.async_create_entry(
            title=self.plant_info[ATTR_NAME],
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


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handling opetions for plant"""

    def __init__(
        self,
        entry: config_entries.ConfigEntry,
    ) -> None:
        """Initialize options flow."""

        entry.async_on_unload(entry.add_update_listener(self.update_plant_options))

        self.plant = None
        self.entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Manage the options."""
        if user_input is not None:
            _LOGGER.info("User Input: %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        _LOGGER.info(self.entry.data)
        self.plant = self.hass.data[DOMAIN][self.entry.entry_id]["plant"]

        data_schema = {}
        data_schema[
            vol.Required(
                ATTR_SPECIES,
                default=self.plant.species,
            )
        ] = str
        display_species = self.plant.display_species or ""
        data_schema[
            vol.Optional(
                OPB_DISPLAY_PID,
                default=display_species,
            )
        ] = str
        entity_picture = self.plant._attr_entity_picture or ""
        data_schema[vol.Optional(ATTR_ENTITY_PICTURE, default=entity_picture)] = str

        data_schema[
            vol.Optional(
                FLOW_ILLUMINANCE_TRIGGER, default=self.plant.illuminance_trigger
            )
        ] = cv.boolean
        # data_schema[vol.Optional(CONF_CHECK_DAYS, default=self.plant.check_days)] = int

        return self.async_show_form(step_id="init", data_schema=vol.Schema(data_schema))

    async def update_plant_options(
        self, hass: HomeAssistant, entry: config_entries.ConfigEntry
    ):
        """Handle options update."""
        _LOGGER.info("Entry Data %s", entry.options)
        entity_picture = entry.options.get(ATTR_ENTITY_PICTURE)

        if entity_picture is not None:
            if entity_picture == "":
                self.plant.add_image(entity_picture)
            else:
                try:
                    url = cv.url(entity_picture)
                    _LOGGER.info("Url 1 %s", url)
                except Exception as exc1:
                    _LOGGER.warning("Not a valid url: %s", entity_picture)
                    if entity_picture.startswith("/local/"):
                        try:
                            url = cv.path(entity_picture)
                            _LOGGER.info("Url 2 %s", url)
                        except Exception as exc2:
                            _LOGGER.warning("Not a valid path: %s", entity_picture)
                            raise vol.Invalid(
                                f"Invalid URL: {entity_picture}"
                            ) from exc2
                    else:
                        raise vol.Invalid(f"Invalid URL: {entity_picture}") from exc1
                _LOGGER.info("Update image to %s", entity_picture)
                self.plant.add_image(entity_picture)

        new_display_species = entry.options.get(OPB_DISPLAY_PID)
        if new_display_species is not None:
            self.plant.display_species = new_display_species

        new_species = entry.options.get(ATTR_SPECIES)
        if new_species and new_species != self.plant.species:
            _LOGGER.info(
                "Species changed from '%s' to '%s'", self.plant.species, new_species
            )
            ph = PlantHelper(hass=self.hass)
            plant_config = await ph.generate_configentry(
                config={ATTR_SPECIES: new_species}
            )
            if plant_config[DATA_SOURCE] == DATA_SOURCE_PLANTBOOK:
                _LOGGER.info(plant_config)
                self.plant.species = new_species
                self.plant.add_image(plant_config[FLOW_PLANT_INFO][ATTR_ENTITY_PICTURE])
                self.plant.display_species = plant_config[FLOW_PLANT_INFO][
                    OPB_DISPLAY_PID
                ]
                for (key, value) in plant_config[FLOW_PLANT_INFO][
                    FLOW_PLANT_LIMITS
                ].items():
                    set_entity = getattr(self.plant, key)
                    _LOGGER.info("Entity: %s To: %s", set_entity, value)
                    set_entity_id = set_entity.entity_id
                    _LOGGER.info(
                        "Setting %s to %s",
                        set_entity_id,
                        value,
                    )
                    self.hass.states.async_set(set_entity_id, value)

            else:
                self.plant.species = new_species

        self.plant.update_registry()
