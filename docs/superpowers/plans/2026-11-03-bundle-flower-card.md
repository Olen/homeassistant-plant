# Bundle the flower card with plant — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** plant serves and registers the flower card itself, tells users with another copy to remove it, and receives each card release as a PR whose notes land in plant's changelog.

**Architecture:** A new `custom_components/plant/frontend.py` serves `www/flower-card.js` and keeps one plant-owned dashboard resource in sync (storage mode) or adds an extra JS module (YAML mode), stepping aside with a repair while another `flower-card.js` resource exists. flower-card's Auto Release opens/updates a PR on the plant repo carrying the build and the release notes between markers; plant's Auto Release appends those notes as a "🌸 Flower card" section.

**Tech Stack:** Python / Home Assistant (`lovelace`, `frontend`, `http`, `issue_registry`), pytest-homeassistant-custom-component; TypeScript / lit / vitest; GitHub Actions + `gh`.

**Spec:** `docs/superpowers/specs/2026-11-03-bundle-flower-card-design.md` (plant repo)

## Global Constraints

- Existing dashboards must work without edits: element `flower-card`, `type: custom:flower-card`, all options, `getConfigForm` editor and card-picker entry unchanged.
- Plant never deletes or edits a resource or file it does not own.
- Never commit a locally built `flower-card.js`. The only builds that enter plant come from flower-card's CI (Task 1 uses the v2026.11.0 release asset).
- `hacs.json` minimum stays `2025.8.0`. Code must run on every HA version plant's CI tests (`Tests (HA 2026.3)`, `Tests (HA latest)`, beta).
- Version bumps are separate PRs. Label every PR (`plant-repo-pr-labels`).
- Each repo: branch from an up-to-date `main`; run black + ruff (plant) / lint + test + build (card) before pushing; return the checkout to `main` afterwards.
- Dispatch on known types and raise on unknowns (Olen's code rules); no `getattr(..., None)` dodges.

## Review Focus

1. **A user with the HACS copy updates plant** → their dashboard keeps rendering the card (the HACS one), a repair appears, and plant has created no resource. (Task 2: `test_other_copy_blocks_own_resource`.)
2. **They then remove the HACS copy without restarting** → plant's resource appears and the repair clears. (Task 2: `test_removing_other_copy_registers_own`.)
3. **A plant update with a new card version** → the existing plant resource's `?v=` is updated in place; never a second plant resource. (Task 2: `test_version_change_updates_in_place`, `test_duplicate_own_resources_collapse_to_one`.)
4. **A stable plant release while a beta card is bundled** → CI fails before the release exists. (Task 3: `test_stable_plant_does_not_ship_beta_card`.)
5. **The card loaded twice in one browser** (cached old resource + new one) → no exception, one card-picker entry. (Task 5: `loads twice without throwing`.)

---

## Repository: `Olen/homeassistant-plant` (`/home/olen/prog/home-assistant-plant`)

Branch: `feat/bundle-flower-card` from `main`.

### Task 1: Serve the bundled card

**Files:**
- Create: `custom_components/plant/www/flower-card.js` (download, do not build): `gh release download v2026.11.0 -R Olen/lovelace-flower-card -p flower-card.js -D custom_components/plant/www/`
- Create: `custom_components/plant/www/flower-card.version` containing `2026.11.0` and a newline
- Create: `custom_components/plant/frontend.py`
- Modify: `custom_components/plant/const.py` (constants below)
- Modify: `custom_components/plant/manifest.json`: add `"http"` to `dependencies`; add `"frontend"` and `"lovelace"` to `after_dependencies`
- Test: `tests/test_frontend.py`

**Interfaces:**
- Produces in `const.py`: `CARD_URL_PATH = "/plant/flower-card.js"`, `CARD_FILENAME = "flower-card.js"`, `CARD_VERSION_FILENAME = "flower-card.version"`, `ISSUE_OTHER_FLOWER_CARD = "other_flower_card"`
- Produces in `frontend.py`:
  - `def read_card_version(www: Path) -> str` — stripped contents of the version file; raises `FileNotFoundError` if missing.
  - `def card_url(version: str) -> str` — `f"{CARD_URL_PATH}?v={version}"`.
  - `def url_path(url: str) -> str` — the URL without its query string.
  - `def find_other_flower_cards(items: Iterable[dict]) -> list[str]` — URLs of resources whose `url_path` ends in `/flower-card.js` and is not `CARD_URL_PATH`, in list order.
  - `def find_own_resources(items: Iterable[dict]) -> list[dict]` — resources whose `url_path` equals `CARD_URL_PATH`.
  - `async def async_serve_card(hass: HomeAssistant) -> str` — registers `CARD_URL_PATH` → the JS file with `StaticPathConfig(..., cache_headers=False)` and returns the card version (file read in the executor).

- [ ] **Step 1: Write the failing tests** in `tests/test_frontend.py`

```python
def test_card_url_carries_version():
    assert card_url("2026.11.0") == "/plant/flower-card.js?v=2026.11.0"

def test_find_other_flower_cards():
    items = [
        {"id": "1", "type": "module", "url": "/hacsfiles/lovelace-flower-card/flower-card.js?hacstag=123"},
        {"id": "2", "type": "module", "url": "/local/flower-card.js"},
        {"id": "3", "type": "module", "url": "/plant/flower-card.js?v=2026.11.0"},
        {"id": "4", "type": "module", "url": "/hacsfiles/mini-graph-card/mini-graph-card-bundle.js"},
        {"id": "5", "type": "module", "url": "/local/my-flower-card.js"},
    ]
    assert find_other_flower_cards(items) == [
        "/hacsfiles/lovelace-flower-card/flower-card.js?hacstag=123",
        "/local/flower-card.js",
    ]
    assert [i["id"] for i in find_own_resources(items)] == ["3"]

def test_read_card_version(tmp_path):
    (tmp_path / "flower-card.version").write_text("2026.11.0\n")
    assert read_card_version(tmp_path) == "2026.11.0"

def test_bundled_files_exist():
    www = Path(__file__).parent.parent / "custom_components/plant/www"
    assert (www / "flower-card.js").stat().st_size > 0
    assert read_card_version(www)
```

Note `/local/my-flower-card.js` must **not** match: compare the last path segment, not a suffix of the string.

- [ ] **Step 2: Run** `source .venv/bin/activate && python -m pytest tests/test_frontend.py -q` — expected FAIL (module missing).
- [ ] **Step 3: Implement** the constants, the bundled files, and the pure functions plus `async_serve_card` in `frontend.py`.
- [ ] **Step 4: Run** the same command — expected PASS. Then `python -m pytest tests/test_manifest_ha_compat.py -q` — expected PASS with the new manifest keys.
- [ ] **Step 5: Commit** `feat: bundle the flower card build`

### Task 2: Register the card, step aside for another copy, repair

**Files:**
- Modify: `custom_components/plant/frontend.py`
- Modify: `custom_components/plant/__init__.py` — at the end of `async_setup`, `await async_setup_card(hass)`
- Modify: `custom_components/plant/strings.json`, `custom_components/plant/translations/en.json`, `custom_components/plant/translations/nb.json` — `issues.other_flower_card.{title,description}`; description uses placeholder `{urls}`
- Test: `tests/test_frontend.py`

**Interfaces:**
- Consumes: Task 1 functions and constants.
- Produces:
  - `async def async_setup_card(hass: HomeAssistant) -> None` — serves the card, then dispatches on `hass.data[LOVELACE_DATA].resources`: `ResourceStorageCollection` → `async_sync_storage_resource` and a listener (`resources.async_add_listener`) that re-runs it on every change; `ResourceYAMLCollection` → `sync_yaml_resource` once; any other type → `raise TypeError`. If `LOVELACE_DATA` is absent, log a warning that dashboards are not loaded and return.
  - `async def async_sync_storage_resource(hass: HomeAssistant, resources: ResourceStorageCollection, version: str) -> None`
  - `def sync_yaml_resource(hass: HomeAssistant, resources: ResourceYAMLCollection, version: str) -> None`
  - `def update_other_card_issue(hass: HomeAssistant, others: list[str]) -> None` — creates `ISSUE_OTHER_FLOWER_CARD` (severity `WARNING`, `is_fixable=False`, placeholder `urls` = the URLs joined by `", "`) when `others` is non-empty, deletes it otherwise.

Storage sync, in order (it must be idempotent, because its own writes trigger the listener):
1. `await resources.async_get_info()` (loads the collection), then `items = resources.async_items()`.
2. `others = find_other_flower_cards(items)`; `update_other_card_issue(hass, others)`.
3. If `others`: delete every own resource and stop.
4. No own resource → `async_create_item({"res_type": "module", "url": card_url(version)})`. One with another URL → `async_update_item(id, {"res_type": "module", "url": card_url(version)})`. Delete own resources beyond the first.

YAML sync: `update_other_card_issue`; if no others, `frontend.add_extra_js_url(hass, card_url(version))`.

- [ ] **Step 1: Write the failing tests** (set up `lovelace` with `async_setup_component`; storage resources via `hass.data[LOVELACE_DATA].resources.async_create_item`; issues via `issue_registry.async_get(hass).async_get_issue(DOMAIN, ISSUE_OTHER_FLOWER_CARD)`)
  - `test_creates_own_resource` — empty resources → exactly one item, `url == "/plant/flower-card.js?v=2026.11.0"`, `type == "module"`, no issue.
  - `test_version_change_updates_in_place` — existing own item `?v=2026.10.1` → same `id`, url now `?v=2026.11.0`, still one own item.
  - `test_duplicate_own_resources_collapse_to_one` — two own items → one remains.
  - `test_other_copy_blocks_own_resource` — HACS item present (and an own item) → own item gone, HACS item untouched, issue exists with `translation_placeholders["urls"]` equal to the HACS URL.
  - `test_removing_other_copy_registers_own` — after the above, `async_delete_item(hacs_id)`, `await hass.async_block_till_done()` → one own item, issue gone.
  - `test_yaml_mode_adds_extra_module` — YAML lovelace with no other card; patch `homeassistant.components.frontend.add_extra_js_url` → called once with `card_url("2026.11.0")`.
  - `test_yaml_mode_other_copy_raises_issue` — YAML lovelace with `/hacsfiles/lovelace-flower-card/flower-card.js` → `add_extra_js_url` not called, issue exists.
  - `test_unknown_resource_collection_raises` — `hass.data[LOVELACE_DATA].resources` replaced with `object()` → `async_setup_card` raises `TypeError`.
  Pin the version in tests by patching `read_card_version` to return `"2026.11.0"`, so a card update does not break them.
- [ ] **Step 2: Run** `python -m pytest tests/test_frontend.py -q` — expected FAIL.
- [ ] **Step 3: Implement** the functions, the `async_setup` call and the translations. Check how this HA version configures YAML resources (`lovelace: mode: yaml` vs. `resource_mode`) in `homeassistant/components/lovelace/__init__.py` of the venv before writing the YAML tests.
- [ ] **Step 4: Run** `python -m pytest tests/ -x -q` — expected PASS, including `test_translations.py`.
- [ ] **Step 5: Run** `python -m black custom_components/plant/ tests/ && ruff check .` — clean.
- [ ] **Step 6: Commit** `feat: register the bundled flower card and flag other copies`

### Task 3: Release plumbing for card PRs

**Files:**
- Create: `scripts/flower_card_notes.py`
- Modify: `.github/release.yml` — add `flower-card` to `changelog.exclude.labels` (its notes get their own section, below)
- Modify: `.github/workflows/release.yml` — after each `softprops/action-gh-release` step, a step that runs the script and `gh release edit v$VERSION --notes-file`
- Test: `tests/test_flower_card_notes.py`, `tests/test_bundled_card_version.py`
- Create the label once: `gh label create flower-card -R Olen/homeassistant-plant --color 7BC67E --description "Bundled flower card update"`

**Interfaces:**
- Produces in `scripts/flower_card_notes.py`:
  - `NOTES_START = "<!-- flower-card-notes:start -->"`, `NOTES_END = "<!-- flower-card-notes:end -->"` (Task 6 writes these exact strings)
  - `def extract_notes(pr_body: str) -> str` — text between the markers, stripped; raises `ValueError` when either marker is missing.
  - `def card_section(pr_bodies: list[str]) -> str` — `""` for no bodies, otherwise `"## 🌸 Flower card\n\n"` followed by each body's notes, in the given order, separated by a blank line.
  - CLI: `python scripts/flower_card_notes.py --since-tag <tag>` prints `card_section` for PRs labelled `flower-card` merged after that tag's commit date (`gh pr list --label flower-card --state merged --search "merged:>=<iso date>" --json body`), oldest first.

The workflow step: `PREV=$(git describe --tags --abbrev=0 HEAD^)`; run the CLI; when output is non-empty, append it to the release body (`gh release view --json body`) and `gh release edit --notes-file`. `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}`.

- [ ] **Step 1: Write the failing tests**

```python
BODY = "Bundles flower card 2026.11.1.\n\n<!-- flower-card-notes:start -->\n* Fix A by @Olen in https://github.com/Olen/lovelace-flower-card/pull/390\n<!-- flower-card-notes:end -->\n"

def test_extract_notes():
    assert extract_notes(BODY) == "* Fix A by @Olen in https://github.com/Olen/lovelace-flower-card/pull/390"

def test_extract_notes_without_markers_raises():
    with pytest.raises(ValueError):
        extract_notes("no markers here")

def test_card_section_empty():
    assert card_section([]) == ""

def test_card_section_keeps_order():
    second = BODY.replace("Fix A", "Fix B").replace("390", "391")
    assert card_section([BODY, second]).startswith("## 🌸 Flower card\n\n* Fix A")
    assert card_section([BODY, second]).index("Fix A") < card_section([BODY, second]).index("Fix B")
```

  and in `tests/test_bundled_card_version.py`:

```python
def test_stable_plant_does_not_ship_beta_card():
    plant = json.loads(MANIFEST.read_text())["version"]
    card = read_card_version(WWW)
    if "beta" not in plant:
        assert "beta" not in card, f"stable plant {plant} bundles beta card {card}"
```

  CI runs this on the version-bump PR, and Auto Release only runs after CI succeeds, so a beta card cannot reach a stable release.
- [ ] **Step 2: Run** `python -m pytest tests/test_flower_card_notes.py tests/test_bundled_card_version.py -q` — expected FAIL (script missing).
- [ ] **Step 3: Implement** the script, the `release.yml` exclusion, the workflow steps; create the label.
- [ ] **Step 4: Run** the tests — expected PASS. Run `actionlint .github/workflows/release.yml` if available (otherwise say so in the PR).
- [ ] **Step 5: Commit** `ci: add bundled flower card notes to plant releases`

### Task 4: Plant README pointer

**Files:** Modify `README.md` — one line near the top-level feature list: the flower card is included with the integration and documented at https://github.com/Olen/lovelace-flower-card.

- [ ] **Step 1:** Edit, then **commit** `docs: point to the bundled flower card`.
- [ ] **Step 2:** Push the branch, open the PR labelled `enhancement`, watch CI to green. Do not merge before the card side (Tasks 5–6) is merged, so the first card PR has a target.

---

## Repository: `Olen/lovelace-flower-card` (`/home/olen/prog/lovelace-flower-card`)

Branch: `feat/bundle-into-plant` from `main`. CI: `npm run lint`, `npm run test`, `npm run build` (discard the built files before committing).

### Task 5: Loading twice never throws

**Files:**
- Modify: `src/flower-card.ts:37-48`
- Test: `tests/register.test.ts`

**Interfaces:**
- Produces: the module defines `flower-card` only when `customElements.get(CARD_NAME)` is undefined, and pushes the `window.customCards` entry only when no entry with `type === CARD_NAME` exists. Replace `@customElement(CARD_NAME)` with an explicit guarded `customElements.define` after the class.

- [ ] **Step 1: Write the failing test** (`loads twice without throwing`): define a placeholder `class extends HTMLElement {}` as `flower-card` and push a `{ type: 'flower-card' }` entry to `window.customCards`, then `await import('../src/flower-card')` → resolves; `window.customCards.filter(c => c.type === 'flower-card')` has length 1; `customElements.get('flower-card')` is still the placeholder.
- [ ] **Step 2: Run** `npx vitest run tests/register.test.ts` — expected FAIL (`define` throws).
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `npm run lint && npm run test && npm run build` — all pass; then `git checkout -- flower-card.js flower-card.js.LICENSE.txt flower-card.js.gz`.
- [ ] **Step 5: Commit** `fix: tolerate the card being loaded twice`

### Task 6: Send each release to plant; README

**Files:**
- Create: `scripts/plant-pr.sh`
- Modify: `.github/workflows/release.yml` — new last step `🌸 Update plant`, run for stable and beta, after the release steps: `scripts/plant-pr.sh "$COMPONENT_VERSION"` with `GH_TOKEN: ${{ secrets.PLANT_REPO_TOKEN }}`
- Modify: `README.md` — rewrite `## 📦 Installation` (incl. `### Manual Installation`); update the table-of-contents entry if its anchor changes

**Interfaces:**
- Consumes: the marker strings from Task 3 (`<!-- flower-card-notes:start -->`, `<!-- flower-card-notes:end -->`).
- `scripts/plant-pr.sh <version>`:
  1. `notes=$(gh release view "v$version" --json body --jq .body)`.
  2. Clone `Olen/homeassistant-plant`; branch `flower-card/update` (one branch for all card updates).
  3. If an open PR exists with head `flower-card/update`: check out that branch, take the existing notes between the markers, and append the new ones; else branch from `main`, notes = the new ones.
  4. Copy `flower-card.js` into `custom_components/plant/www/`, write `$version` to `flower-card.version`, commit `Flower card $version`, push (force when reusing).
  5. Title: `Flower card $version`, plus ` (beta)` when `$version` contains `beta`. Body: one line `Bundles flower card $version.`, a blank line, then the markers around the notes. Label `flower-card`. Create the PR or `gh pr edit` the existing one.
  `--dry-run` prints the title and body instead of pushing.

README installation text must say: the card is installed with the Plant Monitor integration and needs no separate install; users with the card from HACS, or added under Resources by hand, remove that copy when Home Assistant shows the repair; the dashboard keeps working throughout and needs a browser refresh after removal. Keep the rest of the README.

- [ ] **Step 1: Write** the script, the workflow step and the README section.
- [ ] **Step 2: Verify** `bash -n scripts/plant-pr.sh && shellcheck scripts/plant-pr.sh`, and `GH_TOKEN=$(gh auth token) scripts/plant-pr.sh 2026.11.0 --dry-run` prints `Flower card 2026.11.0`, the marker block, and the 2026.11.0 notes. Run `actionlint` if available.
- [ ] **Step 3: Commit** `ci: send each release to the plant integration` and `docs: the card now comes with Plant Monitor`.
- [ ] **Step 4:** Push, open the PR labelled `enhancement`, watch CI to green.

### Handover (Olen)

- Create a fine-grained token with *Contents* and *Pull requests* write access to `Olen/homeassistant-plant`, and store it in flower-card as the secret `PLANT_REPO_TOKEN`. Task 6's workflow step fails until it exists.
- Merge order: card PR (Tasks 5–6) → plant PR (Tasks 1–4) → plant version bump. Card fixes from Task 5 reach plant with the next card release.
