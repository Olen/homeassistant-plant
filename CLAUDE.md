# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a custom Home Assistant integration for plant monitoring. It replaces the built-in `plant` component with an enhanced version that treats plants as devices with multiple entities. It integrates with OpenPlantbook for automatic threshold data retrieval.

**Domain:** `plant`
**Minimum HA Version:** 2025.8.0

## Build & Lint Commands

```bash
# Setup (one time)
uv venv
uv pip install pytest pytest-asyncio pytest-cov pytest-timeout pytest-homeassistant-custom-component syrupy black

# Format check (used in CI)
uv run black . --check --fast --diff

# Format code
uv run black .

# Run tests
uv run pytest tests/ -v

# Run tests with coverage
uv run pytest tests/ --cov=custom_components/plant --cov-report=term-missing

# Validate Home Assistant integration manifest
# Run via hassfest action or within HA dev container
```

See DEVELOPMENT.md for full development setup instructions.

## Architecture

### Core Components

- **`__init__.py`** - Main integration setup. Defines `PlantDevice` entity class which is the primary plant entity. Handles config entry setup, device registry, and the `plant.replace_sensor` service.

- **`config_flow.py`** - Multi-step config flow for plant setup:
  1. Name/species input and sensor selection
  2. OpenPlantbook species search (if available)
  3. Threshold limits configuration

  Also handles `OptionsFlowHandler` for reconfiguring plants (species changes, image updates, problem triggers).

- **`sensor.py`** - Sensor entities for each plant:
  - `PlantCurrentStatus` (base class) - Tracks external sensors for moisture, temperature, conductivity, illuminance, humidity
  - `PlantCurrentPpfd` - Calculates PPFD from illuminance
  - `PlantTotalLightIntegral` - Integration sensor for cumulative light
  - `PlantDailyLightIntegral` - Utility meter for DLI calculation
  - Dummy sensors for testing (enabled via `SETUP_DUMMY_SENSORS` flag)

- **`number.py`** - Threshold entities (min/max for each measurement type). Uses `RestoreNumber` for persistence. Entities are `EntityCategory.CONFIG`.

- **`plant_helpers.py`** - `PlantHelper` class for OpenPlantbook integration:
  - `openplantbook_search()` - Search for species
  - `openplantbook_get()` - Get detailed plant data
  - `generate_configentry()` - Build config entry from OPB data or defaults

- **`const.py`** - All constants, defaults, and configuration key mappings including `CONF_PLANTBOOK_MAPPING` for OPB field translation.

### Entity Structure per Plant

Each plant creates:
- 1 `PlantDevice` entity (main plant state: ok/problem/unknown)
- 5 sensor entities (moisture, temperature, conductivity, illuminance, humidity)
- 12 number entities (min/max thresholds for 6 measurement types)
- 3 calculated sensors (PPFD, total integral, DLI)

### Key Patterns

- Plants are HA devices with identifiers `{(DOMAIN, unique_id)}`
- External physical sensors are tracked and their values copied to plant-owned sensors
- Service `plant.replace_sensor` allows changing the external sensor for any measurement type
- Temperature thresholds respect HA's configured unit system (°C/°F)
- DLI is calculated from illuminance via PPFD conversion: `lux * 0.0185 / 1000000`

### OpenPlantbook Integration

The integration optionally depends on the `openplantbook` integration. When available:
- Thresholds are auto-populated from OPB data
- Species search is available during setup
- Images are fetched from OPB

Without OPB, default threshold values from `const.py` are used.

## Configuration Flow States

1. `user` - Name, species, sensor selection
2. `select_species` - OPB search results dropdown (skipped if no OPB)
3. `limits` - Threshold values and image configuration
4. `limits_done` - Entry creation

## Websocket API

- `plant/get_info` - Returns plant data including current readings and thresholds for Lovelace cards
