# Care Attributes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose OpenPlantbook's `care` fields (watering, sunlight, soil, pruning, fertilization) as separate `care_*` state attributes on the plant device.

**Architecture:** The plant integration requests `include: care` on every OPB `get` call, extracts the returned care fields into a `care` sub-dict inside the persisted `FLOW_PLANT_INFO`, and spreads them as individually-named `care_*` attributes in `PlantDevice.extra_state_attributes`. No new entities. Mirrors how `display_species`/limits/image are already fetched-once-and-persisted across the three code paths that build/refresh a plant.

**Tech Stack:** Python, Home Assistant custom integration, pytest + pytest-homeassistant-custom-component.

**Spec:** `docs/superpowers/specs/2026-06-01-care-attributes-design.md`

---

## File Structure

| File | Responsibility | Change |
|------|----------------|--------|
| `custom_components/plant/const.py` | Constants | Add include/care constants + canonical `CARE_FIELDS` list + `ATTR_CARE` storage key |
| `custom_components/plant/plant_helpers.py` | OPB calls + config generation | Request `include: care`; extract care into `FLOW_PLANT_INFO["care"]` |
| `custom_components/plant/__init__.py` | `PlantDevice` | Read stored care; emit `care_*` attributes |
| `custom_components/plant/config_flow.py` | Config + species-refresh flows | Persist care in the user-create path and the refresh path |
| `tests/fixtures/openplantbook_responses.py` | OPB mock data | Add care fields |
| `tests/conftest.py` | OPB service mock | Make `mock_get` care-aware (only returns care when `include=care`) |
| `tests/test_plant_helpers.py` | Unit tests | Fetch + extract tests |
| `tests/test_init.py` | Unit tests | Expose `care_*` attribute test |
| `tests/test_config_flow.py` | Unit tests | Persistence-path tests |

**Canonical values used throughout this plan:**
- `CARE_FIELDS = ["watering", "sunlight", "soil", "pruning", "fertilization"]`
- Attribute prefix: `care_` (e.g. `care_watering`)
- Storage key: `FLOW_PLANT_INFO["care"]` via `ATTR_CARE = "care"`
- Service param: `include` (`OPB_ATTR_INCLUDE`) = `"care"` (`OPB_INCLUDE_CARE`)

---

## Task 1: Constants

**Files:**
- Modify: `custom_components/plant/const.py`
- Test: `tests/test_plant_helpers.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_plant_helpers.py` (top-level, after the existing imports add the new names to the `from custom_components.plant.const import (...)` block, then add this test class at the end of the file):

```python
class TestCareConstants:
    """Tests for the care-field constants."""

    def test_care_fields_canonical_list(self) -> None:
        from custom_components.plant.const import CARE_FIELDS

        assert CARE_FIELDS == [
            "watering",
            "sunlight",
            "soil",
            "pruning",
            "fertilization",
        ]

    def test_include_constants(self) -> None:
        from custom_components.plant.const import (
            ATTR_CARE,
            OPB_ATTR_INCLUDE,
            OPB_INCLUDE_CARE,
        )

        assert OPB_ATTR_INCLUDE == "include"
        assert OPB_INCLUDE_CARE == "care"
        assert ATTR_CARE == "care"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_plant_helpers.py::TestCareConstants -v`
Expected: FAIL with `ImportError: cannot import name 'CARE_FIELDS'`

- [ ] **Step 3: Add the constants**

In `custom_components/plant/const.py`, near the other `OPB_*` constants (around line 194-198, after `OPB_DISPLAY_PID`), add:

```python
OPB_ATTR_INCLUDE = "include"
OPB_INCLUDE_CARE = "care"
```

Near the `ATTR_*` constants (e.g. after `ATTR_SPECIES` around line 39), add:

```python
ATTR_CARE = "care"
```

Add the canonical field list (place it after the `CONF_PLANTBOOK_MAPPING` block at the end of the file, or alongside the other lists):

```python
# OpenPlantbook `include: care` returns these free-text fields per species.
# Order is the canonical attribute order used when exposing them.
CARE_FIELDS = ["watering", "sunlight", "soil", "pruning", "fertilization"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_plant_helpers.py::TestCareConstants -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add custom_components/plant/const.py tests/test_plant_helpers.py
git commit -m "feat: add care-field constants for OPB include:care

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Request `include: care` from OpenPlantbook

**Files:**
- Modify: `custom_components/plant/plant_helpers.py:177-179` (inside `openplantbook_get`)
- Test: `tests/test_plant_helpers.py`

- [ ] **Step 1: Write the failing test**

Add this test to the `TestPlantHelperGet` class in `tests/test_plant_helpers.py`. It patches the service call directly so it can inspect the `service_data` passed to OPB:

```python
    async def test_openplantbook_get_requests_care(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Every OPB get must request the care category via include=care."""
        from unittest.mock import AsyncMock, patch

        from custom_components.plant.const import DOMAIN_PLANTBOOK
        from tests.fixtures.openplantbook_responses import (
            GET_RESULT_MONSTERA_DELICIOSA,
        )

        helper = PlantHelper(hass)
        mock_call = AsyncMock(return_value=GET_RESULT_MONSTERA_DELICIOSA)
        with patch(
            "homeassistant.core.ServiceRegistry.async_services",
            return_value={DOMAIN_PLANTBOOK: {"search": None, "get": None}},
        ):
            with patch(
                "homeassistant.core.ServiceRegistry.async_call",
                new=mock_call,
            ):
                await helper.openplantbook_get("monstera deliciosa")

        assert mock_call.await_count == 1
        service_data = mock_call.await_args.kwargs["service_data"]
        assert service_data["include"] == "care"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_plant_helpers.py::TestPlantHelperGet::test_openplantbook_get_requests_care -v`
Expected: FAIL with `KeyError: 'include'`

- [ ] **Step 3: Implement**

In `custom_components/plant/plant_helpers.py`, add `OPB_ATTR_INCLUDE` and `OPB_INCLUDE_CARE` to the existing `from .const import (...)` block. Then in `openplantbook_get`, the current block is:

```python
        service_data = {ATTR_SPECIES: species.lower()}
        if not cache:
            service_data["cache"] = False
```

Change it to:

```python
        service_data = {
            ATTR_SPECIES: species.lower(),
            OPB_ATTR_INCLUDE: OPB_INCLUDE_CARE,
        }
        if not cache:
            service_data["cache"] = False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_plant_helpers.py::TestPlantHelperGet -v`
Expected: PASS (all get tests, including the new one)

- [ ] **Step 5: Commit**

```bash
git add custom_components/plant/plant_helpers.py tests/test_plant_helpers.py
git commit -m "feat: request OPB care data on every species get

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Extract care into `FLOW_PLANT_INFO["care"]`

**Files:**
- Modify: `tests/fixtures/openplantbook_responses.py` (add care data)
- Modify: `tests/conftest.py:238-243` (care-aware `mock_get`)
- Modify: `custom_components/plant/plant_helpers.py` (`generate_configentry`)
- Test: `tests/test_plant_helpers.py`

- [ ] **Step 1: Add care data to the fixtures**

In `tests/fixtures/openplantbook_responses.py`, add a care payload constant at the end of the file:

```python
# Care fields returned by OPB only when include=care is requested.
CARE_MONSTERA_DELICIOSA = {
    "watering": "Likes wet envs; reduce watering in winter.",
    "sunlight": "Relatively shade-tolerant, prefers half-shade.",
    "soil": "Well-draining, peat-based potting mix.",
    "pruning": "Timely remove dead and yellowish leaves.",
    "fertilization": "Dilute fertilizer once every 15 days.",
}
```

- [ ] **Step 2: Make the conftest mock care-aware**

In `tests/conftest.py`, add `CARE_MONSTERA_DELICIOSA` to the fixtures import block (around line 61 where `GET_RESULT_MONSTERA_DELICIOSA` is imported). Then change the `mock_get` inside `mock_openplantbook_services` (lines 238-243) from:

```python
    async def mock_get(domain, service, service_data, blocking, return_response):
        """Mock get service."""
        species = service_data.get("species", "").lower()
        if species == "monstera deliciosa":
            return GET_RESULT_MONSTERA_DELICIOSA
        return None
```

to:

```python
    async def mock_get(domain, service, service_data, blocking, return_response):
        """Mock get service."""
        species = service_data.get("species", "").lower()
        if species == "monstera deliciosa":
            result = dict(GET_RESULT_MONSTERA_DELICIOSA)
            if service_data.get("include") == "care":
                result.update(CARE_MONSTERA_DELICIOSA)
            return result
        return None
```

- [ ] **Step 3: Write the failing test**

Add to `TestPlantHelperGenerateConfigentry` in `tests/test_plant_helpers.py` (add `ATTR_CARE` to the const import block and import `CARE_MONSTERA_DELICIOSA` from the fixtures):

```python
    async def test_generate_configentry_stores_care(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """Care fields from OPB are stored under FLOW_PLANT_INFO['care']."""
        helper = PlantHelper(hass)
        config = {
            ATTR_NAME: "My Monstera",
            ATTR_SPECIES: "monstera deliciosa",
            ATTR_SENSORS: {},
        }

        result = await helper.generate_configentry(config)

        care = result[FLOW_PLANT_INFO][ATTR_CARE]
        assert care["watering"] == CARE_MONSTERA_DELICIOSA["watering"]
        assert care["sunlight"] == CARE_MONSTERA_DELICIOSA["sunlight"]
        assert care["soil"] == CARE_MONSTERA_DELICIOSA["soil"]
        assert care["pruning"] == CARE_MONSTERA_DELICIOSA["pruning"]
        assert care["fertilization"] == CARE_MONSTERA_DELICIOSA["fertilization"]

    async def test_generate_configentry_omits_absent_care_fields(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
        monkeypatch,
    ) -> None:
        """Care fields OPB does not return are not stored (no empty strings)."""
        import custom_components.plant.plant_helpers as ph

        async def partial_care_get(self, species, cache=True):
            return {
                "pid": "monstera deliciosa",
                "display_pid": "Monstera deliciosa",
                "max_soil_moist": 60,
                "min_soil_moist": 20,
                "max_light_lux": 35000,
                "min_light_lux": 1500,
                "watering": "Water weekly.",
                # sunlight/soil/pruning/fertilization deliberately absent
            }

        monkeypatch.setattr(ph.PlantHelper, "openplantbook_get", partial_care_get)

        helper = ph.PlantHelper(hass)
        config = {
            ATTR_NAME: "My Monstera",
            ATTR_SPECIES: "monstera deliciosa",
            ATTR_SENSORS: {},
        }

        result = await helper.generate_configentry(config)

        care = result[FLOW_PLANT_INFO][ATTR_CARE]
        assert care == {"watering": "Water weekly."}
```

- [ ] **Step 4: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_plant_helpers.py::TestPlantHelperGenerateConfigentry::test_generate_configentry_stores_care -v`
Expected: FAIL with `KeyError: 'care'`

- [ ] **Step 5: Implement the extraction**

In `custom_components/plant/plant_helpers.py`, add `ATTR_CARE` and `CARE_FIELDS` to the `from .const import (...)` block.

Initialize a `care_data` default alongside the other defaults in `generate_configentry` (near line 296, where `data_source = DATA_SOURCE_DEFAULT` is set):

```python
        care_data: dict[str, Any] = {}
```

Inside the `if opb_plant:` block (anywhere after `data_source = DATA_SOURCE_PLANTBOOK`, e.g. right before the `_LOGGER.debug("Parsing input config...` line), add:

```python
            care_data = {
                field: opb_plant[field]
                for field in CARE_FIELDS
                if opb_plant.get(field)
            }
```

Finally, add the care sub-dict to the returned `FLOW_PLANT_INFO`. In the `ret = { ... FLOW_PLANT_INFO: { ... } }` literal, add this entry alongside `OPB_DISPLAY_PID` (e.g. right after the `OPB_DISPLAY_PID: display_species or "",` line):

```python
                ATTR_CARE: care_data,
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_plant_helpers.py -v`
Expected: PASS (all helper tests, including both new care tests)

- [ ] **Step 7: Commit**

```bash
git add custom_components/plant/plant_helpers.py tests/conftest.py tests/fixtures/openplantbook_responses.py tests/test_plant_helpers.py
git commit -m "feat: persist OPB care fields in FLOW_PLANT_INFO

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Expose `care_*` attributes on the plant device

**Files:**
- Modify: `custom_components/plant/__init__.py` (`PlantDevice.__init__` ~line 497, `extra_state_attributes` ~line 669)
- Modify: `tests/conftest.py` (add optional `care` to `create_plant_config_data`)
- Test: `tests/test_init.py`

- [ ] **Step 1: Allow the test fixture to carry care data**

In `tests/conftest.py`, find `create_plant_config_data(...)` (the helper that builds the dict shown around line 121). Add a `care=None` parameter to its signature, and inside the returned `FLOW_PLANT_INFO` dict add:

```python
            ATTR_CARE: care or {},
```

Add `ATTR_CARE` to the const import block in `tests/conftest.py` if not already present.

- [ ] **Step 2: Write the failing test**

Add to `TestPlantDevice` in `tests/test_init.py` (add `ATTR_CARE` to the const import block; import `create_plant_config_data` if the test builds its own entry — check the top of the file for how other tests import it):

```python
    async def test_plant_device_care_attributes(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Care fields are exposed as separate care_* attributes."""
        from pytest_homeassistant_custom_component.common import MockConfigEntry

        from tests.conftest import create_plant_config_data

        care = {
            "watering": "Water weekly.",
            "sunlight": "Bright indirect light.",
            # soil/pruning/fertilization absent on purpose
        }
        data = create_plant_config_data(care=care)
        entry = MockConfigEntry(domain=DOMAIN, data=data, options={})
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]
        plant.plant_complete = True

        attrs = plant.extra_state_attributes
        assert attrs["care_watering"] == "Water weekly."
        assert attrs["care_sunlight"] == "Bright indirect light."
        # Absent fields must not appear, not even as empty strings
        assert "care_soil" not in attrs
        assert "care_pruning" not in attrs
        assert "care_fertilization" not in attrs
```

> Note: check how `create_plant_config_data` and `ATTR_PLANT` are imported by existing `test_init.py` tests and match that style; the import lines above are illustrative.

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_init.py::TestPlantDevice::test_plant_device_care_attributes -v`
Expected: FAIL with `KeyError: 'care_watering'`

- [ ] **Step 4: Implement**

In `custom_components/plant/__init__.py`, add `ATTR_CARE` to the `from .const import (...)` block.

In `PlantDevice.__init__`, after the `self.species = ...` assignment (around line 497), add:

```python
        # Static per-species care text from OpenPlantbook (include: care).
        # Stored at config/refresh time; only fields OPB returned are present.
        self.care = self._config.data[FLOW_PLANT_INFO].get(ATTR_CARE, {})
```

In `extra_state_attributes`, the current return is:

```python
        attributes = {
            ATTR_SPECIES: self.display_species,
            ...
            f"{ATTR_SPECIES}_original": self.species,
        }
        return attributes
```

Change the end to spread the care fields in before returning:

```python
        attributes = {
            ATTR_SPECIES: self.display_species,
            ...
            f"{ATTR_SPECIES}_original": self.species,
        }
        for field, value in self.care.items():
            attributes[f"care_{field}"] = value
        return attributes
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_init.py::TestPlantDevice -v`
Expected: PASS (all plant-device tests, including the new one)

- [ ] **Step 6: Commit**

```bash
git add custom_components/plant/__init__.py tests/conftest.py tests/test_init.py
git commit -m "feat: expose OPB care fields as care_* plant attributes

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Persist care in the config-flow user-create path

**Files:**
- Modify: `custom_components/plant/config_flow.py` (`async_step_limits`, after the `generate_configentry` call ~line 335)
- Test: `tests/test_config_flow.py`

**Why:** The user-create flow builds `self.plant_info` manually and stores it at `async_step_limits_done` (line 533). It calls `generate_configentry` only for limit/display defaults, so care must be copied into `self.plant_info` explicitly or it is lost on create.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config_flow.py` (match the existing style there for driving the flow — find an existing end-to-end create test and mirror its `async_init` / `async_configure` calls). The assertion that matters:

```python
    async def test_create_flow_persists_care(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """A plant created via the UI flow stores OPB care fields."""
        from custom_components.plant.const import (
            ATTR_CARE,
            DOMAIN,
            FLOW_PLANT_INFO,
        )
        from tests.fixtures.openplantbook_responses import (
            CARE_MONSTERA_DELICIOSA,
        )

        # Drive the user -> select_species -> limits -> limits_done flow for
        # species "monstera deliciosa" exactly as the existing create-flow
        # test in this file does, capturing the final result dict.
        result = await _run_full_create_flow(hass, species="monstera deliciosa")

        assert result["type"] == "create_entry"
        care = result["data"][FLOW_PLANT_INFO][ATTR_CARE]
        assert care["watering"] == CARE_MONSTERA_DELICIOSA["watering"]
```

> `_run_full_create_flow` is a stand-in: reuse whatever the existing successful-create test in `tests/test_config_flow.py` already does to walk the steps, then assert on `result["data"]`. If no such helper exists, inline the `async_init`/`async_configure` calls copied from that test.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_config_flow.py::*::test_create_flow_persists_care -v`
Expected: FAIL with `KeyError: 'care'` (care not copied into `self.plant_info`)

- [ ] **Step 3: Implement**

In `custom_components/plant/config_flow.py`, add `ATTR_CARE` to the `from .const import (...)` block. In `async_step_limits`, immediately after the `plant_config = await plant_helper.generate_configentry(...)` call (the block ending at line 335), add:

```python
        care = plant_config[FLOW_PLANT_INFO].get(ATTR_CARE)
        if care:
            self.plant_info[ATTR_CARE] = care
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_config_flow.py -v`
Expected: PASS (all config-flow tests, including the new one)

- [ ] **Step 5: Commit**

```bash
git add custom_components/plant/config_flow.py tests/test_config_flow.py
git commit -m "feat: persist care fields when creating a plant via the UI

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Persist + refresh care in the species-refresh path

**Files:**
- Modify: `custom_components/plant/config_flow.py` (`refresh_plant_from_openplantbook` ~lines 905-954)
- Test: `tests/test_config_flow.py`

**Why:** When a user forces a species update, `refresh_plant_from_openplantbook` mutates `plant.*` and writes `entry.data[FLOW_PLANT_INFO]` atomically. Care must be updated on both the live `plant` object (so `extra_state_attributes` reflects it without a reload) and the persisted `plant_info`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config_flow.py`. Find the existing test that exercises `refresh_plant_from_openplantbook` (search the file for `refresh_plant_from_openplantbook`) and mirror its setup; the new assertions:

```python
    async def test_refresh_updates_care(
        self,
        hass: HomeAssistant,
        mock_openplantbook_services,
    ) -> None:
        """Forcing a species refresh updates both plant.care and entry data."""
        from custom_components.plant.config_flow import (
            refresh_plant_from_openplantbook,
        )
        from custom_components.plant.const import ATTR_CARE, FLOW_PLANT_INFO
        from tests.fixtures.openplantbook_responses import (
            CARE_MONSTERA_DELICIOSA,
        )

        # Set up a plant entry (any species) exactly as the existing refresh
        # test does, obtaining `hass`, `entry`, and the live `plant` object.
        entry, plant = await _setup_plant_for_refresh(hass)

        ok = await refresh_plant_from_openplantbook(
            hass, entry, plant, new_species="monstera deliciosa"
        )

        assert ok is True
        assert plant.care["watering"] == CARE_MONSTERA_DELICIOSA["watering"]
        stored = entry.data[FLOW_PLANT_INFO][ATTR_CARE]
        assert stored["watering"] == CARE_MONSTERA_DELICIOSA["watering"]
```

> `_setup_plant_for_refresh` is a stand-in: reuse the existing refresh test's setup in this file to get `entry` and the live `plant`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_config_flow.py::*::test_refresh_updates_care -v`
Expected: FAIL with `KeyError: 'watering'` (plant.care not updated)

- [ ] **Step 3: Implement**

In `refresh_plant_from_openplantbook`, after the existing plant-side mutations (after `plant.display_species = ...` around line 910), add:

```python
    plant.care = plant_config[FLOW_PLANT_INFO].get(ATTR_CARE, {})
```

Then in the atomic-update block (lines 946-949), after `plant_info[FLOW_PLANT_LIMITS] = dict(limits)`, add:

```python
    plant_info[ATTR_CARE] = dict(plant.care)
```

(`ATTR_CARE` was already added to the const import in Task 5.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_config_flow.py -v`
Expected: PASS (all config-flow tests, including the new one)

- [ ] **Step 5: Commit**

```bash
git add custom_components/plant/config_flow.py tests/test_config_flow.py
git commit -m "feat: update care fields on forced species refresh

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Full test suite, lint, and format

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `.venv/bin/pytest tests/ -v`
Expected: PASS (no regressions)

- [ ] **Step 2: Lint**

Run: `ruff check custom_components/plant/`
Expected: no errors. If import-order issues, run `ruff check --fix custom_components/plant/`.

- [ ] **Step 3: Format check**

Run: `.venv/bin/black . --check --fast --diff`
Expected: no diff. If any, run `.venv/bin/black .` and re-run tests.

- [ ] **Step 4: Commit any lint/format fixes**

```bash
git add -A
git commit -m "chore: lint and format for care attributes

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Release note

**Files:**
- Modify/Create: project release-notes location (check how prior notes are recorded; e.g. README "What's new" section or a `docs/` changelog — mirror the existing convention)

- [ ] **Step 1: Add a release note**

Add a user-facing note capturing:

> **New:** Plants now expose OpenPlantbook care guidance as `care_watering`, `care_sunlight`, `care_soil`, `care_pruning`, and `care_fertilization` attributes (when OpenPlantbook provides them). **Existing plants must be refreshed** (force a species update) to populate care data — newly added plants get it automatically. Only fields OpenPlantbook returns appear.

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "docs: release note for care attributes

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Out of scope (phase 2)

Flower-card display of selected care fields via the `plant/get_info` websocket — see the spec's "Out of scope" section. Not part of this plan.

---

## Self-review notes

- **Spec coverage:** fetch (Task 2), constants (Task 1), persist into `FLOW_PLANT_INFO["care"]` via the canonical generate path (Task 3) plus the two additional persistence paths the spec's data-flow implies — UI create (Task 5) and forced refresh (Task 6) — expose as `care_*` (Task 4), absent-field omission (Tasks 3 & 4), tests (each task), release note (Task 8). All covered.
- **Naming consistency:** `ATTR_CARE="care"`, `CARE_FIELDS`, `OPB_ATTR_INCLUDE="include"`, `OPB_INCLUDE_CARE="care"`, attribute prefix `care_`, storage key `FLOW_PLANT_INFO["care"]` — used identically across all tasks.
- **No `strings.json`/`translations` work:** state attributes have no display-name translations (the CLAUDE.md translation rule applies to entities only).
