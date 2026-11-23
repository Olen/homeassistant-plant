# Plant care: modes, per-type events and watering prediction — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give plant everything the plant-care card needs: watering and prune intervals, one care event entity per care type, the problem-trigger checkboxes as the sensor/interval switch (including fertilize sensor mode), a watering-prediction sensor, and a `care` block in `plant/get_info`.

**Architecture:** Builds on the care PoC (draft PR #583, branch `feature/care-todo-poc`). `CareTasks` (care.py) stays the only writer of to-do items; it gains a per-care *mode* (`sensor` / `interval` / `none`) computed by the plant from options and sensor presence. Event entities become one per care type. The prediction is a pure function over recorder history, wrapped in a timestamp sensor.

**Tech Stack:** Python, Home Assistant custom integration, pytest with the repo's HA test helpers.

**Spec:** `/home/olen/prog/lovelace-flower-card/docs/superpowers/specs/2026-11-23-plant-care-card-design.md` (section "Changes in plant", plus "Tracking mode" and "Case by case").

## Global Constraints

- Plant keeps no runtime care state of its own. Persistence only via the to-do list, event-entity restore and the recorder.
- Item marker stays `plant.<id> · <care>` (`MARKER_SEPARATOR = " · "`); one definition only (care.py `_marker`).
- Care types: `water`, `fertilize`, `repot`, `prune`. Event types: `watered`, `fertilized`, `repotted`, `pruned`.
- Mode rule: trigger checked **and** sensor present ⇒ `sensor`; otherwise interval > 0 ⇒ `interval`; otherwise `none`. Repot and prune have no sensor. Sensor wins over an interval.
- Changing a care type's mode removes that plant's open items of that care type.
- In water interval mode, detected waterings still complete open water items / report `watered`.
- Sensor-closed fertilize items report `fertilized` like any completed item (no workaround for flaky sensors).
- Work on branch `feature/care-todo-poc` (PR #583). Run before each commit: `.venv/bin/pytest tests/ -q`, `black . --check`, `ruff check .`.
- Comments: one line of non-obvious *why*; no history in code.

## Review Focus

1. **Plant renamed while items are open** — open items must still be found and moved (existing `async_move_items`) for all four care types, including prune. Test in Task 2.
2. **Plant without a moisture sensor but `moisture_trigger` left at its default `True`** — mode must be `interval`/`none`, never `sensor`. Test in Task 2.
3. **Conductivity flapping around min** (low → ok → low within minutes) — must not create duplicate fertilize items; one open item at a time. Test in Task 3.
4. **Prediction with a watering inside the 96 h window, or rising moisture** — only readings after the last jump count; rising/flat slope ⇒ no prediction (sensor `unknown`), never a date in the past beyond "now". Test in Task 4.
5. **`plant/get_info` on a plant without a to-do list** — `care` block present with `todo_list: null`, modes still reported, no exception. Test in Task 5.

---

### Task 1: Prune care type and one event entity per care type

**Files:**
- Modify: `custom_components/plant/const.py` (care constants block, ~329-348)
- Modify: `custom_components/plant/event.py`
- Modify: `custom_components/plant/care.py` (`SUMMARIES`, event reporting)
- Modify: `custom_components/plant/__init__.py` (`_watered`, `care_event` attribute ~695, CareTasks construction ~448-456)
- Modify: `custom_components/plant/care_trigger.py`, `custom_components/plant/trigger_impl.py`, `custom_components/plant/triggers.yaml`
- Modify: `custom_components/plant/strings.json`, `translations/*.json`
- Test: `tests/test_care.py`, `tests/test_triggers.py`

**Interfaces:**
- Produces:
  - const: `CARE_PRUNE = "prune"`; `CARE_EVENT_TYPES = {CARE_WATER: "watered", CARE_FERTILIZE: "fertilized", CARE_REPOT: "repotted", CARE_PRUNE: "pruned"}`; `ATTR_CARE_EVENTS = "care_events"` (replaces `ATTR_CARE_EVENT`).
  - `class PlantCareEvent(EventEntity)`: `__init__(self, entry: ConfigEntry, plant: Entity, care: str)`; `_attr_event_types = [CARE_EVENT_TYPES[care]]`; `_attr_translation_key = CARE_EVENT_TYPES[care]`; `_attr_unique_id = f"{entry.entry_id}-{CARE_EVENT_TYPES[care]}"`; `report(self) -> None` (no argument).
  - `hass.data[DOMAIN][entry_id][ATTR_CARE_EVENTS]: dict[str, PlantCareEvent]` keyed by care type; `plant.care_events` same dict.
  - `SUMMARIES[CARE_PRUNE] = "Prune {name}"`.
  - `resolve_care_event(hass, plant_entity_id: str, event_type: str) -> str | None` returns that type's event entity id.
  - `CareTasks.__init__` takes `care_events: dict[str, PlantCareEvent]` instead of `care_event`.

- [ ] **Step 1: Write failing tests** in `tests/test_care.py`:
  - `test_one_event_entity_per_care_type`: after `_setup_plant`, the entity registry holds unique ids `f"{TEST_ENTRY_ID}-watered"`, `-fertilized`, `-repotted`, `-pruned`, and no `f"{TEST_ENTRY_ID}-care"`.
  - `test_watering_reports_only_the_watered_entity`: a moisture jump (`_set_moisture` 20 → 35) changes the `-watered` entity's state and leaves `-fertilized` unchanged.
  - `test_ticking_off_prune_item_reports_pruned`: with `prune_interval` 30 and a list, tick off the open "Prune …" item ⇒ `-pruned` entity fires; next prune item due today + 30 days.
  - Update `_care_events(hass)` to take the event type and read by `f"{TEST_ENTRY_ID}-{event_type}"`.
  - In `tests/test_triggers.py:43` add `"pruned"` to the expected trigger keys.

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_care.py tests/test_triggers.py -q` — expect the new tests to FAIL.

- [ ] **Step 3: Implement.** `async_setup_entry` in event.py creates one `PlantCareEvent` per key of `CARE_EVENT_TYPES` and stores the dict. `CareTasks` reports with `self._care_events[care].report()`. `__init__._watered` reports `care_events[CARE_WATER].report()` when there are no care tasks. Triggers resolve per event type. Add `pruned` to triggers.yaml (same shape as `repotted`), translations: `entity.event.{watered,fertilized,repotted,pruned}.name` ("Watered", "Fertilized", "Repotted", "Pruned"), `triggers.pruned.{name,description}` ("Plant pruned"); drop `entity.event.care`. Add the prune interval constant `FLOW_PRUNE_INTERVAL = "prune_interval"` and `FLOW_WATER_INTERVAL = "water_interval"` here too (used in Task 2).

- [ ] **Step 4: Run** `.venv/bin/pytest tests/ -q` — all PASS. Then `black . --check && ruff check .`.

- [ ] **Step 5: Commit**
```bash
git add -A custom_components/plant tests
git commit -m "Care: one event entity per care type, add prune"
```

Note for Olen (not code): the PoC's old `event.<plant>_care` entities on octopus become orphans; remove them from the entity registry after deploying.

---

### Task 2: Care modes from trigger checkboxes, watering and prune intervals

**Files:**
- Modify: `custom_components/plant/care.py` (`care_settings`, `CareTasks.__init__`, `async_start`, `async_moisture_low`, `_async_plan_interval_items`, `async_remove_open_items`)
- Modify: `custom_components/plant/__init__.py` (`care_settings` use ~258/447, new `care_modes`, `_soil_became_dry` ~1400)
- Modify: `custom_components/plant/config_flow.py` (`async_step_care_tasks` ~973, `update_plant_options` ~1073)
- Modify: `strings.json`, `translations/*.json`
- Test: `tests/test_care.py`

**Interfaces:**
- Consumes: Task 1 constants and `care_events`.
- Produces:
  - const: `CARE_MODE_SENSOR = "sensor"`, `CARE_MODE_INTERVAL = "interval"`, `CARE_MODE_NONE = "none"`.
  - `care_settings(options: Mapping[str, Any]) -> CareSettings` where `@dataclass(frozen=True) class CareSettings: todo: str | None; intervals: dict[str, int]` (keys: all four care types; missing option ⇒ 0).
  - `care_modes(settings: CareSettings, moisture_sensor: bool, conductivity_sensor: bool, moisture_trigger: bool, conductivity_trigger: bool) -> dict[str, str]` in care.py — pure; implements the Global Constraints mode rule.
  - `PlantDevice.care_modes -> dict[str, str]` property calling `care_modes(...)` with the plant's own sensors and trigger options.
  - `CareTasks.__init__(self, hass, plant_entity_id, plant_name, todo_entity_id, intervals: dict[str, int], modes: dict[str, str], care_events, moisture_status)`.
  - `CareTasks.async_remove_open_items(self, cares: set[str] | None = None) -> None` — `None` means all care types (existing behaviour).

- [ ] **Step 1: Write failing tests.**
  - Pure, parametrized `test_care_modes` covering: water with sensor + trigger ⇒ `sensor`; sensor + trigger off + interval 3 ⇒ `interval`; no sensor + trigger on (default) + interval 3 ⇒ `interval`; no sensor, interval 0 ⇒ `none`; sensor + trigger + interval 3 ⇒ `sensor`; repot interval 365 ⇒ `interval`; prune interval 0 ⇒ `none`; same rows for fertilize with conductivity.
  - `test_water_interval_mode_plans_items`: no moisture sensor, `water_interval` 7, list set ⇒ one open "Water …" item due today; tick off ⇒ next due today + 7.
  - `test_water_interval_mode_ignores_dry_soil`: moisture sensor present, `moisture_trigger` False, `water_interval` 7 ⇒ moisture going low adds no extra item (only the interval item exists).
  - `test_water_interval_mode_detected_watering_completes_item`: same setup, moisture jump ⇒ open water item completed, `-watered` fires once.
  - `test_mode_change_removes_open_items_of_that_type`: `fertilize_interval` 15 with an open fertilize item and an open repot item; switch `conductivity_trigger` from False to True (plant has conductivity sensor) through the options flow ⇒ fertilize item gone, repot item kept.
  - `test_rename_moves_prune_items` (Review Focus 1): open prune item follows a plant rename.
  - Options-flow test: the care_tasks step accepts and stores `water_interval` and `prune_interval` (ints, 0–730).

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_care.py -q` — new tests FAIL.

- [ ] **Step 3: Implement.**
  - `_async_plan_interval_items` plans only care types whose mode is `interval`.
  - `async_moisture_low` and the startup moisture reconcile in `async_start` act only when `modes[CARE_WATER] == CARE_MODE_SENSOR`. `async_watered` is unchanged (runs in every mode).
  - `care_tasks` step: add `FLOW_WATER_INTERVAL` and `FLOW_PRUNE_INTERVAL` with the same number selector as fertilize (min 0, max 730, box, unit "d"). Order: watering, fertilize, repot, prune. Translations for both fields, en/de/dk at minimum (other languages fall back).
  - `update_plant_options`: compare old vs new `care_modes`; for care types whose mode changed, `await plant.care_tasks.async_remove_open_items(changed)` before the reload. Keep the existing list-changed path. Trigger options live in `plant_properties`, so this comparison must run for both steps.

- [ ] **Step 4: Run** `.venv/bin/pytest tests/ -q`, `black . --check`, `ruff check .` — PASS.

- [ ] **Step 5: Commit**
```bash
git add -A custom_components/plant tests
git commit -m "Care: trigger checkboxes choose sensor or interval; watering and prune intervals"
```

---

### Task 3: Fertilize sensor mode

**Files:**
- Modify: `custom_components/plant/care.py` (new methods)
- Modify: `custom_components/plant/__init__.py` (conductivity block ~1548; helpers next to `_soil_became_dry` ~1400)
- Test: `tests/test_care.py`

**Interfaces:**
- Consumes: Task 2 `modes`.
- Produces:
  - `CareTasks.async_conductivity_low(self) -> None` — add "Fertilize X" due today unless one is open.
  - `CareTasks.async_conductivity_recovered(self) -> None` — complete open fertilize items (the list change then reports `fertilized` through `_async_sync`).
  - `CareTasks.__init__` gains `conductivity_status: Callable[[], str | None]`; `async_start` reconciles it like moisture (LOW ⇒ low handler, OK/HIGH ⇒ recovered), only in fertilize sensor mode.

- [ ] **Step 1: Write failing tests** (plant with conductivity sensor, `conductivity_trigger` True, list set):
  - `test_conductivity_low_opens_fertilize_item`: conductivity below min ⇒ one open "Fertilize …" item due today.
  - `test_conductivity_back_above_min_completes_item`: then above min ⇒ item completed, `-fertilized` fires once.
  - `test_conductivity_flapping_keeps_one_item` (Review Focus 3): low → ok → low → ok ⇒ never more than one open fertilize item; `-fertilized` fires twice.
  - `test_conductivity_trigger_off_ignores_conductivity`: trigger False, `fertilize_interval` 15 ⇒ conductivity low adds nothing beyond the interval item.
  - Use a conductivity setter helper in the style of `_set_moisture` (`set_sensor_state(hass, CONDUCTIVITY, v)` + `update_plant_sensors`).

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_care.py -q` — FAIL.

- [ ] **Step 3: Implement.** In `update()`, keep `previous_conductivity_status`; on transition into LOW call `_conductivity_became_low()`, on LOW → OK/HIGH call `_conductivity_recovered()`. Both helpers `hass.add_job` the CareTasks method only when `care_tasks` is not None and `care_modes[CARE_FERTILIZE] == CARE_MODE_SENSOR`. Do not change how the conductivity problem itself is computed.

- [ ] **Step 4: Run** full suite + `black . --check` + `ruff check .` — PASS.

- [ ] **Step 5: Commit**
```bash
git add -A custom_components/plant tests
git commit -m "Care: conductivity drives fertilize items in sensor mode"
```

---

### Task 4: Watering prediction sensor

**Files:**
- Create: `custom_components/plant/prediction.py`
- Modify: `custom_components/plant/sensor.py` (new entity), `custom_components/plant/__init__.py` (register entity on plants with a moisture sensor)
- Modify: `strings.json`, `translations/*.json` (`entity.sensor.next_watering.name` = "Next watering")
- Test: `tests/test_prediction.py`, `tests/test_care.py` (entity presence)

**Interfaces:**
- Produces:
  - `predict_dry_time(readings: list[tuple[datetime, float]], minimum: float, now: datetime) -> datetime | None` in prediction.py (pure).
  - Constants in const.py: `PREDICTION_WINDOW = timedelta(hours=96)`, `PREDICTION_MIN_SPAN = timedelta(hours=12)`, `PREDICTION_MIN_READINGS = 6`. *(Values are Claude's call, based on the 2026 backtest: 96 h linear slope.)*
  - `PlantNextWatering(SensorEntity)`: `device_class = SensorDeviceClass.TIMESTAMP`, unique id `f"{entry.entry_id}-next-watering"`, translation key `next_watering`. Only created when the plant has a moisture sensor.

Algorithm for `predict_dry_time` (not determined by the signature):
```
keep readings within PREDICTION_WINDOW before now, sorted by time
drop everything up to and including the last reading that rose >= MOISTURE_INCREASE_THRESHOLD over its predecessor (a watering)
if fewer than PREDICTION_MIN_READINGS remain, or their span < PREDICTION_MIN_SPAN: return None
slope = least-squares slope of value over time (per hour)
if slope >= 0: return None
latest = last reading value
if latest <= minimum: return now
return now + (latest - minimum) / -slope hours
```

- [ ] **Step 1: Write failing tests** in `tests/test_prediction.py` with explicit readings:
  - `test_steady_drydown`: 49 hourly readings ending at `now`, from 40.0 % falling 0.5 %/h (last = 16.0 %), minimum 15 ⇒ result == now + 2 h.
  - `test_watering_inside_window_uses_only_later_readings`: dry-down to 18 %, jump to 45 %, then 24 h falling 0.4 %/h ⇒ slope from post-jump readings only.
  - `test_rising_or_flat_returns_none` (Review Focus 4).
  - `test_too_few_readings_returns_none` (5 readings) and `test_too_short_span_returns_none` (10 readings over 6 h).
  - `test_already_below_minimum_returns_now`.

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_prediction.py -q` — FAIL.

- [ ] **Step 3: Implement** `predict_dry_time`, then the entity: on each plant moisture update (throttled to once per hour), fetch the moisture sensor's history for `PREDICTION_WINDOW` with `homeassistant.components.recorder.history.state_changes_during_period` via `get_instance(hass).async_add_executor_job`, convert numeric states to `(last_updated, float)`, compute with `self._plant.min_moisture` value, set `native_value` (None ⇒ unknown).

- [ ] **Step 4: Run** full suite + black + ruff — PASS. Add `test_next_watering_entity_only_with_moisture_sensor` in test_care.py.

- [ ] **Step 5: Commit**
```bash
git add -A custom_components/plant tests
git commit -m "Care: predicted next watering from the moisture dry-down"
```

---

### Task 5: `care` block in `plant/get_info`, docs

**Files:**
- Modify: `custom_components/plant/__init__.py` (`websocket_info` ~887)
- Modify: `README.md` (care section), plant docs if a care page exists
- Test: `tests/test_websocket.py`

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces (the card's contract — the card plan depends on this exact shape):
```json
"care": {
  "todo_list": "todo.plant_care" | null,
  "modes":     {"water": "sensor", "fertilize": "interval", "repot": "interval", "prune": "none"},
  "intervals": {"water": 0, "fertilize": 15, "repot": 365, "prune": 0},
  "events":    {"water": "event.<...>_watered", "fertilize": "...", "repot": "...", "prune": "..."},
  "next_watering": "sensor.<...>_next_watering" | null,
  "marker_separator": " · "
}
```
  Added as `websocket_info["care"]` whenever `websocket_info` is not `{}`.

- [ ] **Step 1: Write failing tests** in `tests/test_websocket.py`:
  - `test_get_info_care_block`: plant with list, moisture sensor, `fertilize_interval` 15 ⇒ block equals the shape above with real entity ids from the registry.
  - `test_get_info_care_block_without_list` (Review Focus 5): `todo_list` is None, modes still present.

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_websocket.py -q` — FAIL.

- [ ] **Step 3: Implement** the block. Options dialog: add `options.step.plant_properties.data_description` entries in `strings.json` and `translations/en.json` (and de/dk where their `plant_properties` block exists, translated) for:
  - `moisture_trigger`: "Also decides watering tasks: checked, the moisture sensor opens and closes them; unchecked, watering follows the watering interval."
  - `conductivity_trigger`: "Also decides fertilizing tasks: checked, the conductivity sensor opens and closes them; unchecked, fertilizing follows the fertilize interval."
  - `illuminance_trigger` and `dli_trigger`: "Light problems also mark the Light & soil row on the plant-care card."
  README, "Use … as problem trigger": wherever the README describes these checkboxes (and in the care section, cross-linked), state plainly what each one now does for care, as a table — moisture: checked = moisture problems + water items opened/closed by the sensor, no Done; unchecked = no moisture problem, watering follows the watering interval (if set), detected waterings still count. Conductivity: same pattern for fertilizing (sensor closing an item records `fertilized`). Illuminance / DLI: checked = light problems, which turn the card's Light & soil row red; no care items. Then the rules: a checked trigger wins over an interval; changing a checkbox removes that care type's open items and the new mode plans its own; uncheck a trigger when you don't trust that sensor. README: care tasks section — the four care types, intervals, the trigger checkboxes now choosing sensor vs interval, fertilize sensor mode closing on conductivity recovery (and that it then records `fertilized`), the per-type event entities and triggers, the next-watering sensor, and that due dates exist only with a to-do list.

- [ ] **Step 4: Run** full suite + black + ruff — PASS.

- [ ] **Step 5: Commit and push**
```bash
git add -A custom_components/plant tests README.md docs/superpowers/plans/2026-11-23-plant-care-modes.md
git commit -m "Care: expose care data to the card via plant/get_info"
git push
```
Then watch PR #583's CI to green (`gh pr checks 583 --watch`).
