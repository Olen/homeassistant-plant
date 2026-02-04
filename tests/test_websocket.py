"""Tests for plant integration websocket API."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant.const import (
    ATTR_CONDUCTIVITY,
    ATTR_CURRENT,
    ATTR_DLI,
    ATTR_HUMIDITY,
    ATTR_ILLUMINANCE,
    ATTR_MAX,
    ATTR_MIN,
    ATTR_MOISTURE,
    ATTR_PLANT,
    ATTR_SENSOR,
    ATTR_TEMPERATURE,
    DOMAIN,
)


class TestWebsocketGetInfo:
    """Tests for plant/get_info websocket command."""

    async def test_websocket_get_info_success(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
        hass_ws_client,
    ) -> None:
        """Test successful websocket get_info request."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Ensure plant is complete
        plant.plant_complete = True

        client = await hass_ws_client(hass)

        await client.send_json(
            {
                "id": 1,
                "type": "plant/get_info",
                "entity_id": plant.entity_id,
            }
        )

        response = await client.receive_json()

        assert response["success"] is True
        assert "result" in response

        result = response["result"]["result"]
        assert ATTR_TEMPERATURE in result
        assert ATTR_MOISTURE in result
        assert ATTR_CONDUCTIVITY in result
        assert ATTR_ILLUMINANCE in result
        assert ATTR_HUMIDITY in result
        assert ATTR_DLI in result

    async def test_websocket_get_info_entity_structure(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
        hass_ws_client,
    ) -> None:
        """Test websocket response structure for each measurement type."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        plant.plant_complete = True

        client = await hass_ws_client(hass)

        await client.send_json(
            {
                "id": 1,
                "type": "plant/get_info",
                "entity_id": plant.entity_id,
            }
        )

        response = await client.receive_json()
        result = response["result"]["result"]

        # Check structure of temperature data
        temp_data = result[ATTR_TEMPERATURE]
        assert ATTR_MAX in temp_data
        assert ATTR_MIN in temp_data
        assert ATTR_CURRENT in temp_data
        assert "icon" in temp_data
        assert "unit_of_measurement" in temp_data
        assert ATTR_SENSOR in temp_data

    async def test_websocket_get_info_entity_not_found(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
        hass_ws_client,
    ) -> None:
        """Test websocket error when entity not found."""
        client = await hass_ws_client(hass)

        await client.send_json(
            {
                "id": 1,
                "type": "plant/get_info",
                "entity_id": "plant.nonexistent_plant",
            }
        )

        response = await client.receive_json()

        assert response["success"] is False
        assert response["error"]["code"] == "entity_not_found"

    async def test_websocket_get_info_domain_not_found(
        self,
        hass: HomeAssistant,
        hass_ws_client,
    ) -> None:
        """Test websocket error when domain not loaded."""
        # Don't initialize the integration - the websocket command won't be registered
        client = await hass_ws_client(hass)

        await client.send_json(
            {
                "id": 1,
                "type": "plant/get_info",
                "entity_id": "plant.test_plant",
            }
        )

        response = await client.receive_json()

        # When domain is not loaded, the websocket command is not registered
        # so we get "unknown_command" error
        assert response["success"] is False
        assert response["error"]["code"] == "unknown_command"

    async def test_websocket_get_info_plant_not_complete(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
        hass_ws_client,
    ) -> None:
        """Test websocket returns empty result when plant not complete."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Set plant as not complete
        plant.plant_complete = False

        client = await hass_ws_client(hass)

        await client.send_json(
            {
                "id": 1,
                "type": "plant/get_info",
                "entity_id": plant.entity_id,
            }
        )

        response = await client.receive_json()

        assert response["success"] is True
        # Result should be empty dict when not complete
        assert response["result"]["result"] == {}


    async def test_websocket_get_info_disabled_sensors(
        self,
        hass: HomeAssistant,
        init_integration_no_sensors: MockConfigEntry,
        hass_ws_client,
    ) -> None:
        """Test websocket returns partial result when sensors are disabled."""
        plant = hass.data[DOMAIN][init_integration_no_sensors.entry_id][ATTR_PLANT]

        # Plant is complete but sensors have no external source and are disabled
        plant.plant_complete = True

        client = await hass_ws_client(hass)

        await client.send_json(
            {
                "id": 1,
                "type": "plant/get_info",
                "entity_id": plant.entity_id,
            }
        )

        response = await client.receive_json()

        # Should succeed, not crash with unknown_error
        assert response["success"] is True
        assert "result" in response

        # Result should be a dict (possibly empty if all sensors disabled)
        result = response["result"]["result"]
        assert isinstance(result, dict)

        # Each included sensor should have the expected structure
        for attr_name in result:
            assert ATTR_MAX in result[attr_name]
            assert ATTR_MIN in result[attr_name]
            assert ATTR_CURRENT in result[attr_name]
            assert ATTR_SENSOR in result[attr_name]


class TestWebsocketRegistration:
    """Tests for websocket command registration."""

    async def test_websocket_command_registered(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
        hass_ws_client,
    ) -> None:
        """Test that websocket command is registered during setup."""
        # The websocket command should be registered and accessible
        # Verify by making a request that gets a valid response (even if error)
        client = await hass_ws_client(hass)

        await client.send_json(
            {
                "id": 1,
                "type": "plant/get_info",
                "entity_id": "plant.nonexistent",
            }
        )

        response = await client.receive_json()

        # If command is registered, we get an error response, not an unknown_command
        assert "error" in response
        # The error should be from our handler, not "unknown_command"
        assert response["error"]["code"] != "unknown_command"
        assert DOMAIN in hass.data
