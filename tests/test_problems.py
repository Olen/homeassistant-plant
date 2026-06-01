"""Tests for the problems attribute on plant entities.

The _problems list is built during PlantDevice.update() and exposed as
the 'problems' entity attribute. Each entry is a dict describing an
active problem (sensor_type, status, current value, min/max thresholds).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.const import STATE_PROBLEM, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache_with_extra_data,
)

from custom_components.plant.const import (
    ATTR_CONDUCTIVITY,
    ATTR_HUMIDITY,
    ATTR_MOISTURE,
    ATTR_PLANT,
    ATTR_PROBLEMS,
    ATTR_TEMPERATURE,
    DOMAIN,
    STATE_HIGH,
    STATE_LOW,
)

from .common import set_external_sensor_states, update_plant_sensors


class TestProblemsAttribute:
    """Tests for the problems attribute on plant entities."""

    async def test_problems_empty_when_healthy(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that problems list is empty when plant is healthy."""
        await set_external_sensor_states(
            hass,
            moisture=50,
            temperature=25,
            conductivity=1000,
            illuminance=5000,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        assert plant._problems == []

    @pytest.mark.parametrize(
        "sensor_kwargs, expected_type, expected_status",
        [
            (
                {"moisture": 5.0, "temperature": 25.0, "conductivity": 1000},
                ATTR_MOISTURE,
                STATE_LOW,
            ),
            (
                {"moisture": 80.0, "temperature": 25.0, "conductivity": 1000},
                ATTR_MOISTURE,
                STATE_HIGH,
            ),
            (
                {"moisture": 50.0, "temperature": 5.0, "conductivity": 1000},
                ATTR_TEMPERATURE,
                STATE_LOW,
            ),
            (
                {"moisture": 50.0, "temperature": 45.0, "conductivity": 1000},
                ATTR_TEMPERATURE,
                STATE_HIGH,
            ),
            (
                {"moisture": 50.0, "temperature": 25.0, "conductivity": 100},
                ATTR_CONDUCTIVITY,
                STATE_LOW,
            ),
            (
                {"moisture": 50.0, "temperature": 25.0, "conductivity": 5000},
                ATTR_CONDUCTIVITY,
                STATE_HIGH,
            ),
            (
                {"moisture": 50.0, "temperature": 25.0, "humidity": 5.0},
                ATTR_HUMIDITY,
                STATE_LOW,
            ),
            (
                {"moisture": 50.0, "temperature": 25.0, "humidity": 80.0},
                ATTR_HUMIDITY,
                STATE_HIGH,
            ),
        ],
        ids=[
            "moisture_low",
            "moisture_high",
            "temperature_low",
            "temperature_high",
            "conductivity_low",
            "conductivity_high",
            "humidity_low",
            "humidity_high",
        ],
    )
    async def test_problem_entry_structure(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
        sensor_kwargs: dict,
        expected_type: str,
        expected_status: str,
    ) -> None:
        """Test that each problem entry has the correct structure and values."""
        await set_external_sensor_states(hass, **sensor_kwargs)
        await update_plant_sensors(hass, init_integration.entry_id)

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]

        # Find the problem for our expected sensor type
        matching = [p for p in plant._problems if p["sensor_type"] == expected_type]
        assert len(matching) == 1, (
            f"Expected 1 problem for {expected_type}, "
            f"got {len(matching)}: {plant._problems}"
        )

        problem = matching[0]
        assert problem["status"] == expected_status
        # Verify all required keys are present
        assert "current" in problem
        assert "min" in problem
        assert "max" in problem
        # current should be a string representation of the sensor value
        assert isinstance(problem["current"], str)

    async def test_multiple_problems_listed(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that multiple simultaneous problems are all listed."""
        await set_external_sensor_states(
            hass,
            moisture=5.0,  # Too low (min: 20)
            temperature=45.0,  # Too high (max: 40)
            conductivity=1000,
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        problem_types = {p["sensor_type"] for p in plant._problems}
        assert ATTR_MOISTURE in problem_types
        assert ATTR_TEMPERATURE in problem_types
        assert len(plant._problems) == 2

    async def test_problems_cleared_on_recovery(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that problems list is cleared when values return to normal."""
        # Cause a problem
        await set_external_sensor_states(
            hass, moisture=5.0, temperature=25.0, conductivity=1000
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        assert len(plant._problems) == 1

        # Fix it (clear hysteresis: min=20, band=2.0, so need > 22)
        await set_external_sensor_states(hass, moisture=50.0)
        await update_plant_sensors(hass, init_integration.entry_id)

        assert plant._problems == []


class TestLogbookIntegration:
    """Tests for logbook entries on plant problem changes."""

    async def test_logbook_called_when_problem_appears(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that log_entry is called when a new problem appears."""
        with patch("custom_components.plant.log_entry") as mock_log:
            await set_external_sensor_states(
                hass, moisture=5.0, temperature=25.0, conductivity=1000
            )
            await update_plant_sensors(hass, init_integration.entry_id)

        assert mock_log.called
        message = mock_log.call_args[0][2]
        assert "moisture" in message
        assert "low" in message

    async def test_logbook_called_on_recovery(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that log_entry is called when a problem is resolved."""
        plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
        # Pre-seed a tracked problem so recovery can be detected
        plant._logged_problem_types = {ATTR_MOISTURE}

        with patch("custom_components.plant.log_entry") as mock_log:
            await set_external_sensor_states(
                hass, moisture=50.0, temperature=25.0, conductivity=1000
            )
            await update_plant_sensors(hass, init_integration.entry_id)

        assert mock_log.called
        message = mock_log.call_args[0][2]
        assert "moisture" in message
        assert "back in range" in message

    async def test_logbook_not_called_when_problems_unchanged(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that log_entry is not called when problems don't change."""
        # First update — causes a moisture problem and logs it
        await set_external_sensor_states(
            hass, moisture=5.0, temperature=25.0, conductivity=1000
        )
        await update_plant_sensors(hass, init_integration.entry_id)

        # Second update — same problem still active, should not log again
        with patch("custom_components.plant.log_entry") as mock_log:
            await update_plant_sensors(hass, init_integration.entry_id)

        assert not mock_log.called

    async def test_active_problems_not_relogged_after_restart(
        self,
        hass: HomeAssistant,
        plant_config_data: dict,
        mock_no_openplantbook,
    ) -> None:
        """Problems still active after a restart are not re-logged as new onsets.

        On restart ``_logged_problem_types`` is restored from the persisted
        ``problems`` attribute, so a problem that was already logged before the
        restart is not written to the logbook again.
        """
        # Simulate a restart: the plant was in PROBLEM with moisture already low.
        mock_restore_cache_with_extra_data(
            hass,
            [
                (
                    State(
                        "plant.test_plant",
                        STATE_PROBLEM,
                        {
                            "moisture_status": STATE_LOW,
                            ATTR_PROBLEMS: [
                                {
                                    "sensor_type": ATTR_MOISTURE,
                                    "status": STATE_LOW,
                                    "current": "5.0",
                                    "min": "20",
                                    "max": "60",
                                }
                            ],
                        },
                    ),
                    {},
                )
            ],
        )

        # Sources unavailable during startup, so the restore window holds the
        # restored problem state instead of recomputing it away immediately.
        for source_entity_id in (
            "sensor.test_moisture",
            "sensor.test_temperature",
            "sensor.test_conductivity",
            "sensor.test_illuminance",
            "sensor.test_humidity",
            "sensor.test_co2",
            "sensor.test_soil_temperature",
        ):
            hass.states.async_set(source_entity_id, STATE_UNAVAILABLE)

        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data=plant_config_data,
            entry_id="problems_restore_entry",
            title="Test Plant",
        )
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][config_entry.entry_id][ATTR_PLANT]
        # The active problem was restored as already-logged.
        assert plant._logged_problem_types == {ATTR_MOISTURE}

        # A live reading arrives with the same problem still active -> the
        # restore window ends and update() runs, but moisture must NOT be
        # re-logged as a new onset.
        with patch("custom_components.plant.log_entry") as mock_log:
            await set_external_sensor_states(
                hass, moisture=5.0, temperature=25.0, conductivity=1000
            )
            await update_plant_sensors(hass, config_entry.entry_id)

        assert not mock_log.called

        await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()
