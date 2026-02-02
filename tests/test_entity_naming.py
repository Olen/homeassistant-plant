"""Tests for entity naming with multiple plants.

Ensures that entity IDs include the plant name so that multiple plants
don't produce colliding entity IDs (e.g. sensor.co2 vs sensor.co2_2).

Regression test for https://github.com/Olen/homeassistant-plant/issues/331
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant.const import DOMAIN

from .conftest import create_plant_config_data, setup_mock_external_sensors


async def _setup_plant(
    hass: HomeAssistant,
    name: str,
    entry_id: str,
    *,
    temperature_sensor: str | None = None,
    moisture_sensor: str | None = None,
    conductivity_sensor: str | None = None,
    illuminance_sensor: str | None = None,
    humidity_sensor: str | None = None,
    co2_sensor: str | None = None,
    soil_temperature_sensor: str | None = None,
) -> MockConfigEntry:
    """Set up a single plant and return its config entry."""
    config_data = create_plant_config_data(
        name=name,
        temperature_sensor=temperature_sensor,
        moisture_sensor=moisture_sensor,
        conductivity_sensor=conductivity_sensor,
        illuminance_sensor=illuminance_sensor,
        humidity_sensor=humidity_sensor,
        co2_sensor=co2_sensor,
        soil_temperature_sensor=soil_temperature_sensor,
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=name,
        data=config_data,
        entry_id=entry_id,
        unique_id=entry_id,
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _slugify(name: str) -> str:
    """Approximate HA slugify for entity_id checks."""
    return name.lower().replace(" ", "_").replace("-", "_")


class TestEntityNamingSinglePlant:
    """Test that a single plant's entities include the plant name."""

    async def test_sensor_entity_ids_contain_plant_name(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that sensor entity IDs contain the plant name."""
        entity_registry = er.async_get(hass)
        entities = er.async_entries_for_config_entry(
            entity_registry, init_integration.entry_id
        )

        sensor_entities = [e for e in entities if e.entity_id.startswith("plant.")]
        plant_slug = _slugify("Test Plant")

        for entity in sensor_entities:
            assert plant_slug in entity.entity_id, (
                f"Entity {entity.entity_id} (unique_id={entity.unique_id}) "
                f"does not contain plant name '{plant_slug}'"
            )

    async def test_number_entity_ids_contain_plant_name(
        self,
        hass: HomeAssistant,
        init_integration: MockConfigEntry,
    ) -> None:
        """Test that number (threshold) entity IDs contain the plant name."""
        entity_registry = er.async_get(hass)
        entities = er.async_entries_for_config_entry(
            entity_registry, init_integration.entry_id
        )

        # Number entities use the plant domain for entity_id generation
        number_entities = [
            e
            for e in entities
            if e.entity_id.startswith("number.")
            or (
                e.entity_id.startswith("plant.")
                and any(kw in e.entity_id for kw in ("max_", "min_", "lux_to_ppfd"))
            )
        ]
        plant_slug = _slugify("Test Plant")

        for entity in number_entities:
            assert plant_slug in entity.entity_id, (
                f"Entity {entity.entity_id} (unique_id={entity.unique_id}) "
                f"does not contain plant name '{plant_slug}'"
            )


class TestEntityNamingMultiplePlants:
    """Test that multiple plants produce unique, non-colliding entity IDs."""

    async def test_two_plants_no_entity_id_collisions(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that two plants produce unique entity IDs without _2 suffixes."""
        # Set up external sensors for both plants
        hass.states.async_set(
            "sensor.fern_temperature",
            "22.0",
            {"unit_of_measurement": "°C", "device_class": "temperature"},
        )
        hass.states.async_set(
            "sensor.fern_moisture",
            "45.0",
            {"unit_of_measurement": "%", "device_class": "moisture"},
        )
        hass.states.async_set(
            "sensor.fern_illuminance",
            "5000.0",
            {"unit_of_measurement": "lx", "device_class": "illuminance"},
        )
        hass.states.async_set(
            "sensor.cactus_temperature",
            "25.0",
            {"unit_of_measurement": "°C", "device_class": "temperature"},
        )
        hass.states.async_set(
            "sensor.cactus_moisture",
            "20.0",
            {"unit_of_measurement": "%", "device_class": "moisture"},
        )
        hass.states.async_set(
            "sensor.cactus_illuminance",
            "8000.0",
            {"unit_of_measurement": "lx", "device_class": "illuminance"},
        )

        entry1 = await _setup_plant(
            hass,
            name="My Fern",
            entry_id="entry_fern_001",
            temperature_sensor="sensor.fern_temperature",
            moisture_sensor="sensor.fern_moisture",
            illuminance_sensor="sensor.fern_illuminance",
        )
        entry2 = await _setup_plant(
            hass,
            name="My Cactus",
            entry_id="entry_cactus_002",
            temperature_sensor="sensor.cactus_temperature",
            moisture_sensor="sensor.cactus_moisture",
            illuminance_sensor="sensor.cactus_illuminance",
        )

        entity_registry = er.async_get(hass)
        entities1 = er.async_entries_for_config_entry(entity_registry, entry1.entry_id)
        entities2 = er.async_entries_for_config_entry(entity_registry, entry2.entry_id)

        all_entity_ids = [e.entity_id for e in entities1 + entities2]

        # No entity_id should appear more than once
        counts = Counter(all_entity_ids)
        duplicates = {eid: c for eid, c in counts.items() if c > 1}
        assert not duplicates, f"Duplicate entity IDs found: {duplicates}"

        # No entity_id should have a _2, _3, etc. suffix from collision resolution
        for eid in all_entity_ids:
            assert not any(
                eid.endswith(f"_{n}") for n in range(2, 10)
            ), f"Entity ID '{eid}' has a numeric suffix indicating a collision"

    async def test_two_plants_entities_contain_respective_names(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that each plant's entities contain its own name, not the other's."""
        await setup_mock_external_sensors(hass)

        # Second plant uses different external sensors
        hass.states.async_set(
            "sensor.rose_temperature",
            "20.0",
            {"unit_of_measurement": "°C", "device_class": "temperature"},
        )
        hass.states.async_set(
            "sensor.rose_moisture",
            "50.0",
            {"unit_of_measurement": "%", "device_class": "moisture"},
        )
        hass.states.async_set(
            "sensor.rose_conductivity",
            "600.0",
            {"unit_of_measurement": "µS/cm", "device_class": "conductivity"},
        )
        hass.states.async_set(
            "sensor.rose_illuminance",
            "3000.0",
            {"unit_of_measurement": "lx", "device_class": "illuminance"},
        )
        hass.states.async_set(
            "sensor.rose_humidity",
            "60.0",
            {"unit_of_measurement": "%", "device_class": "humidity"},
        )
        hass.states.async_set(
            "sensor.rose_co2",
            "500.0",
            {"unit_of_measurement": "ppm", "device_class": "carbon_dioxide"},
        )
        hass.states.async_set(
            "sensor.rose_soil_temperature",
            "19.0",
            {"unit_of_measurement": "°C", "device_class": "temperature"},
        )

        entry1 = await _setup_plant(
            hass,
            name="Green Fern",
            entry_id="entry_greenfern_001",
            temperature_sensor="sensor.test_temperature",
            moisture_sensor="sensor.test_moisture",
            conductivity_sensor="sensor.test_conductivity",
            illuminance_sensor="sensor.test_illuminance",
            humidity_sensor="sensor.test_humidity",
            co2_sensor="sensor.test_co2",
            soil_temperature_sensor="sensor.test_soil_temperature",
        )
        entry2 = await _setup_plant(
            hass,
            name="Red Rose",
            entry_id="entry_redrose_002",
            temperature_sensor="sensor.rose_temperature",
            moisture_sensor="sensor.rose_moisture",
            conductivity_sensor="sensor.rose_conductivity",
            illuminance_sensor="sensor.rose_illuminance",
            humidity_sensor="sensor.rose_humidity",
            co2_sensor="sensor.rose_co2",
            soil_temperature_sensor="sensor.rose_soil_temperature",
        )

        entity_registry = er.async_get(hass)

        fern_entities = er.async_entries_for_config_entry(
            entity_registry, entry1.entry_id
        )
        rose_entities = er.async_entries_for_config_entry(
            entity_registry, entry2.entry_id
        )

        fern_slug = _slugify("Green Fern")
        rose_slug = _slugify("Red Rose")

        for entity in fern_entities:
            assert (
                fern_slug in entity.entity_id
            ), f"Fern entity '{entity.entity_id}' does not contain '{fern_slug}'"
            assert (
                rose_slug not in entity.entity_id
            ), f"Fern entity '{entity.entity_id}' contains other plant name '{rose_slug}'"

        for entity in rose_entities:
            assert (
                rose_slug in entity.entity_id
            ), f"Rose entity '{entity.entity_id}' does not contain '{rose_slug}'"
            assert (
                fern_slug not in entity.entity_id
            ), f"Rose entity '{entity.entity_id}' contains other plant name '{fern_slug}'"

        # Cleanup
        for entry in (entry1, entry2):
            if hass.config_entries.async_get_entry(entry.entry_id):
                await hass.config_entries.async_unload(entry.entry_id)
                await hass.async_block_till_done()

    async def test_three_plants_all_unique_entity_ids(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that three plants with no external sensors still get unique IDs."""
        entries = []
        for i, name in enumerate(["Aloe Vera", "Snake Plant", "Spider Plant"]):
            entry = await _setup_plant(
                hass,
                name=name,
                entry_id=f"entry_{i:03d}",
            )
            entries.append(entry)

        entity_registry = er.async_get(hass)
        all_entity_ids = []
        for entry in entries:
            entities = er.async_entries_for_config_entry(
                entity_registry, entry.entry_id
            )
            all_entity_ids.extend(e.entity_id for e in entities)

        # Every entity_id must be unique
        counts = Counter(all_entity_ids)
        duplicates = {eid: c for eid, c in counts.items() if c > 1}
        assert not duplicates, f"Duplicate entity IDs with 3 plants: {duplicates}"

        # No collision suffixes
        for eid in all_entity_ids:
            assert not any(
                eid.endswith(f"_{n}") for n in range(2, 10)
            ), f"Entity ID '{eid}' has collision suffix"

        # Cleanup
        for entry in entries:
            if hass.config_entries.async_get_entry(entry.entry_id):
                await hass.config_entries.async_unload(entry.entry_id)
                await hass.async_block_till_done()
