"""Config flow for Custom Plant integration."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from config.custom_components import plant
from config.custom_components.plant import (
    DEFAULT_CHECK_DAYS,
    DEFAULT_MAX_CONDUCTIVITY,
    DEFAULT_MAX_HUMIDITY,
    DEFAULT_MAX_ILLUMINANCE,
    DEFAULT_MAX_MMOL,
    DEFAULT_MAX_MOISTURE,
    DEFAULT_MAX_MOL,
    DEFAULT_MAX_TEMPERATURE,
    DEFAULT_MIN_CONDUCTIVITY,
    DEFAULT_MIN_HUMIDITY,
    DEFAULT_MIN_ILLUMINANCE,
    DEFAULT_MIN_MMOL,
    DEFAULT_MIN_MOISTURE,
    DEFAULT_MIN_MOL,
    DEFAULT_MIN_TEMPERATURE,
)
from homeassistant import config_entries, data_entry_flow
from homeassistant.components.sensor import (
    DEVICE_CLASSES,
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_DOMAIN,
    ATTR_ENTITY_PICTURE,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import selector
from homeassistant.helpers.temperature import display_temp

from .const import (
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
    OPB_SEARCH,
    OPB_SEARCH_RESULT,
    PPFD_DLI_FACTOR,
    READING_BATTERY,
    READING_CONDUCTIVITY,
    READING_ILLUMINANCE,
    READING_MOISTURE,
    READING_TEMPERATURE,
)

FLOW_WRONG_PLANT = "wrong_plant"
FLOW_RIGHT_PLANT = "right_plant"
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

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

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
            _LOGGER.info("Found nothing")
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
            if not user_input.get(FLOW_RIGHT_PLANT):
                return await self.async_step_select_species()
            if valid:

                self.plant_info[FLOW_PLANT_LIMITS] = user_input
                _LOGGER.info("Plant_info: %s", self.plant_info)
                # Return the form of the next step
                return await self.async_step_limits_done()

        data_schema = {}
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
        min_condictivity = DEFAULT_MIN_CONDUCTIVITY
        max_mol = DEFAULT_MAX_MOL
        min_mol = DEFAULT_MIN_MOL
        max_humidity = DEFAULT_MAX_HUMIDITY
        min_humidity = DEFAULT_MIN_HUMIDITY

        opb_image = ""
        # opb_species = None
        opb_name = self.plant_info[FLOW_PLANT_SPECIES]
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
                    CONF_PLANTBOOK_MAPPING[CONF_MAX_MOISTURE], DEFAULT_MAX_MOISTURE
                )
                min_moisture = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MIN_MOISTURE], DEFAULT_MIN_MOISTURE
                )
                max_light_lx = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MAX_ILLUMINANCE],
                    DEFAULT_MAX_ILLUMINANCE,
                )
                min_light_lx = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MIN_ILLUMINANCE],
                    DEFAULT_MIN_ILLUMINANCE,
                )
                max_temp = display_temp(
                    self.hass,
                    opb_plant.attributes.get(
                        CONF_PLANTBOOK_MAPPING[CONF_MAX_TEMPERATURE],
                        DEFAULT_MAX_TEMPERATURE,
                    ),
                    TEMP_CELSIUS,
                    0,
                )
                min_temp = display_temp(
                    self.hass,
                    opb_plant.attributes.get(
                        CONF_PLANTBOOK_MAPPING[CONF_MIN_TEMPERATURE],
                        DEFAULT_MIN_TEMPERATURE,
                    ),
                    TEMP_CELSIUS,
                    0,
                )
                opb_mmol = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MAX_MMOL]
                )
                if opb_mmol:
                    max_mol = round(opb_mmol * PPFD_DLI_FACTOR)
                else:
                    max_mol = DEFAULT_MAX_MOL

                opb_mmol = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MIN_MMOL]
                )
                if opb_mmol:
                    min_mol = round(opb_mmol * PPFD_DLI_FACTOR)
                else:
                    min_mol = DEFAULT_MIN_MOL

                max_conductivity = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MAX_CONDUCTIVITY],
                    DEFAULT_MAX_CONDUCTIVITY,
                )
                min_condictivity = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MIN_CONDUCTIVITY],
                    DEFAULT_MIN_CONDUCTIVITY,
                )
                max_humidity = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MAX_HUMIDITY], DEFAULT_MAX_HUMIDITY
                )
                min_humidity = opb_plant.attributes.get(
                    CONF_PLANTBOOK_MAPPING[CONF_MIN_HUMIDITY], DEFAULT_MIN_HUMIDITY
                )

                opb_image = opb_plant.attributes.get(FLOW_PLANT_IMAGE)
                opb_name = opb_plant.attributes.get(OPB_DISPLAY_PID)

                data_schema[vol.Optional(FLOW_RIGHT_PLANT, default=True)] = cv.boolean

                # data_schema[FLOW_WRONG_PLANT] = selector({"boolean": {}})
        data_schema[vol.Required(OPB_DISPLAY_PID, default=opb_name)] = str
        data_schema[vol.Required(CONF_MAX_MOISTURE, default=max_moisture)] = int
        data_schema[vol.Required(CONF_MIN_MOISTURE, default=min_moisture)] = int
        data_schema[vol.Required(CONF_MAX_ILLUMINANCE, default=max_light_lx)] = int
        data_schema[vol.Required(CONF_MIN_ILLUMINANCE, default=min_light_lx)] = int
        data_schema[vol.Required(CONF_MAX_MOL, default=max_mol)] = int
        data_schema[vol.Required(CONF_MIN_MOL, default=min_mol)] = int
        data_schema[
            vol.Required(
                CONF_MAX_TEMPERATURE,
                default=max_temp,
            )
        ] = int
        data_schema[
            vol.Required(
                CONF_MIN_TEMPERATURE,
                default=min_temp,
            )
        ] = int
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
                "temp_unit": self.hass.config.units.temperature_unit,
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
                FLOW_PLANT_SPECIES,
                default=self.plant.species,
            )
        ] = str
        data_schema[
            vol.Optional(
                OPB_DISPLAY_PID,
                default=self.plant.display_species,
            )
        ] = str
        data_schema[
            vol.Optional(ATTR_ENTITY_PICTURE, default=self.plant._attr_entity_picture)
        ] = str

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
        # species = entry.get(CONF_SPECIES)
        _LOGGER.info("Picture: %s", entity_picture)

        if entity_picture is not None:
            if entity_picture == "":
                _LOGGER.info("Remove image to %s", entity_picture)
                self.plant.add_image(entity_picture)
                return
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
                        raise vol.Invalid(f"Invalid URL: {entity_picture}") from exc2
                else:
                    raise vol.Invalid(f"Invalid URL: {entity_picture}") from exc1
            _LOGGER.info("Update image to %s", entity_picture)
            self.plant.add_image(entity_picture)

        new_display_species = entry.options.get(OPB_DISPLAY_PID)
        _LOGGER.info("New display pid")
        if new_display_species is not None:
            self.plant.display_species = new_display_species

        new_species = entry.options.get(FLOW_PLANT_SPECIES)
        if new_species and new_species != self.plant.species:
            opb_plant = None
            opb_ok = False
            _LOGGER.info(
                "Species changed from '%s' to '%s'", self.plant.species, new_species
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
                self.plant.add_image(opb_plant.attributes[FLOW_PLANT_IMAGE])

                for (ha_attribute, opb_attribute) in CONF_PLANTBOOK_MAPPING.items():

                    set_entity = getattr(self.plant, ha_attribute)

                    set_entity_id = set_entity.entity_id
                    _LOGGER.info(
                        "Setting %s to %s",
                        set_entity_id,
                        opb_plant.attributes[opb_attribute],
                    )
                    self.hass.states.async_set(
                        set_entity_id, opb_plant.attributes[opb_attribute]
                    )
                self.plant.species = opb_plant.attributes[OPB_PID]
                _LOGGER.info(
                    "Setting display_species to %s",
                    opb_plant.attributes[OPB_DISPLAY_PID],
                )

                self.plant.display_species = opb_plant.attributes[OPB_DISPLAY_PID]
                # self.async_write_ha_state()

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

                    self.plant.species = new_species
                    # self.async_write_ha_state()

                return True

        self.plant.update_registry()
