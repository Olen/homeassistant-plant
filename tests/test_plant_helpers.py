"""Tests for PlantHelper class."""

from __future__ import annotations

from homeassistant.const import ATTR_ENTITY_PICTURE, ATTR_NAME
from homeassistant.core import HomeAssistant

from custom_components.plant.const import (
    ATTR_LIMITS,
    ATTR_SENSORS,
    ATTR_SPECIES,
    CONF_MAX_DLI,
    CONF_MAX_ILLUMINANCE,
    CONF_MAX_MOISTURE,
    CONF_MIN_DLI,
    CONF_MIN_ILLUMINANCE,
    CONF_MIN_MOISTURE,
    DATA_SOURCE,
    DATA_SOURCE_DEFAULT,
    DATA_SOURCE_PLANTBOOK,
    DEFAULT_MAX_ILLUMINANCE,
    DEFAULT_MAX_MOISTURE,
    DEFAULT_MIN_ILLUMINANCE,
    DEFAULT_MIN_MOISTURE,
    FLOW_PLANT_INFO,
    OPB_DISPLAY_PID,
)
from custom_components.plant.plant_helpers import PlantHelper

from .fixtures.openplantbook_responses import (
    GET_RESULT_MONSTERA_DELICIOSA,
)


class TestPlantHelperOpenplantbookDetection:
    """Tests for OpenPlantbook availability detection."""

    async def test_has_openplantbook_when_available(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """Test has_openplantbook returns True when OPB is available."""
        helper = PlantHelper(hass)
        assert helper.has_openplantbook is True

    async def test_has_openplantbook_when_not_available(
        self,
        hass: HomeAssistant,
        mock_no_openplantbook,
    ) -> None:
        """Test has_openplantbook returns False when OPB is not available."""
        helper = PlantHelper(hass)
        assert helper.has_openplantbook is False


class TestPlantHelperSearch:
    """Tests for OpenPlantbook search functionality."""

    async def test_openplantbook_search_success(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """Test successful OpenPlantbook search."""
        helper = PlantHelper(hass)
        result = await helper.openplantbook_search("monstera")

        assert result is not None
        assert "monstera deliciosa" in result

    async def test_openplantbook_search_no_opb(
        self,
        hass: HomeAssistant,
        mock_no_openplantbook,
    ) -> None:
        """Test search returns None when OPB not available."""
        helper = PlantHelper(hass)
        result = await helper.openplantbook_search("monstera")

        assert result is None

    async def test_openplantbook_search_empty_species(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """Test search with empty species returns None."""
        helper = PlantHelper(hass)

        assert await helper.openplantbook_search("") is None
        assert await helper.openplantbook_search(None) is None

    async def test_openplantbook_search_no_results(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """Test search with no results."""
        helper = PlantHelper(hass)
        # Search for something that won't match our mock
        result = await helper.openplantbook_search("nonexistent plant xyz")

        # Our mock returns empty dict for non-matching searches
        assert result == {} or result is None


class TestPlantHelperGet:
    """Tests for OpenPlantbook get functionality."""

    async def test_openplantbook_get_success(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """Test successful OpenPlantbook get."""
        helper = PlantHelper(hass)
        result = await helper.openplantbook_get("monstera deliciosa")

        assert result is not None
        assert result["pid"] == "monstera deliciosa"
        assert "max_soil_moist" in result
        assert "min_temp" in result

    async def test_openplantbook_get_no_opb(
        self,
        hass: HomeAssistant,
        mock_no_openplantbook,
    ) -> None:
        """Test get returns None when OPB not available."""
        helper = PlantHelper(hass)
        result = await helper.openplantbook_get("monstera deliciosa")

        assert result is None

    async def test_openplantbook_get_empty_species(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """Test get with empty species returns None."""
        helper = PlantHelper(hass)

        assert await helper.openplantbook_get("") is None
        assert await helper.openplantbook_get(None) is None

    async def test_openplantbook_get_not_found(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """Test get with unknown species returns None."""
        helper = PlantHelper(hass)
        result = await helper.openplantbook_get("unknown plant species")

        assert result is None


class TestPlantHelperGenerateConfigentry:
    """Tests for generate_configentry functionality."""

    async def test_generate_configentry_with_defaults(
        self,
        hass: HomeAssistant,
        mock_no_openplantbook,
    ) -> None:
        """Test generating config entry with default values."""
        helper = PlantHelper(hass)
        config = {
            ATTR_NAME: "Test Plant",
            ATTR_SPECIES: "",
            ATTR_SENSORS: {},
        }

        result = await helper.generate_configentry(config)

        assert DATA_SOURCE in result
        assert result[DATA_SOURCE] == DATA_SOURCE_DEFAULT
        assert FLOW_PLANT_INFO in result

        plant_info = result[FLOW_PLANT_INFO]
        assert plant_info[ATTR_NAME] == "Test Plant"

        limits = plant_info[ATTR_LIMITS]
        assert limits[CONF_MAX_MOISTURE] == DEFAULT_MAX_MOISTURE
        assert limits[CONF_MIN_MOISTURE] == DEFAULT_MIN_MOISTURE
        assert limits[CONF_MAX_ILLUMINANCE] == DEFAULT_MAX_ILLUMINANCE
        assert limits[CONF_MIN_ILLUMINANCE] == DEFAULT_MIN_ILLUMINANCE

    async def test_generate_configentry_with_opb(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """Test generating config entry with OpenPlantbook data."""
        helper = PlantHelper(hass)
        config = {
            ATTR_NAME: "My Monstera",
            ATTR_SPECIES: "monstera deliciosa",
            ATTR_SENSORS: {},
        }

        result = await helper.generate_configentry(config)

        assert result[DATA_SOURCE] == DATA_SOURCE_PLANTBOOK

        plant_info = result[FLOW_PLANT_INFO]
        limits = plant_info[ATTR_LIMITS]

        # Values should come from OPB mock data
        assert (
            limits[CONF_MAX_MOISTURE] == GET_RESULT_MONSTERA_DELICIOSA["max_soil_moist"]
        )
        assert (
            limits[CONF_MIN_MOISTURE] == GET_RESULT_MONSTERA_DELICIOSA["min_soil_moist"]
        )
        assert (
            limits[CONF_MAX_ILLUMINANCE]
            == GET_RESULT_MONSTERA_DELICIOSA["max_light_lux"]
        )
        assert (
            limits[CONF_MIN_ILLUMINANCE]
            == GET_RESULT_MONSTERA_DELICIOSA["min_light_lux"]
        )

        # Image should be from OPB
        assert (
            plant_info[ATTR_ENTITY_PICTURE]
            == GET_RESULT_MONSTERA_DELICIOSA["image_url"]
        )

        # Display PID should be set
        assert (
            plant_info[OPB_DISPLAY_PID] == GET_RESULT_MONSTERA_DELICIOSA["display_pid"]
        )

    async def test_generate_configentry_preserves_custom_limits(
        self,
        hass: HomeAssistant,
        mock_no_openplantbook,
    ) -> None:
        """Test that custom limits in config are preserved."""
        helper = PlantHelper(hass)
        config = {
            ATTR_NAME: "Test Plant",
            ATTR_SPECIES: "test",
            ATTR_SENSORS: {},
            CONF_MAX_MOISTURE: 75,
            CONF_MIN_MOISTURE: 25,
        }

        result = await helper.generate_configentry(config)

        limits = result[FLOW_PLANT_INFO][ATTR_LIMITS]
        assert limits[CONF_MAX_MOISTURE] == 75
        assert limits[CONF_MIN_MOISTURE] == 25

    async def test_generate_configentry_preserves_entity_picture(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """Test that custom entity picture is preserved over OPB."""
        helper = PlantHelper(hass)
        custom_image = "https://example.com/my_plant.jpg"
        config = {
            ATTR_NAME: "My Monstera",
            ATTR_SPECIES: "monstera deliciosa",
            ATTR_SENSORS: {},
            ATTR_ENTITY_PICTURE: custom_image,
        }

        result = await helper.generate_configentry(config)

        # Custom image should be preserved
        assert result[FLOW_PLANT_INFO][ATTR_ENTITY_PICTURE] == custom_image

    async def test_generate_configentry_with_sensors(
        self,
        hass: HomeAssistant,
        mock_no_openplantbook,
    ) -> None:
        """Test generating config entry with sensor assignments."""
        helper = PlantHelper(hass)
        config = {
            ATTR_NAME: "Test Plant",
            ATTR_SPECIES: "",
            ATTR_SENSORS: {
                "temperature": "sensor.temp",
                "moisture": "sensor.moisture",
            },
        }

        result = await helper.generate_configentry(config)

        plant_info = result[FLOW_PLANT_INFO]
        assert plant_info.get("temperature_sensor") == "sensor.temp"
        assert plant_info.get("moisture_sensor") == "sensor.moisture"

    async def test_generate_configentry_dli_from_mmol(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """Test DLI calculation from OPB mmol values."""
        helper = PlantHelper(hass)
        config = {
            ATTR_NAME: "My Monstera",
            ATTR_SPECIES: "monstera deliciosa",
            ATTR_SENSORS: {},
        }

        result = await helper.generate_configentry(config)

        limits = result[FLOW_PLANT_INFO][ATTR_LIMITS]

        # DLI should be calculated from mmol
        # max_light_mmol = 6000, PPFD_DLI_FACTOR = 0.0036
        # expected_max_dli = round(6000 * 0.0036) = 22
        assert limits[CONF_MAX_DLI] == 22

        # min_light_mmol = 1500
        # expected_min_dli = round(1500 * 0.0036) = 5
        assert limits[CONF_MIN_DLI] == 5


class TestPlantHelperEdgeCases:
    """Tests for edge cases in PlantHelper."""

    async def test_generate_configentry_missing_sensors_key(
        self,
        hass: HomeAssistant,
        mock_no_openplantbook,
    ) -> None:
        """Test generating config entry when ATTR_SENSORS is missing."""
        helper = PlantHelper(hass)
        config = {
            ATTR_NAME: "Test Plant",
            ATTR_SPECIES: "",
            # No ATTR_SENSORS key
        }

        # Should not raise, should add empty sensors
        result = await helper.generate_configentry(config)
        assert FLOW_PLANT_INFO in result

    async def test_generate_configentry_empty_display_pid(
        self,
        hass: HomeAssistant,
        mock_no_openplantbook,
    ) -> None:
        """Test generating config with empty display_pid."""
        helper = PlantHelper(hass)
        config = {
            ATTR_NAME: "Test Plant",
            ATTR_SPECIES: "test",
            ATTR_SENSORS: {},
            OPB_DISPLAY_PID: "",
        }

        result = await helper.generate_configentry(config)

        # Empty string should be converted to None/empty
        plant_info = result[FLOW_PLANT_INFO]
        assert plant_info[OPB_DISPLAY_PID] == "" or plant_info[OPB_DISPLAY_PID] is None
