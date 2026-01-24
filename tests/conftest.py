"""Shared fixtures for plant integration tests."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.const import (
    ATTR_ENTITY_PICTURE,
    ATTR_NAME,
    CONF_NAME,
    STATE_OK,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from custom_components.plant.const import (
    ATTR_LIMITS,
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
    DATA_SOURCE_DEFAULT,
    DATA_SOURCE_PLANTBOOK,
    DOMAIN,
    DOMAIN_PLANTBOOK,
    FLOW_PLANT_INFO,
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


# Standard test plant configuration data
TEST_PLANT_NAME = "Test Plant"
TEST_PLANT_SPECIES = "monstera deliciosa"
TEST_PLANT_DISPLAY_SPECIES = "Monstera deliciosa"
TEST_PLANT_IMAGE = "https://example.com/plant.jpg"
TEST_ENTRY_ID = "test_entry_id_12345"


def create_plant_config_data(
    name: str = TEST_PLANT_NAME,
    species: str = TEST_PLANT_SPECIES,
    display_species: str = TEST_PLANT_DISPLAY_SPECIES,
    entity_picture: str = TEST_PLANT_IMAGE,
    temperature_sensor: str | None = "sensor.test_temperature",
    moisture_sensor: str | None = "sensor.test_moisture",
    conductivity_sensor: str | None = "sensor.test_conductivity",
    illuminance_sensor: str | None = "sensor.test_illuminance",
    humidity_sensor: str | None = "sensor.test_humidity",
    data_source: str = DATA_SOURCE_DEFAULT,
    limits: dict | None = None,
) -> dict[str, Any]:
    """Create plant configuration data for testing."""
    if limits is None:
        limits = {
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
        }

    return {
        DATA_SOURCE: data_source,
        FLOW_PLANT_INFO: {
            ATTR_NAME: name,
            ATTR_SPECIES: species,
            OPB_DISPLAY_PID: display_species,
            ATTR_ENTITY_PICTURE: entity_picture,
            ATTR_LIMITS: limits,
            FLOW_SENSOR_TEMPERATURE: temperature_sensor,
            FLOW_SENSOR_MOISTURE: moisture_sensor,
            FLOW_SENSOR_CONDUCTIVITY: conductivity_sensor,
            FLOW_SENSOR_ILLUMINANCE: illuminance_sensor,
            FLOW_SENSOR_HUMIDITY: humidity_sensor,
        },
    }


@pytest.fixture
def plant_config_data() -> dict[str, Any]:
    """Return standard plant configuration data."""
    return create_plant_config_data()


@pytest.fixture
def plant_config_data_no_sensors() -> dict[str, Any]:
    """Return plant configuration data without external sensors."""
    return create_plant_config_data(
        temperature_sensor=None,
        moisture_sensor=None,
        conductivity_sensor=None,
        illuminance_sensor=None,
        humidity_sensor=None,
    )


@pytest.fixture
def plant_config_data_with_opb() -> dict[str, Any]:
    """Return plant configuration data from OpenPlantbook."""
    return create_plant_config_data(
        data_source=DATA_SOURCE_PLANTBOOK,
        limits={
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
            CONF_MAX_DLI: 22,  # Calculated from max_light_mmol
            CONF_MIN_DLI: 5,  # Calculated from min_light_mmol
        },
        entity_picture=GET_RESULT_MONSTERA_DELICIOSA["image_url"],
    )


@pytest.fixture
def mock_config_entry(plant_config_data: dict[str, Any]) -> MockConfigEntry:
    """Create a mock config entry for the plant integration."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=TEST_PLANT_NAME,
        data=plant_config_data,
        entry_id=TEST_ENTRY_ID,
        unique_id=TEST_ENTRY_ID,
    )


@pytest.fixture
def mock_config_entry_no_sensors(
    plant_config_data_no_sensors: dict[str, Any],
) -> MockConfigEntry:
    """Create a mock config entry without external sensors."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=TEST_PLANT_NAME,
        data=plant_config_data_no_sensors,
        entry_id=TEST_ENTRY_ID,
        unique_id=TEST_ENTRY_ID,
    )


@pytest.fixture
def mock_config_entry_with_opb(
    plant_config_data_with_opb: dict[str, Any],
) -> MockConfigEntry:
    """Create a mock config entry with OpenPlantbook data."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=TEST_PLANT_NAME,
        data=plant_config_data_with_opb,
        entry_id=TEST_ENTRY_ID,
        unique_id=TEST_ENTRY_ID,
    )


@pytest.fixture
def mock_openplantbook_services() -> Generator[MagicMock, None, None]:
    """Mock the OpenPlantbook services."""

    async def mock_search(domain, service, service_data, blocking, return_response):
        """Mock search service."""
        alias = service_data.get("alias", "").lower()
        if "monstera" in alias:
            return SEARCH_RESULT_MONSTERA
        return {}

    async def mock_get(domain, service, service_data, blocking, return_response):
        """Mock get service."""
        species = service_data.get("species", "").lower()
        if species == "monstera deliciosa":
            return GET_RESULT_MONSTERA_DELICIOSA
        return None

    async def mock_service_call(
        domain, service, service_data=None, blocking=False, return_response=False
    ):
        """Route service calls to appropriate mock."""
        if domain == DOMAIN_PLANTBOOK:
            if service == "search":
                return await mock_search(
                    domain, service, service_data, blocking, return_response
                )
            elif service == "get":
                return await mock_get(
                    domain, service, service_data, blocking, return_response
                )
        return None

    with patch(
        "homeassistant.core.ServiceRegistry.async_services",
        return_value={DOMAIN_PLANTBOOK: {"search": None, "get": None}},
    ):
        with patch(
            "homeassistant.core.ServiceRegistry.async_call",
            side_effect=mock_service_call,
        ):
            yield


@pytest.fixture
def mock_no_openplantbook() -> Generator[MagicMock, None, None]:
    """Mock absence of OpenPlantbook integration."""
    with patch(
        "homeassistant.core.ServiceRegistry.async_services",
        return_value={},
    ):
        yield


async def setup_mock_external_sensors(
    hass: HomeAssistant,
    temperature: float = 22.0,
    moisture: float = 45.0,
    conductivity: float = 800.0,
    illuminance: float = 5000.0,
    humidity: float = 55.0,
) -> None:
    """Set up mock external sensor states."""
    hass.states.async_set(
        "sensor.test_temperature",
        str(temperature),
        {"unit_of_measurement": "°C", "device_class": "temperature"},
    )
    hass.states.async_set(
        "sensor.test_moisture",
        str(moisture),
        {"unit_of_measurement": "%", "device_class": "moisture"},
    )
    hass.states.async_set(
        "sensor.test_conductivity",
        str(conductivity),
        {"unit_of_measurement": "µS/cm", "device_class": "conductivity"},
    )
    hass.states.async_set(
        "sensor.test_illuminance",
        str(illuminance),
        {"unit_of_measurement": "lx", "device_class": "illuminance"},
    )
    hass.states.async_set(
        "sensor.test_humidity",
        str(humidity),
        {"unit_of_measurement": "%", "device_class": "humidity"},
    )


@pytest.fixture
async def mock_external_sensors(hass: HomeAssistant) -> None:
    """Fixture to set up mock external sensors."""
    await setup_mock_external_sensors(hass)


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_external_sensors: None,
) -> MockConfigEntry:
    """Initialize the plant integration for testing."""
    mock_config_entry.add_to_hass(hass)

    # Set up the integration
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    return mock_config_entry


@pytest.fixture
async def init_integration_no_sensors(
    hass: HomeAssistant,
    mock_config_entry_no_sensors: MockConfigEntry,
) -> MockConfigEntry:
    """Initialize the plant integration without external sensors."""
    mock_config_entry_no_sensors.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry_no_sensors.entry_id)
    await hass.async_block_till_done()

    return mock_config_entry_no_sensors
