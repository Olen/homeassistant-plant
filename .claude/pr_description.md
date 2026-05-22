# feat: structured `problems` attribute and logbook integration

## The problem

When a plant changes state to `problem`, Home Assistant's activity feed shows:

> *Oregano changed to problem — 17:57*

To find out *what* went wrong, you have to open the entity details panel and read through a dozen individual `_status` attributes — one per sensor. There is no single place that tells you "conductivity is too low, currently 352, minimum is 400".

## What's new

### `problems` attribute

Each plant entity now exposes a `problems` attribute: a structured list of every active threshold violation. Each entry contains everything needed to understand the problem at a glance.

```yaml
problems:
  - sensor_type: conductivity
    status: Low
    current: "352.0"
    min: "400"
    max: "900"
  - sensor_type: dli
    status: Low
    current: "0.69"
    min: "9"
    max: "16"
```

When the plant is healthy, `problems` is an empty list `[]`.

> *Screenshot: entity details panel → three-dot menu → Details, showing the `problems` structure alongside the individual `_status` fields*

<!-- ADD SCREENSHOT HERE -->

### Logbook integration

The HA activity feed now shows a specific entry whenever a problem appears or clears — not just a state change notification:

> *Oregano — conductivity low — current: 352.0, min: 400*
> *Oregano — dli low — current: 0.69, min: 9*
> *Oregano — conductivity back in range*

Duplicate entries are suppressed: if the same problem persists across multiple update cycles, only one logbook entry is written at onset and one at recovery.

> *Screenshot: Logbook panel filtered by plant entity, showing problem onset and recovery entries*

<!-- ADD SCREENSHOT HERE -->

## Using `problems` in automations and dashboards

The attribute is designed to be template-friendly. Example dashboard card showing all plants with active problems:

```yaml
type: custom:markdown-card
content: |
  {% for state in states.plant %}
  {% set problems = state.attributes.get('problems', []) %}
  {% if problems %}
  **{{ state.name }}**
  {% for p in problems %}
  - {{ p.sensor_type | replace('_', ' ') | title }}: {{ p.status | lower }} — current: {{ p.current }}, {{ 'min: ' + p.min if p.status == 'Low' else 'max: ' + p.max }}
  {% endfor %}

  {% endif %}
  {% endfor %}
```

## Implementation notes

- `problems` is built inside `PlantDevice.update()` using a compact `_problem_sensors` dict collected at each threshold trigger site. Adding a new sensor type to problem tracking requires one extra line at the trigger site — the rest is handled generically.
- Logbook writes are handled by a dedicated `_log_problem_changes()` method to keep `update()` focused on threshold checking.
- `log_entry()` (sync, thread-safe) is used since `update()` runs in an executor thread.
- `logbook` added to `after_dependencies` in `manifest.json`.
- No changes to `sensor.py`, `number.py`, `config_flow.py`, or existing attribute structure.

## Known limitations

On HA restart or integration reload, `_logged_problem_types` resets to empty, so any currently active problems are re-logged as new onsets. Two approaches to fix this in a future PR: (1) extend `PlantDevice` with `RestoreEntity` and restore from `async_get_last_state()`; (2) read `hass.states.get(entity_id)` in `async_added_to_hass` without changing the base class.

## Tests

- `tests/test_problems.py`: 14 tests covering the `problems` attribute structure, multiple simultaneous problems, recovery, and logbook deduplication.
