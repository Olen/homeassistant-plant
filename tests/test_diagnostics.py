"""Tests for the plant diagnostics module."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant.diagnostics import async_get_config_entry_diagnostics


class TestDiagnostics:
    """Test diagnostics."""

    async def test_diagnostics_returns_data(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry, init_integration
    ):
        """Test that diagnostics returns expected data structure."""
        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Check basic structure
        assert "config_entry" in result
        assert result["config_entry"]["entry_id"] == mock_config_entry.entry_id
        assert result["config_entry"]["domain"] == "plant"
        assert result["config_entry"]["title"] == "Test Plant"

    async def test_diagnostics_includes_plant_data(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry, init_integration
    ):
        """Test that diagnostics includes plant entity data."""
        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Check plant data
        assert "plant" in result
        assert result["plant"]["entity_id"] == "plant.test_plant"
        assert result["plant"]["name"] == "Test Plant"

    async def test_diagnostics_includes_thresholds(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry, init_integration
    ):
        """Test that diagnostics includes threshold data."""
        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Check thresholds
        assert "thresholds" in result
        assert "max_moisture" in result["thresholds"]
        assert "min_moisture" in result["thresholds"]

    async def test_diagnostics_includes_triggers(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry, init_integration
    ):
        """Test that diagnostics includes trigger settings."""
        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Check triggers
        assert "triggers" in result
        assert "moisture" in result["triggers"]
        assert "temperature" in result["triggers"]

    async def test_diagnostics_includes_sensors(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry, init_integration
    ):
        """Test that diagnostics includes sensor data."""
        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Check sensors
        assert "sensors" in result
        assert len(result["sensors"]) > 0
        # Each sensor should have required fields
        for sensor in result["sensors"]:
            assert "entity_id" in sensor
            assert "name" in sensor
            assert "state" in sensor
