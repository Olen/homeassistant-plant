# Design: `plant.*` triggers & conditions for HA 2026.7

- **Date:** 2026-07-27
- **Status:** Approved (design), pending implementation plan
- **Feedback issue:** #480
- **Prototype (strawman) PR:** #481 (`prototype/2026.7-triggers`)
- **Supersedes:** the strawman — this is the real, complete implementation

## Background

Home Assistant 2026.7 introduces **purpose-specific triggers and conditions**: an
integration can teach the automation engine its own triggers/conditions
(e.g. `battery.became_low`), and *custom* integrations are explicitly supported.
The platform is discovered by HA calling `platform.async_get_triggers(hass)` /
`platform.async_get_conditions(hass)` on the integration's `trigger.py` /
`condition.py`.

The plant integration's value-add over core's generic purpose triggers is
**auto-thresholding**: core's `temperature.crossed_threshold` makes the user
supply a number (or point at a threshold entity); the plant already computes a
per-measurement `<m>_status` (Low / High / ok) from the species-configured
min/max **with hysteresis**, so `plant.*` triggers fire on the plant's own
threshold with zero user input.

### API verification (done before this design)

Verified against the **released** `homeassistant==2026.7.4` source (not the
`2026.7.0b1` the strawman was written against):

- Every helper the strawman uses exists in 2026.7.4 with **identical signatures**
  to b1: `make_entity_target_state_trigger`, `make_entity_state_condition`,
  `DomainSpec` (incl. `value_source`), `async_track_target_selector_state_change_event`,
  `Trigger` / `TriggerConfig` / `TriggerActionRunner`, `Condition` / `ConditionConfig`.
- Discovery hooks confirmed: `helpers/trigger.py` calls
  `platform.async_get_triggers(hass)`; `helpers/condition.py` calls
  `platform.async_get_conditions(hass)`.
- Strawman's own tests pass 8/8 on the installed HA.

**Correctness gap the strawman missed (must fix here):** HA **2025.8** (our support
floor) *already* has trigger/condition platform discovery (`async_get_triggers`
exists) and **will import** `trigger.py`/`condition.py`, but it lacks the newer
helper symbols (`make_entity_target_state_trigger`, `TriggerConfig`,
`TriggerActionRunner`). The strawman imports those at module level with no guard,
so its "inert on < 2026.7" claim is false. This design makes version-safety a
first-class requirement (see §6).

## Goals

- Ship the full, consistent `plant.*` trigger/condition surface for HA 2026.7+.
- Zero-config auto-thresholding: users never type a threshold or pick a sensor.
- Stay clean and inert on HA 2025.8–2026.6 (we still support 2025.8+).
- Table-generated surface (loop over a measurement table), not hand-written per key.

## Non-goals

- **No `crossed_threshold` family.** For standard-device-class measurements core
  already provides it (and it can read the plant's `number.<plant>_min_*`/`_max_*`
  threshold entities); for custom classes the `became_low/high` auto-threshold is
  strictly nicer UX. A manual-threshold `plant.*` would duplicate core / reintroduce
  the friction we remove. YAGNI — can add later.
- No change to how the plant computes `<m>_status` or hysteresis.
- No new device classes on the moisture/conductivity sensors (deferred; #480 Q4).

## Measurement taxonomy

Two sets, derived from the sensor classes in `sensor.py`:

- **Status measurements (9)** — have a `<m>_status` attribute (Low/High/ok):
  `moisture, conductivity, temperature, soil_temperature, humidity, illuminance,
  co2, dli, vpd`. These get the per-measurement **status** family.
- **Externally-sourced measurements (7)** — subclasses of `PlantCurrentStatus`
  with a configured `FLOW_SENSOR_*` external source:
  `moisture, conductivity, temperature, soil_temperature, humidity, illuminance,
  co2`. These get the per-measurement **stale** family.
- **Derived (`dli, vpd, ppfd`)** have no source of their own; their staleness
  inherits from their inputs, so they get **no** stale family. (`ppfd` also has no
  `<m>_status`, so it appears in neither family.)

## Families, naming, and surface

Naming grounded in core 2026.7.4 conventions (`battery.became_low`/`is_low`,
`update.became_available`, `motion.detected`/`cleared`, universal `is_*` conditions).

| Family | Applies to | Triggers | Conditions |
|---|---|---|---|
| **Aggregate** | the plant (1) | `problem_detected`, `problem_cleared` | `has_problem` |
| **Per-measurement status** | 9 | `<m>_became_low`, `<m>_became_high`, `<m>_became_ok` | `<m>_is_low`, `<m>_is_high`, `<m>_is_ok` |
| **Per-measurement stale** | 7 external | `<m>_sensor_became_stale`, `<m>_sensor_became_fresh` | `<m>_sensor_is_stale` |

**Totals: ~43 triggers, ~35 conditions.** Large but deliberate — matches core's
per-measurement philosophy (`air_quality` is ~18 keys), table-generated, and
approved. `<m>` uses the lowercase measurement key in the trigger name even though
`STATE_LOW`/`STATE_HIGH` are `"Low"`/`"High"` and `STATE_OK` is `"ok"`.

### Naming rationale (decided)

- Aggregate uses **detected/cleared** (motion/occupancy style); `problem_cleared`
  is unambiguous even with multiple simultaneous problems (preferred over
  `no_longer_problem` / `became_ok` for the aggregate).
- Aggregate condition is **`has_problem`** (not `is_problem`): "problem" is a noun,
  so `has_` is the grammatically correct verb; the one intentional exception to the
  `is_*` pattern.
- Per-measurement recovery is **`became_ok` / `is_ok`** (not `became_normal`):
  matches the plant's own `<m>_status == "ok"` value exactly.
- Stale recovery is **`became_fresh`** (stale↔fresh); condition stays a single
  `sensor_is_stale` (gate "fresh" with `not`), mirroring aggregate's two-trigger /
  one-condition shape.

## Targeting model (uniform, zero-config)

Every trigger and condition targets the **plant entity** — the user only picks
*which plant*.

- **Status** families read the plant's own `<m>_status` attribute via
  `DomainSpec(value_source="<m>_status")` + `make_entity_target_state_trigger` /
  `make_entity_state_condition`. The threshold is the plant's configured min/max
  with hysteresis — no user input.
- **Stale** families: given the plant entity, the integration resolves that
  measurement's **external source sensor** (the plant's `sensor.<plant>_<m>` carries
  an `external_sensor` reference / the config `FLOW_SENSOR_<M>`), and watches *that
  external sensor*. The plant's internal mirror sensor is never watched — it cannot
  be independently stale, and the external sensor is the root cause we care about.

This removes the strawman's device-vs-entity targeting question entirely.

## Stale detection semantics

- **Stale** = the external source sensor is `unavailable`/`unknown` **OR** has not
  produced an update within `for` (**default 24h**, overridable per automation).
  Two failure modes (drops to unavailable, or silently stops updating with a stale
  last value) are both caught.
- **Recovery** (`<m>_sensor_became_fresh`) fires on the reverse transition (a fresh
  update arrives, or it returns from unavailable). The strawman already tracks a
  `stale` set and re-arms on fresh updates; recovery fires on the stale→fresh edge.
- Implemented as a custom `Trigger`/`Condition` (per-measurement) that resolves the
  external sensor and manages a freshness timer via `async_call_later`.

## Version safety (§6)

`trigger.py` and `condition.py` must not import 2026.7-only symbols at module top
level. Approach:

- Top-level imports limited to always-available symbols.
- **Feature-detect** the 2026.7 API (e.g. `hasattr(homeassistant.helpers.trigger,
  "make_entity_target_state_trigger")`), lazily importing the new API inside
  `async_get_triggers` / `async_get_conditions`.
- On HA < 2026.7, `async_get_triggers` / `async_get_conditions` return `{}` — no
  triggers/conditions registered, no import error, no log noise.
- Feature-detection is preferred over a version-string check (robust to backports).

## File structure

- `custom_components/plant/trigger.py` — `async_get_triggers`, the status-trigger
  factory (`make_entity_target_state_trigger` + `DomainSpec(value_source=...)`),
  the aggregate triggers, and the per-measurement `PlantSensorStale`/`Fresh`
  triggers. Built from a measurement table.
- `custom_components/plant/condition.py` — mirror: `async_get_conditions`, status
  conditions, `has_problem`, per-measurement `sensor_is_stale`.
- `custom_components/plant/triggers.yaml` / `conditions.yaml` — descriptions/selectors
  for the UI, generated to match the table.
- `tests/test_triggers.py` / `tests/test_conditions.py` — behavioral tests, gated
  to run only on HA >= 2026.7, plus a **version-safety test** asserting the module
  imports cleanly and registers nothing on an older-API stub.
- Shared measurement table (single source of truth for the generated surface),
  likely in `const.py` or a small `automation_meta.py`.

## Testing strategy

- Behavioral trigger/condition tests gated on HA >= 2026.7 (feature-detected), run
  in CI's "HA latest" job (currently 2026.7.4).
- Version-safety: a test that importing `trigger.py`/`condition.py` on an
  environment lacking the new API yields empty `async_get_triggers`/`_conditions`
  and raises nothing — so the "HA 2025.8" CI job stays green and the integration
  loads cleanly.
- During implementation, exercise at least one status trigger, the aggregate
  detected/cleared pair, and one stale/fresh pair end-to-end against real 2026.7.4.

## Risks / open items

- The 2026.7 purpose-trigger platform API, though released, is young; monitor for
  changes in later 2026.7.x/2026.8. Feature-detection limits blast radius.
- Stale resolution depends on the `external_sensor` reference staying accurate
  across the "replace sensor" service and reloads — cover in tests.
- Surface size (~43/~35) is intentional; revisit only if user feedback finds it
  unwieldy in the UI.
