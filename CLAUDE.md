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

## Git Workflow

**Always use feature branches for code changes.** Do not commit directly to master.

```bash
# Create a branch for your work
git checkout -b feature-name

# After changes, push and create PR
git push -u origin feature-name
gh pr create --fill
```

The master branch is protected - all changes must go through pull requests.

## Releases

Releases are automated via GitHub Actions. The workflow triggers when `manifest.json` version changes.

**To create a new release:**

1. Update the version in `custom_components/plant/manifest.json`
2. Commit and push to main (or merge PR)
3. The CI workflow runs tests, then the release workflow creates a GitHub release

**Version format:**
- Stable: `YYYY.M.P` (e.g., `2026.1.0`)
- Beta: `YYYY.M.P-betaN` (e.g., `2026.1.0-beta5`)

**Do NOT manually create tags** - the release workflow handles this automatically based on the manifest version.

## Translations

Translation files in `custom_components/plant/translations/`:
- Use abbreviated forms (Max/Min) for entity names due to GUI space constraints
- Each language uses appropriate abbreviations (Maks./Min., Maxi./Mini., etc.)
- Services section should be present in all translation files
