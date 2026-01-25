"""Tests for plant integration config flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant import config_entries
from homeassistant.const import ATTR_ENTITY_PICTURE, ATTR_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.plant.config_flow import PlantConfigFlow
from custom_components.plant.const import (
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
    DOMAIN,
    FLOW_PLANT_INFO,
    FLOW_RIGHT_PLANT,
    FLOW_SENSOR_CONDUCTIVITY,
    FLOW_SENSOR_HUMIDITY,
    FLOW_SENSOR_ILLUMINANCE,
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_TEMPERATURE,
    OPB_DISPLAY_PID,
)

from .fixtures.openplantbook_responses import (
    GET_RESULT_MONSTERA_DELICIOSA,
    SEARCH_RESULT_MONSTERA,
)


class TestConfigFlowUserStep:
    """Tests for the user step of config flow."""

    async def test_user_step_shows_form(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that user step shows the form."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    async def test_user_step_with_input_proceeds_to_select_species(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """Test user step with valid input proceeds to species selection."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                ATTR_NAME: "My Plant",
                ATTR_SPECIES: "monstera",
            },
        )

        # Should proceed to select_species step when OPB is available
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "select_species"

    async def test_user_step_without_opb_skips_to_limits(
        self,
        hass: HomeAssistant,
        mock_no_openplantbook,
    ) -> None:
        """Test user step without OpenPlantbook skips to limits."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                ATTR_NAME: "My Plant",
                ATTR_SPECIES: "monstera",
            },
        )

        # Should skip to limits step when OPB is not available
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "limits"

    async def test_user_step_with_sensors(
        self,
        hass: HomeAssistant,
        mock_no_openplantbook,
    ) -> None:
        """Test user step with sensor selections."""
        # Set up mock sensors
        hass.states.async_set("sensor.temp", "22", {"device_class": "temperature"})
        hass.states.async_set("sensor.moisture", "45", {"device_class": "moisture"})

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                ATTR_NAME: "My Plant",
                ATTR_SPECIES: "ficus",
                FLOW_SENSOR_TEMPERATURE: "sensor.temp",
                FLOW_SENSOR_MOISTURE: "sensor.moisture",
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "limits"


class TestConfigFlowSelectSpeciesStep:
    """Tests for the select_species step of config flow."""

    async def test_select_species_shows_dropdown(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """Test that select_species shows dropdown from OPB search."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                ATTR_NAME: "My Monstera",
                ATTR_SPECIES: "monstera",
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "select_species"

    async def test_select_species_proceeds_to_limits(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """Test selecting a species proceeds to limits step."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                ATTR_NAME: "My Monstera",
                ATTR_SPECIES: "monstera",
            },
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                ATTR_SPECIES: "monstera deliciosa",
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "limits"


class TestConfigFlowLimitsStep:
    """Tests for the limits step of config flow."""

    async def test_limits_step_shows_defaults(
        self,
        hass: HomeAssistant,
        mock_no_openplantbook,
    ) -> None:
        """Test limits step shows default threshold values."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                ATTR_NAME: "My Plant",
                ATTR_SPECIES: "",
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "limits"

    async def test_limits_step_creates_entry(
        self,
        hass: HomeAssistant,
        mock_no_openplantbook,
    ) -> None:
        """Test completing limits step creates config entry."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                ATTR_NAME: "My Plant",
                ATTR_SPECIES: "some plant",
            },
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                OPB_DISPLAY_PID: "Some Plant",
                CONF_MAX_MOISTURE: 60,
                CONF_MIN_MOISTURE: 20,
                CONF_MAX_TEMPERATURE: 40,
                CONF_MIN_TEMPERATURE: 10,
                CONF_MAX_CONDUCTIVITY: 3000,
                CONF_MIN_CONDUCTIVITY: 500,
                CONF_MAX_ILLUMINANCE: 100000,
                CONF_MIN_ILLUMINANCE: 0,
                CONF_MAX_HUMIDITY: 60,
                CONF_MIN_HUMIDITY: 20,
                CONF_MAX_DLI: 30,
                CONF_MIN_DLI: 2,
                ATTR_ENTITY_PICTURE: "",
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "My Plant"
        assert FLOW_PLANT_INFO in result["data"]

    async def test_limits_step_with_opb_data(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """Test limits step with OpenPlantbook data pre-filled."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                ATTR_NAME: "My Monstera",
                ATTR_SPECIES: "monstera",
            },
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                ATTR_SPECIES: "monstera deliciosa",
            },
        )

        # The limits form should show OPB data
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "limits"

    async def test_limits_wrong_plant_goes_back(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """Test clicking 'wrong plant' goes back to species selection."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                ATTR_NAME: "My Monstera",
                ATTR_SPECIES: "monstera",
            },
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                ATTR_SPECIES: "monstera deliciosa",
            },
        )

        # Submit with FLOW_RIGHT_PLANT = False
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                FLOW_RIGHT_PLANT: False,
                OPB_DISPLAY_PID: "Monstera deliciosa",
                CONF_MAX_MOISTURE: 60,
                CONF_MIN_MOISTURE: 20,
                CONF_MAX_TEMPERATURE: 30,
                CONF_MIN_TEMPERATURE: 15,
                CONF_MAX_CONDUCTIVITY: 2000,
                CONF_MIN_CONDUCTIVITY: 350,
                CONF_MAX_ILLUMINANCE: 35000,
                CONF_MIN_ILLUMINANCE: 1500,
                CONF_MAX_HUMIDITY: 80,
                CONF_MIN_HUMIDITY: 50,
                CONF_MAX_DLI: 22,
                CONF_MIN_DLI: 5,
                ATTR_ENTITY_PICTURE: GET_RESULT_MONSTERA_DELICIOSA["image_url"],
            },
        )

        # Should go back to select_species
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "select_species"


class TestConfigFlowImport:
    """Tests for config import from YAML."""

    async def test_import_creates_entry(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test importing config creates an entry."""
        import_data = {
            FLOW_PLANT_INFO: {
                ATTR_NAME: "Imported Plant",
                ATTR_SPECIES: "test species",
            },
        }

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=import_data,
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Imported Plant"


class TestOptionsFlow:
    """Tests for the options flow."""

    async def test_options_flow_init(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test initializing the options flow."""
        result = await hass.config_entries.options.async_init(init_integration.entry_id)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"

    async def test_options_flow_update_species(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
        mock_no_openplantbook,
    ) -> None:
        """Test updating species through options flow."""
        result = await hass.config_entries.options.async_init(init_integration.entry_id)

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                ATTR_SPECIES: "new species",
                OPB_DISPLAY_PID: "New Species",
                ATTR_ENTITY_PICTURE: "https://example.com/new.jpg",
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY

    async def test_options_flow_toggle_triggers(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test toggling problem triggers through options flow."""
        result = await hass.config_entries.options.async_init(init_integration.entry_id)

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "illuminance_trigger": False,
                "moisture_trigger": False,
                "temperature_trigger": True,
                "humidity_trigger": True,
                "conductivity_trigger": True,
                "dli_trigger": True,
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY

    async def test_options_flow_updates_plant_entity(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
        mock_no_openplantbook,
    ) -> None:
        """Test that options flow actually updates the plant entity."""
        # Get the plant entity before making changes
        plant = hass.data[DOMAIN][init_integration.entry_id]["plant"]
        original_display_species = plant.display_species
        original_entity_picture = plant.entity_picture

        # Run the options flow with new values
        new_display_species = "Updated Display Name"
        new_entity_picture = "https://example.com/updated.jpg"

        result = await hass.config_entries.options.async_init(init_integration.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                ATTR_SPECIES: "updated species",
                OPB_DISPLAY_PID: new_display_species,
                ATTR_ENTITY_PICTURE: new_entity_picture,
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()

        # Verify the plant entity was actually updated
        assert plant.display_species == new_display_species
        assert plant.entity_picture == new_entity_picture
        assert plant.display_species != original_display_species
        assert plant.entity_picture != original_entity_picture
