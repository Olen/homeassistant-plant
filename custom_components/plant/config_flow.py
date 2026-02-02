"""Config flow for Custom Plant integration."""

from __future__ import annotations

import logging
import re
import urllib.parse
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_DOMAIN,
    ATTR_ENTITY_PICTURE,
    ATTR_NAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.selector import selector

from .const import (
    ATTR_ENTITY,
    ATTR_LIMITS,
    ATTR_OPTIONS,
    ATTR_SEARCH_FOR,
    ATTR_SELECT,
    ATTR_SENSORS,
    ATTR_SPECIES,
    CONF_MAX_CONDUCTIVITY,
    CONF_MAX_DLI,
    CONF_MAX_HUMIDITY,
    CONF_MAX_ILLUMINANCE,
    CONF_MAX_MOISTURE,
    CONF_MAX_TEMPERATURE,
    CONF_MIN_CONDUCTIVITY,
    CONF_MIN_DLI,
    CONF_MIN_HUMIDITY,
    CONF_MIN_ILLUMINANCE,
    CONF_MIN_MOISTURE,
    CONF_MIN_TEMPERATURE,
    DATA_SOURCE,
    DATA_SOURCE_PLANTBOOK,
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
    DOMAIN,
    DOMAIN_PLANTBOOK,
    DOMAIN_SENSOR,
    FLOW_CO2_TRIGGER,
    FLOW_CONDUCTIVITY_TRIGGER,
    FLOW_DLI_TRIGGER,
    FLOW_ERROR_NOTFOUND,
    FLOW_FORCE_SPECIES_UPDATE,
    FLOW_HUMIDITY_TRIGGER,
    FLOW_ILLUMINANCE_TRIGGER,
    FLOW_MOISTURE_TRIGGER,
    FLOW_PLANT_INFO,
    FLOW_PLANT_LIMITS,
    FLOW_RIGHT_PLANT,
    FLOW_SENSOR_CO2,
    FLOW_SENSOR_CONDUCTIVITY,
    FLOW_SENSOR_HUMIDITY,
    FLOW_SENSOR_ILLUMINANCE,
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_SOIL_TEMPERATURE,
    FLOW_SENSOR_TEMPERATURE,
    FLOW_SOIL_TEMPERATURE_TRIGGER,
    FLOW_STRING_DESCRIPTION,
    FLOW_TEMP_UNIT,
    FLOW_TEMPERATURE_TRIGGER,
    OPB_DISPLAY_PID,
    URL_SCHEME_HTTP,
    URL_SCHEME_MEDIA_SOURCE,
)
from .plant_helpers import PlantHelper

_LOGGER = logging.getLogger(__name__)


class PlantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Plants."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.plant_info: dict[str, Any] = {}
        self.error: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler()

    async def async_step_import(self, import_input: dict[str, Any]) -> ConfigFlowResult:
        """Import config from configuration.yaml."""
        _LOGGER.debug(import_input)
        return self.async_create_entry(
            title=import_input[FLOW_PLANT_INFO][ATTR_NAME],
            data=import_input,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step - name and species only."""
        errors = {}
        if user_input is not None:
            _LOGGER.debug("User Input %s", user_input)
            # Validate user input
            valid = await self.validate_step_1(user_input)
            if valid:
                # Store info to use in next step
                self.plant_info = user_input
                self.plant_info[ATTR_SEARCH_FOR] = user_input[ATTR_SPECIES]
                _LOGGER.debug("Plant_info: %s", self.plant_info)

                # Return the form of the next step
                return await self.async_step_select_species()

        # Specify items in the order they are to be displayed in the UI
        if self.error == FLOW_ERROR_NOTFOUND:
            errors[ATTR_SPECIES] = self.error
        data_schema = {
            vol.Required(ATTR_NAME, default=self.plant_info.get(ATTR_NAME)): cv.string,
            vol.Optional(
                ATTR_SPECIES, default=self.plant_info.get(ATTR_SPECIES, "")
            ): cv.string,
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(data_schema),
            errors=errors,
            description_placeholders={"opb_search": self.plant_info.get(ATTR_SPECIES)},
        )

    async def async_step_select_species(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Search the OpenPlantbook."""
        errors = {}

        if user_input is not None:
            _LOGGER.debug("User Input %s", user_input)

            # Check if the user wants to re-search with a different term
            new_search = user_input.get(ATTR_SEARCH_FOR, "").strip()
            if new_search and new_search != self.plant_info.get(ATTR_SEARCH_FOR, ""):
                self.plant_info[ATTR_SEARCH_FOR] = new_search
                self.plant_info[ATTR_SPECIES] = new_search
                # Re-show this step with new search results
                return await self.async_step_select_species()

            # Validate user input
            valid = await self.validate_step_2(user_input)
            if valid:
                # Store info to use in next step
                self.plant_info[DATA_SOURCE] = DOMAIN_PLANTBOOK
                self.plant_info[ATTR_SPECIES] = user_input[ATTR_SPECIES]

                # Return the form of the next step
                _LOGGER.debug("Plant_info: %s", self.plant_info)
                return await self.async_step_sensors()
        plant_helper = PlantHelper(self.hass)
        search_result = await plant_helper.openplantbook_search(
            species=self.plant_info[ATTR_SEARCH_FOR]
        )
        if search_result is None:
            return await self.async_step_sensors()
        dropdown = []
        for pid, display_pid in search_result.items():
            dropdown.append({"label": display_pid, "value": pid})
        _LOGGER.debug("Dropdown: %s", dropdown)
        data_schema = {}
        data_schema[
            vol.Optional(
                ATTR_SEARCH_FOR,
                default=self.plant_info.get(ATTR_SEARCH_FOR, ""),
            )
        ] = cv.string
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

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle sensor selection step."""
        if user_input is not None:
            _LOGGER.debug("User Input (sensors) %s", user_input)
            # Store sensor selections in plant_info
            for key in (
                FLOW_SENSOR_TEMPERATURE,
                FLOW_SENSOR_MOISTURE,
                FLOW_SENSOR_CONDUCTIVITY,
                FLOW_SENSOR_ILLUMINANCE,
                FLOW_SENSOR_HUMIDITY,
                FLOW_SENSOR_CO2,
                FLOW_SENSOR_SOIL_TEMPERATURE,
            ):
                self.plant_info[key] = user_input.get(key)
            _LOGGER.debug("Plant_info: %s", self.plant_info)
            return await self.async_step_limits()

        data_schema = {}
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
                    ATTR_DEVICE_CLASS: SensorDeviceClass.MOISTURE,
                    ATTR_DOMAIN: DOMAIN_SENSOR,
                }
            }
        )
        data_schema[FLOW_SENSOR_CONDUCTIVITY] = selector(
            {
                ATTR_ENTITY: {
                    ATTR_DEVICE_CLASS: SensorDeviceClass.CONDUCTIVITY,
                    ATTR_DOMAIN: DOMAIN_SENSOR,
                }
            }
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
        data_schema[FLOW_SENSOR_CO2] = selector(
            {
                ATTR_ENTITY: {
                    ATTR_DEVICE_CLASS: SensorDeviceClass.CO2,
                    ATTR_DOMAIN: DOMAIN_SENSOR,
                }
            }
        )
        data_schema[FLOW_SENSOR_SOIL_TEMPERATURE] = selector(
            {
                ATTR_ENTITY: {
                    ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                    ATTR_DOMAIN: DOMAIN_SENSOR,
                }
            }
        )

        return self.async_show_form(
            step_id="sensors",
            data_schema=vol.Schema(data_schema),
        )

    async def async_step_limits(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle max/min values."""

        plant_helper = PlantHelper(self.hass)
        if user_input is not None:
            _LOGGER.debug("User Input %s", user_input)
            # Validate user input
            valid = await self.validate_step_3(user_input)
            if (
                plant_helper.has_openplantbook
                and self.plant_info.get(ATTR_SEARCH_FOR)
                and self.plant_info.get(DATA_SOURCE) == DOMAIN_PLANTBOOK
                and not user_input.get(FLOW_RIGHT_PLANT)
            ):
                return await self.async_step_select_species()
            if valid:
                self.plant_info[ATTR_ENTITY_PICTURE] = user_input.get(
                    ATTR_ENTITY_PICTURE
                )
                self.plant_info[OPB_DISPLAY_PID] = user_input.get(OPB_DISPLAY_PID)
                if not self.plant_info[ATTR_SPECIES]:
                    self.plant_info[ATTR_SPECIES] = self.plant_info[OPB_DISPLAY_PID]
                user_input.pop(ATTR_ENTITY_PICTURE)
                user_input.pop(OPB_DISPLAY_PID)
                if FLOW_RIGHT_PLANT in user_input:
                    user_input.pop(FLOW_RIGHT_PLANT)

                # Fill in default values for hidden thresholds to keep data structure complete
                limits = dict(user_input)
                all_threshold_defaults = {
                    CONF_MAX_MOISTURE: DEFAULT_MAX_MOISTURE,
                    CONF_MIN_MOISTURE: DEFAULT_MIN_MOISTURE,
                    CONF_MAX_TEMPERATURE: DEFAULT_MAX_TEMPERATURE,
                    CONF_MIN_TEMPERATURE: DEFAULT_MIN_TEMPERATURE,
                    CONF_MAX_CONDUCTIVITY: DEFAULT_MAX_CONDUCTIVITY,
                    CONF_MIN_CONDUCTIVITY: DEFAULT_MIN_CONDUCTIVITY,
                    CONF_MAX_ILLUMINANCE: DEFAULT_MAX_ILLUMINANCE,
                    CONF_MIN_ILLUMINANCE: DEFAULT_MIN_ILLUMINANCE,
                    CONF_MAX_DLI: DEFAULT_MAX_DLI,
                    CONF_MIN_DLI: DEFAULT_MIN_DLI,
                    CONF_MAX_HUMIDITY: DEFAULT_MAX_HUMIDITY,
                    CONF_MIN_HUMIDITY: DEFAULT_MIN_HUMIDITY,
                }
                for key, default_val in all_threshold_defaults.items():
                    if key not in limits:
                        limits[key] = default_val

                self.plant_info[FLOW_PLANT_LIMITS] = limits
                _LOGGER.debug("Plant_info: %s", self.plant_info)
                # Return the form of the next step
                return await self.async_step_limits_done()

        data_schema = {}
        plant_config = await plant_helper.generate_configentry(
            config={
                ATTR_NAME: self.plant_info[ATTR_NAME],
                ATTR_SPECIES: self.plant_info[ATTR_SPECIES],
                ATTR_SENSORS: {},
            }
        )
        extra_desc = ""
        if plant_config[FLOW_PLANT_INFO].get(OPB_DISPLAY_PID):
            # We got data from OPB.  Display a "wrong plant" switch
            data_schema[vol.Optional(FLOW_RIGHT_PLANT, default=True)] = cv.boolean

            display_pid = plant_config[FLOW_PLANT_INFO].get(OPB_DISPLAY_PID)
        else:
            if plant_helper.has_openplantbook:
                # We did not get any data from OPB.  Show a warning
                if (
                    not self.plant_info[ATTR_SEARCH_FOR]
                    or self.plant_info[ATTR_SEARCH_FOR] == ""
                ):
                    extra_desc = "Skipping OpenPlantbook due to missing species. Using default values for thresholds.<br /><br />"
                else:
                    extra_desc = f"Did not find **«{self.plant_info[ATTR_SEARCH_FOR]}»** in OpenPlantbook. Using default values for thresholds.<br /><br />"
            display_pid = self.plant_info[ATTR_SEARCH_FOR].title() or ""
        data_schema[
            vol.Optional(
                OPB_DISPLAY_PID,
                default=display_pid,
            )
        ] = cv.string

        # Determine which sensors were selected to conditionally show thresholds
        selected_sensors = {
            "moisture": bool(self.plant_info.get(FLOW_SENSOR_MOISTURE)),
            "temperature": bool(self.plant_info.get(FLOW_SENSOR_TEMPERATURE)),
            "conductivity": bool(self.plant_info.get(FLOW_SENSOR_CONDUCTIVITY)),
            "illuminance": bool(self.plant_info.get(FLOW_SENSOR_ILLUMINANCE)),
            "humidity": bool(self.plant_info.get(FLOW_SENSOR_HUMIDITY)),
            "co2": bool(self.plant_info.get(FLOW_SENSOR_CO2)),
            "soil_temperature": bool(self.plant_info.get(FLOW_SENSOR_SOIL_TEMPERATURE)),
        }
        show_all = not any(selected_sensors.values())

        if show_all or selected_sensors["moisture"]:
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

        if show_all or selected_sensors["illuminance"]:
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
            # Always show DLI together with illuminance
            data_schema[
                vol.Required(
                    CONF_MAX_DLI,
                    default=plant_config[FLOW_PLANT_INFO][ATTR_LIMITS].get(
                        CONF_MAX_DLI
                    ),
                )
            ] = int
            data_schema[
                vol.Required(
                    CONF_MIN_DLI,
                    default=plant_config[FLOW_PLANT_INFO][ATTR_LIMITS].get(
                        CONF_MIN_DLI
                    ),
                )
            ] = int

        if show_all or selected_sensors["temperature"]:
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

        if show_all or selected_sensors["conductivity"]:
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

        if show_all or selected_sensors["humidity"]:
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
        entity_picture = plant_config[FLOW_PLANT_INFO].get(ATTR_ENTITY_PICTURE)
        if not entity_picture.startswith(
            URL_SCHEME_HTTP
        ) and not entity_picture.startswith(URL_SCHEME_MEDIA_SOURCE):
            try:
                entity_picture = f"{get_url(self.hass, require_current_request=True)}{urllib.parse.quote(entity_picture)}"
            except NoURLAvailableError:
                _LOGGER.error(
                    "No internal or external url found. Please configure these in HA General Settings"
                )
                entity_picture = ""
        return self.async_show_form(
            step_id="limits",
            data_schema=vol.Schema(data_schema),
            description_placeholders={
                ATTR_ENTITY_PICTURE: entity_picture,
                ATTR_NAME: plant_config[FLOW_PLANT_INFO].get(ATTR_NAME),
                FLOW_TEMP_UNIT: self.hass.config.units.temperature_unit,
                "br": "<br />",
                "extra_desc": extra_desc,
            },
        )

    async def async_step_limits_done(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create entry after limits are set."""
        return self.async_create_entry(
            title=self.plant_info[ATTR_NAME],
            data={FLOW_PLANT_INFO: self.plant_info},
        )

    async def validate_step_1(self, user_input: dict[str, Any]) -> bool:
        """Validate step one."""
        _LOGGER.debug("Validating step 1: %s", user_input)
        return True

    async def validate_step_2(self, user_input: dict[str, Any]) -> bool:
        """Validate step two."""
        _LOGGER.debug("Validating step 2: %s", user_input)

        if ATTR_SPECIES not in user_input:
            return False
        if not isinstance(user_input[ATTR_SPECIES], str):
            return False
        if len(user_input[ATTR_SPECIES]) < 5:
            return False
        _LOGGER.debug("Valid")

        return True

    async def validate_step_3(self, user_input: dict[str, Any]) -> bool:
        """Validate step three."""
        _LOGGER.debug("Validating step 3: %s", user_input)

        return True

    async def validate_step_4(self, user_input: dict[str, Any]) -> bool:
        """Validate step four."""
        return True


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handling options for plant."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self.plant = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            if ATTR_SPECIES not in user_input or not re.match(
                r"\w+", user_input[ATTR_SPECIES]
            ):
                user_input[ATTR_SPECIES] = ""
            if ATTR_ENTITY_PICTURE not in user_input or not re.match(
                r"(\/)?\w+", user_input[ATTR_ENTITY_PICTURE]
            ):
                user_input[ATTR_ENTITY_PICTURE] = ""
            if OPB_DISPLAY_PID not in user_input or not re.match(
                r"\w+", user_input[OPB_DISPLAY_PID]
            ):
                user_input[OPB_DISPLAY_PID] = ""

            return self.async_create_entry(title="", data=user_input)

        self.plant = self.hass.data[DOMAIN][self.config_entry.entry_id]["plant"]
        plant_helper = PlantHelper(hass=self.hass)
        data_schema = {}
        data_schema[
            vol.Optional(
                ATTR_SPECIES, description={"suggested_value": self.plant.species}
            )
        ] = cv.string
        if plant_helper.has_openplantbook and self.plant.species:
            data_schema[vol.Optional(FLOW_FORCE_SPECIES_UPDATE, default=False)] = (
                cv.boolean
            )

        display_species = self.plant.display_species or ""
        data_schema[
            vol.Optional(
                OPB_DISPLAY_PID, description={"suggested_value": display_species}
            )
        ] = str
        entity_picture = self.plant.entity_picture or ""
        data_schema[
            vol.Optional(
                ATTR_ENTITY_PICTURE, description={"suggested_value": entity_picture}
            )
        ] = str

        data_schema[
            vol.Optional(
                FLOW_ILLUMINANCE_TRIGGER, default=self.plant.illuminance_trigger
            )
        ] = cv.boolean
        data_schema[vol.Optional(FLOW_DLI_TRIGGER, default=self.plant.dli_trigger)] = (
            cv.boolean
        )

        data_schema[
            vol.Optional(FLOW_HUMIDITY_TRIGGER, default=self.plant.humidity_trigger)
        ] = cv.boolean
        data_schema[
            vol.Optional(
                FLOW_TEMPERATURE_TRIGGER, default=self.plant.temperature_trigger
            )
        ] = cv.boolean
        data_schema[
            vol.Optional(FLOW_MOISTURE_TRIGGER, default=self.plant.moisture_trigger)
        ] = cv.boolean
        data_schema[
            vol.Optional(
                FLOW_CONDUCTIVITY_TRIGGER, default=self.plant.conductivity_trigger
            )
        ] = cv.boolean
        data_schema[vol.Optional(FLOW_CO2_TRIGGER, default=self.plant.co2_trigger)] = (
            cv.boolean
        )
        data_schema[
            vol.Optional(
                FLOW_SOIL_TEMPERATURE_TRIGGER,
                default=self.plant.soil_temperature_trigger,
            )
        ] = cv.boolean

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(data_schema),
            description_placeholders={"plant_name": self.plant.name},
        )


async def update_plant_options(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> None:
    """Handle options update."""
    # Guard against being called after entry is unloaded
    if entry.entry_id not in hass.data.get(DOMAIN, {}):
        _LOGGER.debug("Ignoring update for unloaded entry %s", entry.entry_id)
        return

    plant = hass.data[DOMAIN][entry.entry_id]["plant"]

    _LOGGER.debug(
        "Update plant options begin for %s Data %s, Options: %s",
        entry.entry_id,
        entry.options,
        entry.data,
    )
    entity_picture = entry.options.get(ATTR_ENTITY_PICTURE)

    if entity_picture is not None:
        if entity_picture == "":
            plant.add_image(entity_picture)
        elif entity_picture.startswith(URL_SCHEME_MEDIA_SOURCE):
            # Media-source URL - pass through for frontend/card to resolve
            _LOGGER.debug("Using media-source URL: %s", entity_picture)
            plant.add_image(entity_picture)
        elif entity_picture.startswith(("http://", "https://")):
            # Full HTTP URL - validate
            try:
                cv.url(entity_picture)
                _LOGGER.debug("Using HTTP URL: %s", entity_picture)
                plant.add_image(entity_picture)
            except vol.Invalid as exc:
                _LOGGER.warning("Not a valid URL: %s", entity_picture)
                raise vol.Invalid(f"Invalid URL: {entity_picture}") from exc
        elif entity_picture.startswith("/"):
            # Relative path (like /local/...) - validate as path
            try:
                cv.path(entity_picture)
                _LOGGER.debug("Using local path: %s", entity_picture)
                plant.add_image(entity_picture)
            except vol.Invalid as exc:
                _LOGGER.warning("Not a valid path: %s", entity_picture)
                raise vol.Invalid(f"Invalid path: {entity_picture}") from exc
        else:
            # Unknown format
            _LOGGER.warning(
                "Unknown image format: %s. Use a full URL or /local/ path.",
                entity_picture,
            )
            raise vol.Invalid(
                f"Unknown image format: {entity_picture}. "
                "Use a full URL, media-source:// URL, or /local/ path."
            )

    new_display_species = entry.options.get(OPB_DISPLAY_PID)
    if new_display_species is not None:
        # Capitalize first letter for proper binomial nomenclature
        plant.display_species = (
            new_display_species[0].upper() + new_display_species[1:]
            if new_display_species
            else ""
        )

    new_species = entry.options.get(ATTR_SPECIES)
    force_new_species = entry.options.get(FLOW_FORCE_SPECIES_UPDATE)
    if new_species is not None and (
        new_species != plant.species or force_new_species is True
    ):
        _LOGGER.debug("Species changed from '%s' to '%s'", plant.species, new_species)
        plant_helper = PlantHelper(hass=hass)
        plant_config = await plant_helper.generate_configentry(
            config={
                ATTR_SPECIES: new_species,
                ATTR_ENTITY_PICTURE: entity_picture,
                OPB_DISPLAY_PID: new_display_species,
                FLOW_FORCE_SPECIES_UPDATE: force_new_species,
            }
        )
        if plant_config[DATA_SOURCE] == DATA_SOURCE_PLANTBOOK:
            plant.species = new_species
            plant.add_image(plant_config[FLOW_PLANT_INFO][ATTR_ENTITY_PICTURE])
            # Capitalize first letter for proper binomial nomenclature
            opb_display = plant_config[FLOW_PLANT_INFO][OPB_DISPLAY_PID]
            plant.display_species = (
                opb_display[0].upper() + opb_display[1:] if opb_display else ""
            )
            for key, value in plant_config[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].items():
                set_entity = getattr(plant, key)
                _LOGGER.debug("Entity: %s To: %s", set_entity, value)
                set_entity_id = set_entity.entity_id
                _LOGGER.debug(
                    "Setting %s to %s",
                    set_entity_id,
                    value,
                )

                hass.states.async_set(
                    set_entity_id,
                    new_state=value,
                    attributes=hass.states.get(set_entity_id).attributes,
                )

        else:
            plant.species = new_species

        # We need to reset the force_update option back to False, or else
        # this will only be run once (unchanged options are will not trigger the flow)
        options = dict(entry.options)
        data = dict(entry.data)
        options[FLOW_FORCE_SPECIES_UPDATE] = False
        options[OPB_DISPLAY_PID] = plant.display_species
        options[ATTR_ENTITY_PICTURE] = plant.entity_picture
        _LOGGER.debug(
            "Doing a refresh to update values: Data: %s Options: %s",
            data,
            options,
        )

        hass.config_entries.async_update_entry(entry, data=data, options=options)
    _LOGGER.debug("Update plant options done for %s", entry.entry_id)
    plant.update_registry()
