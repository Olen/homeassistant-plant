# Plant `plant.*` Triggers & Conditions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the full `plant.*` purpose-trigger and -condition surface for Home Assistant 2026.7+, auto-thresholded off the plant's own per-measurement status, while staying inert and import-clean on HA 2025.8–2026.6.

**Architecture:** A pure-data measurement table (`automation_meta.py`) is the single source of truth. `trigger.py` and `condition.py` expose `async_get_triggers`/`async_get_conditions`; both feature-detect the 2026.7 purpose-trigger API and return `{}` when it's absent, doing all 2026.7-only imports lazily inside a cached `_build_*()` helper. Status families are generated with core's `make_entity_target_state_trigger` / `make_entity_state_condition` reading the plant's `<m>_status` attribute via `DomainSpec(value_source=...)`. Stale families are a custom `Trigger`/`Condition` that resolves each measurement's external source sensor from the `PlantDevice` and watches *that* sensor.

**Tech Stack:** Python 3.13+, Home Assistant core helpers (`homeassistant.helpers.trigger`, `.condition`, `.automation`, `.target`, `.event`), pytest + `pytest-homeassistant-custom-component`, black, ruff.

## Global Constraints

- **HA version floor: 2025.8.** The integration must load cleanly on 2025.8+. `trigger.py`/`condition.py` MUST NOT import any of `make_entity_target_state_trigger`, `make_entity_state_condition`, `TriggerConfig`, `TriggerActionRunner`, `ConditionConfig`, `DomainSpec`, `TargetStateChangedData`, `async_track_target_selector_state_change_event` at module top level. All such imports happen lazily inside a `_build_*()` function guarded by feature detection.
- **Feature detection, not version strings:** gate on `hasattr(homeassistant.helpers.trigger, "make_entity_target_state_trigger")`.
- **`async_get_triggers`/`async_get_conditions` return `{}`** when the API is absent — no registration, no exception, no log noise.
- **Naming is verbatim from the spec** (copy exactly):
  - Aggregate triggers: `problem_detected`, `problem_cleared`; condition: `has_problem`.
  - Per-measurement status triggers: `<m>_became_low`, `<m>_became_high`, `<m>_became_ok`; conditions: `<m>_is_low`, `<m>_is_high`, `<m>_is_ok`.
  - Per-measurement stale triggers: `<m>_sensor_became_stale`, `<m>_sensor_became_fresh`; condition: `<m>_sensor_is_stale`.
- **Status measurements (9):** `moisture, conductivity, temperature, soil_temperature, humidity, illuminance, co2, dli, vpd`.
- **External measurements (7):** the above minus `dli, vpd` (and `ppfd`, which has no status). Stale families apply to external only.
- **Status values:** `STATE_LOW = "Low"`, `STATE_HIGH = "High"` (from `.const`); `STATE_OK = "ok"`, `STATE_PROBLEM = "problem"` (from `homeassistant.const`).
- **Stale default window:** 24h (`timedelta(hours=24)`), overridable via the trigger/condition `for:` option.
- **No `crossed_threshold` family** (explicit non-goal).
- Run `black custom_components/plant/ tests/` before every commit; keep `ruff` clean.
- Tests that exercise the 2026.7 API are gated to skip below 2026.7 (module-level skip, as the existing `tests/test_triggers.py` does).

---

### Task 1: Measurement metadata table + version-safe platform scaffolding

**Files:**
- Create: `custom_components/plant/automation_meta.py`
- Rewrite: `custom_components/plant/trigger.py` (replace strawman)
- Rewrite: `custom_components/plant/condition.py` (replace strawman)
- Rewrite: `tests/test_triggers.py` (replace strawman key-set tests; keep module skip guard)
- Create: `tests/test_automation_version_safety.py`

**Interfaces:**
- Produces: `automation_meta.Measurement` (NamedTuple `key: str`, `status_attr: str`, `device_sensor_attr: str | None`); `automation_meta.STATUS_MEASUREMENTS: tuple[Measurement, ...]`; `automation_meta.EXTERNAL_MEASUREMENTS: tuple[Measurement, ...]`.
- Produces: `trigger.async_get_triggers(hass) -> dict[str, type]`; `condition.async_get_conditions(hass) -> dict[str, type]`; both return `{}` when the 2026.7 API is absent.
- Produces: `trigger._has_purpose_trigger_api() -> bool`; `condition._has_purpose_condition_api() -> bool`.

- [ ] **Step 1: Write the measurement table (pure data, always import-safe)**

Create `custom_components/plant/automation_meta.py`:

```python
"""Shared metadata for the plant.* trigger/condition surface.

Pure data — safe to import on any Home Assistant version. The 2026.7-only
trigger/condition helper APIs are imported lazily inside trigger.py /
condition.py, never here.
"""

from __future__ import annotations

from typing import NamedTuple


class Measurement(NamedTuple):
    """One plant measurement and how the automation surface reaches it."""

    key: str
    """Name fragment and status-attribute prefix, e.g. "moisture"."""
    status_attr: str
    """Plant entity attribute holding Low/High/ok, e.g. "moisture_status"."""
    device_sensor_attr: str | None
    """PlantDevice attribute holding the external source sensor entity, or
    None for derived measurements (dli, vpd) that have no source of their own."""


# The 9 measurements that expose a <key>_status attribute (Low / High / ok).
STATUS_MEASUREMENTS: tuple[Measurement, ...] = (
    Measurement("moisture", "moisture_status", "sensor_moisture"),
    Measurement("conductivity", "conductivity_status", "sensor_conductivity"),
    Measurement("temperature", "temperature_status", "sensor_temperature"),
    Measurement(
        "soil_temperature", "soil_temperature_status", "sensor_soil_temperature"
    ),
    Measurement("humidity", "humidity_status", "sensor_humidity"),
    Measurement("illuminance", "illuminance_status", "sensor_illuminance"),
    Measurement("co2", "co2_status", "sensor_co2"),
    Measurement("dli", "dli_status", None),
    Measurement("vpd", "vpd_status", None),
)

# The 7 externally-sourced measurements (can go stale independently).
EXTERNAL_MEASUREMENTS: tuple[Measurement, ...] = tuple(
    m for m in STATUS_MEASUREMENTS if m.device_sensor_attr is not None
)
```

- [ ] **Step 2: Write the failing version-safety + key-set tests**

Create `tests/test_automation_version_safety.py`:

```python
"""The trigger/condition platforms must be import-clean and return {} when the
2026.7 purpose-trigger API is unavailable (HA 2025.8-2026.6)."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.plant import condition, trigger


async def test_triggers_empty_when_api_absent(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(trigger, "_has_purpose_trigger_api", lambda: False)
    assert await trigger.async_get_triggers(hass) == {}


async def test_conditions_empty_when_api_absent(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(condition, "_has_purpose_condition_api", lambda: False)
    assert await condition.async_get_conditions(hass) == {}
```

Replace the two key-set tests at the top of `tests/test_triggers.py` (keep the
module-level HA-version skip guard, lines 1-30, unchanged) with:

```python
from custom_components.plant.automation_meta import (
    EXTERNAL_MEASUREMENTS,
    STATUS_MEASUREMENTS,
)
from custom_components.plant.condition import async_get_conditions
from custom_components.plant.trigger import async_get_triggers


def _expected_trigger_keys() -> set[str]:
    keys = {"problem_detected", "problem_cleared"}
    for m in STATUS_MEASUREMENTS:
        keys |= {f"{m.key}_became_low", f"{m.key}_became_high", f"{m.key}_became_ok"}
    for m in EXTERNAL_MEASUREMENTS:
        keys |= {f"{m.key}_sensor_became_stale", f"{m.key}_sensor_became_fresh"}
    return keys


def _expected_condition_keys() -> set[str]:
    keys = {"has_problem"}
    for m in STATUS_MEASUREMENTS:
        keys |= {f"{m.key}_is_low", f"{m.key}_is_high", f"{m.key}_is_ok"}
    for m in EXTERNAL_MEASUREMENTS:
        keys |= {f"{m.key}_sensor_is_stale"}
    return keys


async def test_async_get_triggers_full_surface(hass: HomeAssistant) -> None:
    assert set(await async_get_triggers(hass)) == _expected_trigger_keys()
    assert len(_expected_trigger_keys()) == 43


async def test_async_get_conditions_full_surface(hass: HomeAssistant) -> None:
    assert set(await async_get_conditions(hass)) == _expected_condition_keys()
    assert len(_expected_condition_keys()) == 35
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_automation_version_safety.py tests/test_triggers.py -q`
Expected: FAIL — `trigger._has_purpose_trigger_api` / `_build_*` not defined, key sets don't match.

- [ ] **Step 4: Write the version-safe `trigger.py` scaffolding**

Replace `custom_components/plant/trigger.py` entirely:

```python
"""Trigger platform for the plant integration (Home Assistant 2026.7+).

Exposes purpose-specific ``plant.*`` triggers built on the integration's
species-threshold-aware status. Import-safe on every supported HA version: the
2026.7-only helper API is imported lazily and only when present, so on HA
2025.8-2026.6 async_get_triggers returns {} and nothing is registered.
"""

from __future__ import annotations

import homeassistant.helpers.trigger as ha_trigger
from homeassistant.core import HomeAssistant

_TRIGGERS_CACHE: dict[str, type] | None = None


def _has_purpose_trigger_api() -> bool:
    """True when the HA 2026.7 purpose-trigger helper API is available."""
    return hasattr(ha_trigger, "make_entity_target_state_trigger")


async def async_get_triggers(hass: HomeAssistant) -> dict[str, type]:
    """Return the plant.* triggers, or {} on HA without the 2026.7 API."""
    global _TRIGGERS_CACHE
    if not _has_purpose_trigger_api():
        return {}
    if _TRIGGERS_CACHE is None:
        from .trigger_impl import build_triggers

        _TRIGGERS_CACHE = build_triggers()
    return _TRIGGERS_CACHE
```

Create an empty stub `custom_components/plant/trigger_impl.py` so the import
resolves (filled in Tasks 2 & 4):

```python
"""2026.7-only trigger construction. Imported lazily by trigger.py."""

from __future__ import annotations


def build_triggers() -> dict[str, type]:
    """Assemble the full plant.* trigger surface. Filled in Tasks 2 & 4."""
    return {}
```

- [ ] **Step 5: Write the version-safe `condition.py` scaffolding**

Replace `custom_components/plant/condition.py` entirely (mirror of trigger.py):

```python
"""Condition platform for the plant integration (Home Assistant 2026.7+).

Mirror of trigger.py: import-safe everywhere, returns {} on HA without the
2026.7 purpose-condition API.
"""

from __future__ import annotations

import homeassistant.helpers.condition as ha_condition
from homeassistant.core import HomeAssistant

_CONDITIONS_CACHE: dict[str, type] | None = None


def _has_purpose_condition_api() -> bool:
    """True when the HA 2026.7 purpose-condition helper API is available."""
    return hasattr(ha_condition, "make_entity_state_condition")


async def async_get_conditions(hass: HomeAssistant) -> dict[str, type]:
    """Return the plant.* conditions, or {} on HA without the 2026.7 API."""
    global _CONDITIONS_CACHE
    if not _has_purpose_condition_api():
        return {}
    if _CONDITIONS_CACHE is None:
        from .condition_impl import build_conditions

        _CONDITIONS_CACHE = build_conditions()
    return _CONDITIONS_CACHE
```

Create stub `custom_components/plant/condition_impl.py`:

```python
"""2026.7-only condition construction. Imported lazily by condition.py."""

from __future__ import annotations


def build_conditions() -> dict[str, type]:
    """Assemble the full plant.* condition surface. Filled in Tasks 3 & 5."""
    return {}
```

- [ ] **Step 6: Run version-safety tests (pass) and full-surface tests (still fail)**

Run: `python -m pytest tests/test_automation_version_safety.py -q`
Expected: PASS (both return `{}`).
Run: `python -m pytest tests/test_triggers.py::test_async_get_triggers_full_surface -q`
Expected: FAIL — build returns `{}`, key set mismatch. (Filled in Tasks 2-5.)

- [ ] **Step 7: Format and commit**

```bash
black custom_components/plant/ tests/
git add custom_components/plant/automation_meta.py \
        custom_components/plant/trigger.py custom_components/plant/trigger_impl.py \
        custom_components/plant/condition.py custom_components/plant/condition_impl.py \
        tests/test_automation_version_safety.py tests/test_triggers.py
git commit -m "feat: version-safe plant trigger/condition scaffolding + measurement table"
```

---

### Task 2: Aggregate + per-measurement status triggers

**Files:**
- Modify: `custom_components/plant/trigger_impl.py`
- Test: `tests/test_triggers.py`

**Interfaces:**
- Consumes: `automation_meta.STATUS_MEASUREMENTS`; `homeassistant.helpers.trigger.make_entity_target_state_trigger`; `homeassistant.helpers.automation.DomainSpec`.
- Produces: `trigger_impl.build_triggers()` now returns the 2 aggregate + 27 status triggers (stale added in Task 4).

- [ ] **Step 1: Write the failing behavioral tests**

Add to `tests/test_triggers.py` (the `async_capture_events` / `async_setup_component` helpers are already imported at the top of the strawman file):

```python
async def test_problem_detected_fires(hass: HomeAssistant) -> None:
    hass.states.async_set("plant.test", "ok")
    await hass.async_block_till_done()
    events = async_capture_events(hass, "plant_problem")
    assert await async_setup_component(
        hass, "automation",
        {"automation": {
            "trigger": {"trigger": "plant.problem_detected",
                        "target": {"entity_id": "plant.test"}},
            "action": {"event": "plant_problem"}}},
    )
    await hass.async_block_till_done()
    hass.states.async_set("plant.test", "problem")
    await hass.async_block_till_done()
    assert len(events) == 1


async def test_moisture_became_low_uses_status_attribute(hass: HomeAssistant) -> None:
    hass.states.async_set("plant.test", "ok", {"moisture_status": "ok"})
    await hass.async_block_till_done()
    events = async_capture_events(hass, "moisture_low")
    assert await async_setup_component(
        hass, "automation",
        {"automation": {
            "trigger": {"trigger": "plant.moisture_became_low",
                        "target": {"entity_id": "plant.test"}},
            "action": {"event": "moisture_low"}}},
    )
    await hass.async_block_till_done()
    hass.states.async_set("plant.test", "problem", {"moisture_status": "Low"})
    await hass.async_block_till_done()
    assert len(events) == 1


async def test_moisture_became_ok_fires_on_recovery(hass: HomeAssistant) -> None:
    hass.states.async_set("plant.test", "problem", {"moisture_status": "Low"})
    await hass.async_block_till_done()
    events = async_capture_events(hass, "moisture_ok")
    assert await async_setup_component(
        hass, "automation",
        {"automation": {
            "trigger": {"trigger": "plant.moisture_became_ok",
                        "target": {"entity_id": "plant.test"}},
            "action": {"event": "moisture_ok"}}},
    )
    await hass.async_block_till_done()
    hass.states.async_set("plant.test", "ok", {"moisture_status": "ok"})
    await hass.async_block_till_done()
    assert len(events) == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_triggers.py::test_problem_detected_fires tests/test_triggers.py::test_moisture_became_ok_fires_on_recovery -q`
Expected: FAIL — trigger key `plant.problem_detected` unknown.

- [ ] **Step 3: Implement the aggregate + status triggers in `trigger_impl.py`**

Replace `build_triggers` in `custom_components/plant/trigger_impl.py`:

```python
"""2026.7-only trigger construction. Imported lazily by trigger.py."""

from __future__ import annotations

from homeassistant.const import STATE_OK, STATE_PROBLEM
from homeassistant.helpers.automation import DomainSpec
from homeassistant.helpers.trigger import make_entity_target_state_trigger

from .automation_meta import STATUS_MEASUREMENTS
from .const import DOMAIN, STATE_HIGH, STATE_LOW

# transition-name suffix -> plant <m>_status value it maps to
_STATUS_TRANSITIONS = {
    "became_low": STATE_LOW,
    "became_high": STATE_HIGH,
    "became_ok": STATE_OK,
}


def build_triggers() -> dict[str, type]:
    """Assemble the plant.* trigger surface (aggregate + per-measurement status)."""
    triggers: dict[str, type] = {
        # Aggregate plant health (entity state).
        "problem_detected": make_entity_target_state_trigger(DOMAIN, STATE_PROBLEM),
        "problem_cleared": make_entity_target_state_trigger(DOMAIN, STATE_OK),
    }
    # Per-measurement status, auto-thresholded off the plant's own <m>_status.
    for m in STATUS_MEASUREMENTS:
        for suffix, to_state in _STATUS_TRANSITIONS.items():
            triggers[f"{m.key}_{suffix}"] = make_entity_target_state_trigger(
                {DOMAIN: DomainSpec(value_source=m.status_attr)},
                to_state,
            )
    return triggers
```

- [ ] **Step 4: Run the behavioral + surface tests**

Run: `python -m pytest tests/test_triggers.py -q -k "problem_detected or moisture_became or became_ok"`
Expected: PASS.
Run: `python -m pytest tests/test_triggers.py::test_async_get_triggers_full_surface -q`
Expected: still FAIL (stale keys missing — added in Task 4). Confirm the failure names only the 14 `_sensor_became_*` keys.

- [ ] **Step 5: Format and commit**

```bash
black custom_components/plant/ tests/
git add custom_components/plant/trigger_impl.py tests/test_triggers.py
git commit -m "feat: aggregate + per-measurement status plant triggers"
```

---

### Task 3: Per-measurement status conditions + aggregate `has_problem`

**Files:**
- Modify: `custom_components/plant/condition_impl.py`
- Test: `tests/test_conditions.py` (create)

**Interfaces:**
- Consumes: `automation_meta.STATUS_MEASUREMENTS`; `homeassistant.helpers.condition.make_entity_state_condition`; `homeassistant.helpers.automation.DomainSpec`.
- Produces: `condition_impl.build_conditions()` returns the 1 aggregate + 27 status conditions (stale added in Task 5).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_conditions.py`:

```python
"""Tests for the plant.* condition surface (HA 2026.7+)."""

from __future__ import annotations

import pytest
from homeassistant.const import __version__ as HA_VERSION

_p = HA_VERSION.split(".")
if (int(_p[0]), int(_p[1])) < (2026, 7):
    pytest.skip(
        "plant conditions require the HA 2026.7+ platform",
        allow_module_level=True,
    )

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_capture_events


async def _condition_passes(hass: HomeAssistant, cond: dict) -> bool:
    events = async_capture_events(hass, "cond_passed")
    assert await async_setup_component(
        hass, "automation",
        {"automation": {
            "trigger": {"platform": "event", "event_type": "probe"},
            "condition": cond,
            "action": {"event": "cond_passed"}}},
    )
    await hass.async_block_till_done()
    await hass.services.async_call(
        "automation", "trigger",
        {"entity_id": "automation.automation_0", "skip_condition": False},
        blocking=True,
    )
    await hass.async_block_till_done()
    return len(events) == 1


@pytest.mark.parametrize(("state", "expected"), [("problem", True), ("ok", False)])
async def test_has_problem(hass: HomeAssistant, state: str, expected: bool) -> None:
    hass.states.async_set("plant.test", state)
    await hass.async_block_till_done()
    got = await _condition_passes(
        hass, {"condition": "plant.has_problem", "target": {"entity_id": "plant.test"}}
    )
    assert got is expected


@pytest.mark.parametrize(
    ("status", "expected"), [("Low", True), ("High", False), ("ok", False)]
)
async def test_moisture_is_low(hass: HomeAssistant, status: str, expected: bool) -> None:
    hass.states.async_set("plant.test", "problem", {"moisture_status": status})
    await hass.async_block_till_done()
    got = await _condition_passes(
        hass,
        {"condition": "plant.moisture_is_low", "target": {"entity_id": "plant.test"}},
    )
    assert got is expected
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_conditions.py -q`
Expected: FAIL — condition `plant.has_problem` unknown.

- [ ] **Step 3: Implement conditions in `condition_impl.py`**

Replace `build_conditions` in `custom_components/plant/condition_impl.py`:

```python
"""2026.7-only condition construction. Imported lazily by condition.py."""

from __future__ import annotations

from homeassistant.const import STATE_OK, STATE_PROBLEM
from homeassistant.helpers.automation import DomainSpec
from homeassistant.helpers.condition import make_entity_state_condition

from .automation_meta import STATUS_MEASUREMENTS
from .const import DOMAIN, STATE_HIGH, STATE_LOW

_STATUS_CONDITIONS = {
    "is_low": STATE_LOW,
    "is_high": STATE_HIGH,
    "is_ok": STATE_OK,
}


def build_conditions() -> dict[str, type]:
    """Assemble the plant.* condition surface (aggregate + per-measurement status)."""
    conditions: dict[str, type] = {
        "has_problem": make_entity_state_condition(DOMAIN, STATE_PROBLEM),
    }
    for m in STATUS_MEASUREMENTS:
        for suffix, state in _STATUS_CONDITIONS.items():
            conditions[f"{m.key}_{suffix}"] = make_entity_state_condition(
                {DOMAIN: DomainSpec(value_source=m.status_attr)},
                state,
            )
    return conditions
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_conditions.py -q`
Expected: PASS.
Run: `python -m pytest tests/test_triggers.py::test_async_get_conditions_full_surface -q`
Expected: still FAIL (stale conditions missing — Task 5).

- [ ] **Step 5: Format and commit**

```bash
black custom_components/plant/ tests/
git add custom_components/plant/condition_impl.py tests/test_conditions.py
git commit -m "feat: aggregate + per-measurement status plant conditions"
```

---

### Task 4: Per-measurement stale/fresh triggers

**Files:**
- Create: `custom_components/plant/stale.py`
- Modify: `custom_components/plant/trigger_impl.py`
- Test: `tests/test_triggers.py`

**Interfaces:**
- Consumes: `automation_meta.EXTERNAL_MEASUREMENTS`; `PlantDevice` attributes `sensor_<measurement>` (each a sensor entity exposing `.external_sensor: str | None` and `.entity_id`); `hass.data[DOMAIN][entry_id][ATTR_PLANT]`.
- Produces: `stale.resolve_external_sensor(hass, plant_entity_id, device_sensor_attr) -> str | None`; `stale.make_stale_trigger(measurement, fresh: bool) -> type[Trigger]`.
- Produces: `trigger_impl.build_triggers()` now also returns the 14 stale/fresh triggers.

- [ ] **Step 1: Write the failing tests (targeting the plant entity; sensor resolved internally)**

Add to `tests/test_triggers.py`. These use the real integration setup fixture
`init_integration` from `tests/conftest.py` (a configured plant with external
`sensor.test_*` sources):

```python
from datetime import timedelta

import homeassistant.util.dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.plant.const import ATTR_PLANT, DOMAIN as PLANT_DOMAIN


def _plant_entity_id(hass, init_integration) -> str:
    return hass.data[PLANT_DOMAIN][init_integration.entry_id][ATTR_PLANT].entity_id


async def test_moisture_sensor_became_stale_on_unavailable(
    hass: HomeAssistant, init_integration
) -> None:
    plant_id = _plant_entity_id(hass, init_integration)
    events = async_capture_events(hass, "stale")
    assert await async_setup_component(
        hass, "automation",
        {"automation": {
            "trigger": {"trigger": "plant.moisture_sensor_became_stale",
                        "target": {"entity_id": plant_id}},
            "action": {"event": "stale",
                       "event_data": {"reason": "{{ trigger.reason }}"}}}},
    )
    await hass.async_block_till_done()
    hass.states.async_set("sensor.test_moisture", "unavailable")
    await hass.async_block_till_done()
    assert len(events) == 1
    assert events[0].data["reason"] == "unavailable"


async def test_moisture_sensor_became_stale_on_no_update(
    hass: HomeAssistant, init_integration
) -> None:
    plant_id = _plant_entity_id(hass, init_integration)
    events = async_capture_events(hass, "stale")
    assert await async_setup_component(
        hass, "automation",
        {"automation": {
            "trigger": {"trigger": "plant.moisture_sensor_became_stale",
                        "target": {"entity_id": plant_id},
                        "options": {"for": {"seconds": 30}}},
            "action": {"event": "stale"}}},
    )
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()
    assert len(events) == 1


async def test_moisture_sensor_became_fresh_on_recovery(
    hass: HomeAssistant, init_integration
) -> None:
    plant_id = _plant_entity_id(hass, init_integration)
    hass.states.async_set("sensor.test_moisture", "unavailable")
    await hass.async_block_till_done()
    events = async_capture_events(hass, "fresh")
    assert await async_setup_component(
        hass, "automation",
        {"automation": {
            "trigger": {"trigger": "plant.moisture_sensor_became_fresh",
                        "target": {"entity_id": plant_id}},
            "action": {"event": "fresh"}}},
    )
    await hass.async_block_till_done()
    hass.states.async_set("sensor.test_moisture", "42")
    await hass.async_block_till_done()
    assert len(events) == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_triggers.py -q -k "sensor_became_stale or sensor_became_fresh"`
Expected: FAIL — trigger key unknown.

- [ ] **Step 3: Implement `stale.py` (external-sensor resolution + custom Trigger)**

Create `custom_components/plant/stale.py`:

```python
"""Per-measurement stale/fresh source-sensor tracking for plant.* triggers.

A stale trigger targets the *plant* entity; it resolves that measurement's
external source sensor from the PlantDevice and watches that sensor. "Stale" =
unavailable/unknown, or no update within `for` (default 24h). Imported lazily
by trigger_impl.py — only on HA with the 2026.7 API.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

import voluptuous as vol
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_FOR,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, State, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.target import (
    TargetStateChangedData,
    async_track_target_selector_state_change_event,
)
from homeassistant.helpers.trigger import Trigger, TriggerActionRunner, TriggerConfig
from homeassistant.helpers.typing import ConfigType

from .automation_meta import Measurement
from .const import ATTR_PLANT, DOMAIN

DEFAULT_STALE_FOR = timedelta(hours=24)
_EXCLUDED = {STATE_UNAVAILABLE, STATE_UNKNOWN}


def resolve_external_sensor(
    hass: HomeAssistant, plant_entity_id: str, device_sensor_attr: str
) -> str | None:
    """Return the external source sensor entity_id for a plant measurement."""
    for data in hass.data.get(DOMAIN, {}).values():
        if not isinstance(data, dict) or ATTR_PLANT not in data:
            continue
        plant = data[ATTR_PLANT]
        if plant.entity_id != plant_entity_id:
            continue
        sensor = getattr(plant, device_sensor_attr, None)
        return getattr(sensor, "external_sensor", None) if sensor else None
    return None


def make_stale_trigger(measurement: Measurement, *, fresh: bool) -> type[Trigger]:
    """Build a stale (fresh=False) or fresh (fresh=True) trigger for a measurement."""

    class _PlantStaleTrigger(Trigger):
        _schema = vol.Schema(
            {
                vol.Required("target"): cv.TARGET_FIELDS,
                vol.Optional("options", default=dict): vol.Schema(
                    {vol.Optional(CONF_FOR): cv.positive_time_period},
                    extra=vol.ALLOW_EXTRA,
                ),
            },
            extra=vol.ALLOW_EXTRA,
        )

        @classmethod
        async def async_validate_config(
            cls, hass: HomeAssistant, config: ConfigType
        ) -> ConfigType:
            return cls._schema(config)

        def __init__(self, hass: HomeAssistant, config: TriggerConfig) -> None:
            super().__init__(hass, config)
            self._target = config.target
            self._duration: timedelta = (config.options or {}).get(
                CONF_FOR
            ) or DEFAULT_STALE_FOR

        @callback
        def _sources(self, entities: set[str]) -> set[str]:
            """Map targeted plant entities to their external source sensor."""
            resolved: set[str] = set()
            for entity_id in entities:
                if not entity_id.startswith(f"{DOMAIN}."):
                    continue
                source = resolve_external_sensor(
                    self._hass, entity_id, measurement.device_sensor_attr
                )
                if source:
                    resolved.add(source)
            return resolved

        async def async_attach_runner(
            self, run_action: TriggerActionRunner, did_not_trigger: Any | None = None
        ) -> CALLBACK_TYPE:
            timers: dict[str, CALLBACK_TYPE] = {}
            stale: set[str] = set()

            @callback
            def _fire(entity_id: str, reason: str | None) -> None:
                data = {ATTR_ENTITY_ID: entity_id, "measurement": measurement.key}
                if not fresh:
                    data["reason"] = reason  # "unavailable" | "no_update"
                run_action(data, f"{measurement.key} sensor {entity_id}", None)

            @callback
            def _mark_stale(entity_id: str, reason: str) -> None:
                timer = timers.pop(entity_id, None)
                if timer is not None:
                    timer()
                if entity_id not in stale:
                    stale.add(entity_id)
                    if not fresh:
                        _fire(entity_id, reason)

            @callback
            def _arm(entity_id: str) -> None:
                was_stale = entity_id in stale
                stale.discard(entity_id)
                timer = timers.pop(entity_id, None)
                if timer is not None:
                    timer()
                if fresh and was_stale:
                    _fire(entity_id, None)

                @callback
                def _expired(_now: datetime) -> None:
                    timers.pop(entity_id, None)
                    if entity_id not in stale:
                        stale.add(entity_id)
                        if not fresh:
                            _fire(entity_id, "no_update")

                timers[entity_id] = async_call_later(
                    self._hass, self._duration, _expired
                )

            @callback
            def _consider(entity_id: str, state: State | None) -> None:
                if state is None or state.state in _EXCLUDED:
                    _mark_stale(entity_id, "unavailable")
                else:
                    _arm(entity_id)

            @callback
            def _on_state_change(d: TargetStateChangedData) -> None:
                ev = d.state_change_event
                _consider(ev.data["entity_id"], ev.data["new_state"])

            @callback
            def _on_entities_update(
                added: set[str],
                removed: set[str],
                entity_states: Mapping[str, State | None],
            ) -> None:
                for entity_id in removed:
                    timer = timers.pop(entity_id, None)
                    if timer is not None:
                        timer()
                    stale.discard(entity_id)
                for entity_id in added:
                    _consider(entity_id, entity_states.get(entity_id))

            unsub = await async_track_target_selector_state_change_event(
                self._hass, self._target, _on_state_change, self._sources,
                _on_entities_update,
            )

            @callback
            def _remove() -> None:
                unsub()
                for timer in timers.values():
                    timer()
                timers.clear()
                stale.clear()

            return _remove

    return _PlantStaleTrigger
```

- [ ] **Step 4: Wire stale triggers into `build_triggers`**

In `custom_components/plant/trigger_impl.py`, add the import and the loop. Change
the imports block to add:

```python
from .automation_meta import EXTERNAL_MEASUREMENTS, STATUS_MEASUREMENTS
from .stale import make_stale_trigger
```

and before `return triggers` in `build_triggers`, add:

```python
    # Per-measurement source-sensor staleness (external measurements only).
    for m in EXTERNAL_MEASUREMENTS:
        triggers[f"{m.key}_sensor_became_stale"] = make_stale_trigger(m, fresh=False)
        triggers[f"{m.key}_sensor_became_fresh"] = make_stale_trigger(m, fresh=True)
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_triggers.py -q -k "sensor_became_stale or sensor_became_fresh"`
Expected: PASS.
Run: `python -m pytest tests/test_triggers.py::test_async_get_triggers_full_surface -q`
Expected: PASS (all 43 keys present).

- [ ] **Step 6: Format and commit**

```bash
black custom_components/plant/ tests/
git add custom_components/plant/stale.py custom_components/plant/trigger_impl.py tests/test_triggers.py
git commit -m "feat: per-measurement stale/fresh plant sensor triggers"
```

---

### Task 5: Per-measurement `sensor_is_stale` conditions

**Files:**
- Modify: `custom_components/plant/stale.py`
- Modify: `custom_components/plant/condition_impl.py`
- Test: `tests/test_conditions.py`

**Interfaces:**
- Consumes: `stale.resolve_external_sensor`; `automation_meta.EXTERNAL_MEASUREMENTS`; `homeassistant.helpers.condition.Condition`, `ConditionConfig`.
- Produces: `stale.make_stale_condition(measurement) -> type[Condition]`.
- Produces: `condition_impl.build_conditions()` now also returns the 7 `<m>_sensor_is_stale` conditions.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_conditions.py`:

```python
from datetime import timedelta

import homeassistant.util.dt as dt_util

from custom_components.plant.const import ATTR_PLANT, DOMAIN as PLANT_DOMAIN


def _plant_entity_id(hass, init_integration) -> str:
    return hass.data[PLANT_DOMAIN][init_integration.entry_id][ATTR_PLANT].entity_id


async def test_moisture_sensor_is_stale_when_unavailable(
    hass: HomeAssistant, init_integration
) -> None:
    plant_id = _plant_entity_id(hass, init_integration)
    hass.states.async_set("sensor.test_moisture", "unavailable")
    await hass.async_block_till_done()
    got = await _condition_passes(
        hass,
        {"condition": "plant.moisture_sensor_is_stale",
         "target": {"entity_id": plant_id}},
    )
    assert got is True


async def test_moisture_sensor_is_stale_false_when_fresh(
    hass: HomeAssistant, init_integration
) -> None:
    plant_id = _plant_entity_id(hass, init_integration)
    hass.states.async_set("sensor.test_moisture", "42")
    await hass.async_block_till_done()
    got = await _condition_passes(
        hass,
        {"condition": "plant.moisture_sensor_is_stale",
         "target": {"entity_id": plant_id}},
    )
    assert got is False
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_conditions.py -q -k "sensor_is_stale"`
Expected: FAIL — condition key unknown.

- [ ] **Step 3: Add `make_stale_condition` to `stale.py`**

Append to `custom_components/plant/stale.py` (add the imports
`from homeassistant.helpers.condition import Condition, ConditionConfig` and
`from homeassistant.util import dt as dt_util` at the top with the others):

```python
def make_stale_condition(measurement: Measurement) -> type[Condition]:
    """True when the measurement's external source sensor is currently stale."""

    class _PlantStaleCondition(Condition):
        _schema = vol.Schema(
            {
                vol.Required("target"): cv.TARGET_FIELDS,
                vol.Optional("options", default=dict): vol.Schema(
                    {vol.Optional(CONF_FOR): cv.positive_time_period},
                    extra=vol.ALLOW_EXTRA,
                ),
            },
            extra=vol.ALLOW_EXTRA,
        )

        @classmethod
        async def async_validate_config(
            cls, hass: HomeAssistant, config: ConfigType
        ) -> ConfigType:
            return cls._schema(config)

        def __init__(self, hass: HomeAssistant, config: ConditionConfig) -> None:
            super().__init__(hass, config)
            self._target = config.target
            self._duration: timedelta = (config.options or {}).get(
                CONF_FOR
            ) or DEFAULT_STALE_FOR

        def _async_check(self, **kwargs: Any) -> bool:
            from homeassistant.helpers.target import (
                TargetSelection,
                async_extract_referenced_entity_ids,
            )

            selection = TargetSelection(self._target)
            selected = async_extract_referenced_entity_ids(
                self._hass, selection, expand_group=False
            )
            plant_ids = selected.referenced | selected.indirectly_referenced
            now = dt_util.utcnow()
            for plant_id in plant_ids:
                if not plant_id.startswith(f"{DOMAIN}."):
                    continue
                source = resolve_external_sensor(
                    self._hass, plant_id, measurement.device_sensor_attr
                )
                if not source:
                    continue
                state = self._hass.states.get(source)
                if state is None or state.state in _EXCLUDED:
                    return True
                if now - state.last_updated > self._duration:
                    return True
            return False

    return _PlantStaleCondition
```

- [ ] **Step 4: Wire stale conditions into `build_conditions`**

In `custom_components/plant/condition_impl.py`, change the `automation_meta`
import to `from .automation_meta import EXTERNAL_MEASUREMENTS, STATUS_MEASUREMENTS`,
add `from .stale import make_stale_condition`, and before `return conditions` add:

```python
    for m in EXTERNAL_MEASUREMENTS:
        conditions[f"{m.key}_sensor_is_stale"] = make_stale_condition(m)
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_conditions.py -q -k "sensor_is_stale"`
Expected: PASS.
Run: `python -m pytest tests/test_triggers.py::test_async_get_conditions_full_surface -q`
Expected: PASS (all 35 keys present).

- [ ] **Step 6: Format and commit**

```bash
black custom_components/plant/ tests/
git add custom_components/plant/stale.py custom_components/plant/condition_impl.py tests/test_conditions.py
git commit -m "feat: per-measurement plant sensor_is_stale conditions"
```

---

### Task 6: UI descriptions (`triggers.yaml` / `conditions.yaml`)

**Files:**
- Rewrite: `custom_components/plant/triggers.yaml`
- Rewrite: `custom_components/plant/conditions.yaml`
- Test: `tests/test_automation_descriptions.py` (create)

**Interfaces:**
- Consumes: the trigger/condition keys from Tasks 2-5. Every advertised key MUST have a matching description block; HA logs a warning otherwise.

- [ ] **Step 1: Write the failing coverage test**

Create `tests/test_automation_descriptions.py`:

```python
"""Every advertised trigger/condition key must have a UI description block."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from homeassistant.const import __version__ as HA_VERSION

_p = HA_VERSION.split(".")
if (int(_p[0]), int(_p[1])) < (2026, 7):
    pytest.skip("requires HA 2026.7+", allow_module_level=True)

from homeassistant.core import HomeAssistant

from custom_components.plant.condition import async_get_conditions
from custom_components.plant.trigger import async_get_triggers

_ROOT = Path("custom_components/plant")


def _described_keys(filename: str) -> set[str]:
    doc = yaml.safe_load((_ROOT / filename).read_text())
    return {k for k in doc if not k.startswith(".")}


async def test_every_trigger_has_a_description(hass: HomeAssistant) -> None:
    assert set(await async_get_triggers(hass)) <= _described_keys("triggers.yaml")


async def test_every_condition_has_a_description(hass: HomeAssistant) -> None:
    assert set(await async_get_conditions(hass)) <= _described_keys("conditions.yaml")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_automation_descriptions.py -q`
Expected: FAIL — strawman yaml only describes the old key names.

- [ ] **Step 3: Generate the description YAML**

Generate the two files from the measurement table so keys always match. Run this
one-off generator from the repo root and commit its output (not the script):

```python
# scratch generator — run once, do not commit
from custom_components.plant.automation_meta import (
    EXTERNAL_MEASUREMENTS, STATUS_MEASUREMENTS,
)

STATE_TGT = """  target:
    entity:
      domain: plant
  fields:
    behavior:
      required: true
      default: each
      selector:
        automation_behavior:
          mode: trigger
"""
STALE_TGT = """  target:
    entity:
      domain: plant
  fields:
    for:
      required: false
      default: "24:00:00"
      selector:
        duration:
"""

lines = ["# Trigger descriptions for the plant integration (HA 2026.7+).",
         "# Generated from automation_meta.py — keep in sync.", ""]
for key in ("problem_detected", "problem_cleared"):
    lines += [f"{key}:", STATE_TGT.rstrip(), ""]
for m in STATUS_MEASUREMENTS:
    for suf in ("became_low", "became_high", "became_ok"):
        lines += [f"{m.key}_{suf}:", STATE_TGT.rstrip(), ""]
for m in EXTERNAL_MEASUREMENTS:
    for suf in ("sensor_became_stale", "sensor_became_fresh"):
        lines += [f"{m.key}_{suf}:", STALE_TGT.rstrip(), ""]
open("custom_components/plant/triggers.yaml", "w").write("\n".join(lines) + "\n")

clines = ["# Condition descriptions for the plant integration (HA 2026.7+).",
          "# Generated from automation_meta.py — keep in sync.", ""]
COND_TGT = """  target:
    entity:
      domain: plant
"""
for key in ["has_problem"]:
    clines += [f"{key}:", COND_TGT.rstrip(), ""]
for m in STATUS_MEASUREMENTS:
    for suf in ("is_low", "is_high", "is_ok"):
        clines += [f"{m.key}_{suf}:", COND_TGT.rstrip(), ""]
for m in EXTERNAL_MEASUREMENTS:
    clines += [f"{m.key}_sensor_is_stale:", COND_TGT.rstrip(), ""]
open("custom_components/plant/conditions.yaml", "w").write("\n".join(clines) + "\n")
```

Run: `python -c "$(cat scratch_gen.py)"` (or paste into a REPL), then delete the script.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_automation_descriptions.py -q`
Expected: PASS.

- [ ] **Step 5: Format and commit**

```bash
black tests/
git add custom_components/plant/triggers.yaml custom_components/plant/conditions.yaml tests/test_automation_descriptions.py
git commit -m "feat: UI descriptions for the full plant.* trigger/condition surface"
```

---

### Task 7: Full-suite verification against released 2026.7.4 + strawman cleanup

**Files:**
- Verify only: whole test suite
- Modify (if present): remove any leftover strawman-only symbols

**Interfaces:** none new.

- [ ] **Step 1: Confirm no strawman leftovers**

Run: `grep -rn "became_problem\b\|became_ok\b\|moisture_became_low\|sensor_became_stale\b\|is_problem\b\|PROTOTYPE\|strawman" custom_components/plant/trigger.py custom_components/plant/condition.py custom_components/plant/trigger_impl.py custom_components/plant/condition_impl.py custom_components/plant/triggers.yaml custom_components/plant/conditions.yaml`
Expected: no matches (all replaced by the new names; `problem_detected`/`problem_cleared` are the aggregate keys now).

- [ ] **Step 2: Run the full test suite on the installed HA**

Run: `python -m pytest tests/ -q`
Expected: PASS. Note the count (existing 347 + new trigger/condition/version tests).

- [ ] **Step 3: Verify against the actually-released 2026.7.4 in a throwaway venv**

```bash
python -m venv /tmp/ha274venv && /tmp/ha274venv/bin/pip install -q \
  homeassistant==2026.7.4 pytest pytest-homeassistant-custom-component pytest-asyncio
/tmp/ha274venv/bin/python -m pytest tests/test_triggers.py tests/test_conditions.py \
  tests/test_automation_descriptions.py tests/test_automation_version_safety.py -q
```
Expected: PASS on the released 2026.7.4 (not just the b1 in the project venv).

- [ ] **Step 4: Verify version-safety on the 2025.8 floor**

```bash
python -m venv /tmp/ha258venv && /tmp/ha258venv/bin/pip install -q \
  homeassistant==2025.8.3 pytest pytest-homeassistant-custom-component pytest-asyncio
/tmp/ha258venv/bin/python -m pytest tests/test_automation_version_safety.py -q
/tmp/ha258venv/bin/python -c "import custom_components.plant.trigger, custom_components.plant.condition; print('import clean on 2025.8')"
```
Expected: version-safety tests PASS; the import line prints "import clean on 2025.8" with no ImportError.

- [ ] **Step 5: black + ruff clean, then commit any cleanup**

```bash
black --check custom_components/plant/ tests/
git add -A && git commit -m "test: verify plant.* automation surface on released 2026.7.4 and 2025.8" || echo "nothing to commit"
```

---

## Self-Review

**Spec coverage:**
- Aggregate `problem_detected`/`problem_cleared` + `has_problem` → Tasks 2, 3. ✓
- Per-measurement status `became_low/high/ok` + `is_low/high/ok` (9) → Tasks 2, 3. ✓
- Per-measurement stale `sensor_became_stale/fresh` + `sensor_is_stale` (7 external) → Tasks 4, 5. ✓
- Uniform plant-entity targeting + auto-threshold via `DomainSpec(value_source=...)` → Tasks 2, 3. ✓
- Stale semantics (unavailable-or-silent, 24h, recovery, external resolution) → Task 4 (`stale.py`). ✓
- Version safety (feature-detect, lazy import, `{}` on <2026.7) → Task 1, verified Task 7 step 4. ✓
- Discovery contract (`async_get_triggers`/`async_get_conditions`) → Task 1. ✓
- UI descriptions → Task 6. ✓
- Testing incl. 2025.8 safety + released 2026.7.4 → Tasks 1, 7. ✓
- No `crossed_threshold` (non-goal) → nothing adds it. ✓
- Measurement table single source of truth → Task 1 (`automation_meta.py`). ✓

**Placeholder scan:** No TBD/TODO; every code step shows complete code. The one-off YAML generator in Task 6 is explicitly a scratch script that is run and deleted, with the committed artifact being its output.

**Type consistency:** `Measurement(key, status_attr, device_sensor_attr)` used consistently. `resolve_external_sensor(hass, plant_entity_id, device_sensor_attr)`, `make_stale_trigger(measurement, *, fresh)`, `make_stale_condition(measurement)` referenced identically in `stale.py` and both `_impl` modules. `build_triggers()`/`build_conditions()` names match their lazy-import call sites in `trigger.py`/`condition.py`. Status suffix→state maps (`became_low`→`STATE_LOW`, etc.) consistent across trigger and condition impls.
