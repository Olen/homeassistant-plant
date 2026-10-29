# Home Assistant compatibility

Plant supports a range of Home Assistant versions. Code that only exists because of an older (or newer) HA version is listed here, so we can see what goes away when the minimum supported version is raised.

**Current range**

- Declared minimum: **2025.8.0** (`hacs.json`)
- Lowest version tested in CI: **2026.3** (the first HA that requires Python 3.14; see `.github/workflows/CI.yml`)
- Also tested: latest stable, and the latest beta (non-blocking)

## Workarounds by HA version

Sorted by the version that makes each one unnecessary. Raising the minimum to a version means everything up to and including that row can be removed.

| Needed on HA below | What | Where | Once the minimum is at least that version |
|---|---|---|---|
| 2026.7 | `plant.*` triggers and conditions stay inert when the purpose-trigger API is missing | `trigger.py` `_has_purpose_trigger_api()`, `condition.py` `_has_purpose_condition_api()`; test `tests/test_automation_version_safety.py` | Drop the checks and their test |
| 2026.7 | PPM unit falls back to `CONCENTRATION_PARTS_PER_MILLION` when `UnitOfRatio` is missing | `sensor.py`, the `try`/`except ImportError` around `_UNIT_PPM` | Import `UnitOfRatio` directly |
| 2026.8 | `hass` is passed to `IntegrationSensor`, `StatisticsSensor` and `UtilityMeterSensor` only where their `__init__` still takes it | `sensor.py` `_init_accepts_hass()` and the three `_*_ACCEPTS_HASS` flags | Never pass `hass`; drop the helper |
| 2026.11 | `device_class=None` is passed to `IntegrationSensor` only where it's a parameter (required from 2026.11) | `sensor.py` `_INTEGRATION_SENSOR_TAKES_DEVICE_CLASS` | Always pass `device_class=None` |
| 2026.11 | Threshold numbers skip restoring state for a brand-new entity that reuses an old entity_id. HA does this itself from 2026.11 (#542) | `number.py` `_is_new_entity` | Drop the guard |
| 2026.11 | `async_entity_id_changed` only calls `super()` where `Entity` has the method (added in 2026.11) | `PlantDevice`, `PlantMinMax`, `PlantCurrentStatus`, `PlantCurrentVpd`, `PlantDailyLightIntegral24h` | Call `super().async_entity_id_changed()` directly |
| 2026.11 (tests) | Tests read `DeviceInfo` as dict or dataclass (#540, PR #548) | `tests/conftest.py` `device_info_field()` | Use attribute access; drop the helper |

## Test-environment workarounds

HA 2026.11 replaced `pytest-homeassistant-custom-component` with the official `pytest-home-assistant`. CI uses the official package for the beta job and the old one for the others, so the tests work with both.

| What | Where | Remove when |
|---|---|---|
| Test helpers imported from whichever package is installed | `tests/ha_common.py` (`OFFICIAL_TEST_PACKAGE`) | Every CI job uses `pytest-home-assistant`; then import from `pytest_homeassistant.common` directly |
| `pytest_plugins` and the `enable_custom_integrations` fixture only with the old package (the official one loads itself and enables custom integrations) | `tests/conftest.py` | Same |
| `pytest-home-assistant` installed from the core tag of the beta, as it is not on PyPI yet | `.github/workflows/CI.yml`, beta job | It is published on PyPI |

## Upcoming requirements

Not workarounds yet, but they set a deadline:

- **2027.11:** entities without `async_entity_id_changed` stop being removed and re-added on a rename. Plant's entities have it (#539); a new class that implements `async_added_to_hass` or `async_will_remove_from_hass` needs it too. `tests/test_entity_id_change.py` checks this on HA 2026.11+.
- **2027.8:** `CONCENTRATION_PARTS_PER_MILLION` is removed. The PPM fallback above only uses it on HA < 2026.7, so this is fine as long as that row is removed before the minimum gets anywhere near 2027.8.

## Not tied to an HA version

Compatibility with **older plant data**, kept regardless of the HA minimum:

- Existing entities keep their old entity_ids (`async_generate_entity_id` for entities already in the registry): `number.py`, `sensor.py`.
- Config entries without a `limits_temperature_unit` marker use their stored temperature limits as-is: `number.py` `_get_temperature_default()`.

## When raising the minimum

1. Remove every row up to the new version, and the tests that only cover the old path.
2. Update `hacs.json` (`homeassistant`) and the lowest CI lane in `.github/workflows/CI.yml`.
3. Update this file.

When adding a new workaround, add a row here in the same PR.
