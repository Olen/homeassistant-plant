# Care Attributes — Design

**Date:** 2026-06-01
**Status:** Approved design, ready for implementation planning

## Summary

OpenPlantbook (OPB) integration v1.5.0 added a `care` data category, requested
via `include: care` on its `get` service. It returns five free-text fields for a
species: `watering`, `sunlight`, `soil`, `pruning`, `fertilization`.

This change makes that care text **available** in the plant integration as
separate, individually-named state attributes on the plant device entity. It
does **not** add any new entities and does **not** change the flower-card (see
Out of Scope).

## Motivation

Users want access to per-species care guidance (how to water, light, prune,
etc.) within Home Assistant so they can template against it, use it in
automations, or surface it on a dashboard. The data already exists in OPB; the
plant integration just needs to fetch, persist, and expose it.

## Why attributes, not entities

The care fields are **static, free-text, per-species reference content** — not
measured, changing state. That rules out sensors. Two decisive points:

- **HA caps entity state at 255 characters** (`MAX_LENGTH_STATE_STATE`). OPB care
  strings are prose and can exceed that; a sensor whose state goes over the limit
  is rejected/logged as an error. State attributes have a much larger budget
  (~16 KB), so they sidestep this.
- `EntityCategory.DIAGNOSTIC` is semantically about **device operational health**
  (signal, battery, uptime, firmware), not informational content. Using it just
  to tuck care text into a collapsed expander overloads the category.

The integration already has a clear convention: *measured/changing → entity;
static species facts → attribute* (see `species` / `species_original` on the
plant device). Care fields slot into the second bucket.

## Design

Mirrors how `display_species`, image, and limits already flow: fetched once at
config time, persisted into the config entry, read at runtime.

### 1. Fetch — `plant_helpers.py` (`openplantbook_get`)

Always request care data by passing `include: care` in the OPB `get` service
call. One extra param on an existing call; OPB caches results, so the extra
payload cost is negligible.

### 2. Constants — `const.py`

Add:
- An OPB include constant (e.g. `OPB_ATTR_INCLUDE = "include"`,
  `OPB_INCLUDE_CARE = "care"`).
- A canonical list of the five care field names (e.g. `CARE_FIELDS`) used by both
  the persist and expose steps so the field set is defined in exactly one place.

### 3. Persist — `plant_helpers.py` (`generate_configentry`)

After a successful `opb_plant` fetch, extract the care fields that are present
into a new sub-dict `FLOW_PLANT_INFO["care"]` (key → value, only for fields OPB
actually returned). Stored in the config entry; survives restarts and OPB being
offline/uninstalled. No empty `""` fields are stored.

### 4. Expose — `__init__.py` (`PlantDevice.extra_state_attributes`)

Read the stored `care` dict and spread each field as a separate attribute with a
`care_` prefix, alongside the existing species attributes:

- `care_watering`
- `care_sunlight`
- `care_soil`
- `care_pruning`
- `care_fertilization`

Only fields present in storage are emitted — no empty `care_*: ""` clutter. The
`care_` prefix namespaces them and groups them in the attribute list.

## Decisions

- **Attribute naming:** `care_` prefix (namespaced, collision-safe, groups
  together), not bare OPB field names.
- **Fetch policy:** always include `care` (available by default), not behind a
  config option.

## Behavior notes (for release notes)

- **Existing plants** won't show care data until their **species is refreshed**
  (the `FLOW_FORCE_SPECIES_UPDATE` path), because care is captured at config
  time. This matches how a species' limits/image already behave. Worth a release
  note, same spirit as the #438/#440 imperial-temperature note.
- Care text **persists** in the config entry, so it remains available when OPB is
  offline or uninstalled.
- Plants whose species OPB has no care data for simply get no `care_*` attributes.

## Testing

- When the mocked OPB `get` returns care fields, the plant device exposes the
  corresponding `care_*` attributes with the expected values.
- Fields OPB omits are not emitted as attributes (no empty strings).
- `include: care` is actually passed through to the OPB service call.
- A species with no care data produces no `care_*` attributes and does not error.

## Out of scope (potential phase 2)

**Flower-card integration.** A future change may let the
[lovelace-flower-card](https://github.com/Olen/lovelace-flower-card) optionally
display selected care fields. The per-field separation in this design is the
enabler for that: the card (via the `plant/get_info` websocket) could let users
tick which care fields to show. That work — websocket payload changes here and
rendering in the card repo — is deliberately **not** part of this spec.

## Explicitly not doing

- No new entities (sensor / diagnostic / config / text).
- No `strings.json` / `translations/` changes — those govern *entity* names, not
  state attributes, so the usual translation rule does not apply here.
- No flower-card or `plant/get_info` websocket changes in this phase.
