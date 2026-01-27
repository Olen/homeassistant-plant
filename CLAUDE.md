# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project Overview

Custom Home Assistant integration for plant monitoring. Replaces the built-in `plant` component with an enhanced version that treats plants as devices with multiple entities.

**Domain:** `plant`
**Minimum HA Version:** 2025.8.0

## Related Repositories

This integration is part of a plant monitoring ecosystem:

- **[home-assistant-openplantbook](https://github.com/Olen/home-assistant-openplantbook)** - OpenPlantbook API integration that provides species data and thresholds
- **[lovelace-flower-card](https://github.com/Olen/lovelace-flower-card)** - Lovelace card for displaying plant data (uses the websocket API)

## Quick Commands

```bash
# Format check (CI uses this)
.venv/bin/black . --check --fast --diff

# Format code
.venv/bin/black .

# Run tests
.venv/bin/pytest tests/ -v

# Run tests with coverage
.venv/bin/pytest tests/ --cov=custom_components/plant --cov-report=term-missing
```

See DEVELOPMENT.md for full setup instructions.

## Architecture

### Core Files

| File | Purpose |
|------|---------|
| `__init__.py` | Integration setup, `PlantDevice` entity, `plant.replace_sensor` service |
| `config_flow.py` | Multi-step config flow + `OptionsFlowHandler` for editing plants |
| `sensor.py` | Sensor entities: current values, PPFD, TLI, DLI |
| `number.py` | Threshold entities (min/max) using `RestoreNumber` |
| `plant_helpers.py` | `PlantHelper` class for OpenPlantbook API calls |
| `const.py` | Constants, defaults, `CONF_PLANTBOOK_MAPPING` |

### Entity Structure per Plant

- 1 `PlantDevice` (main state: ok/problem/unknown)
- 8 sensor entities (moisture, temperature, conductivity, illuminance, humidity, CO2, soil_temperature + PPFD, TLI, DLI)
- 16 number entities (min/max thresholds for 8 measurement types)

### Config Flow Steps

1. `user` - Name, species, sensor selection
2. `select_species` - OpenPlantbook search results (skipped if no OPB)
3. `limits` - Threshold values and image
4. `limits_done` - Entry creation

### Websocket API

`plant/get_info` - Returns plant data for Lovelace cards (used by lovelace-flower-card)

## Key Patterns

- Plants are HA devices with identifiers `{(DOMAIN, unique_id)}`
- External sensors are tracked; values copied to plant-owned sensors
- Service `plant.replace_sensor` changes the external sensor for any measurement
- Temperature thresholds respect HA's configured unit system
- DLI calculated from illuminance: `lux * lux_to_ppfd_factor / 1000000`

## Translations

Translation files in `custom_components/plant/translations/`:
- Use abbreviated forms (Max/Min) for entity names due to GUI space constraints
- Each language uses appropriate abbreviations (Maks./Min., Maxi./Mini., etc.)
- Services section should be present in all translation files
