# Bundle the flower card with the plant integration

## Intent

The flower card (`Olen/lovelace-flower-card`) only works with this integration: it needs the
`plant/get_info` websocket command that only `plant` registers. Today users install the two
separately, from two HACS repositories. After this change, installing or updating `plant` installs
or updates the card and registers it as a dashboard resource. Nobody installs the card on its own.

A HACS maintainer asked for this in the review of hacs/default#13025. Olen agrees it is the better
setup in its own right. It does **not** get `plant` into the HACS default catalog: `plant` replaces
HA's built-in `plant` domain, and the catalog rejects core domain conflicts.

## Goals

- `plant` serves the card's JavaScript from its own folder and registers it as a dashboard
  resource on setup.
- Users who have the card installed from HACS are told, by a repair, to remove that copy.
- Each card release reaches users through a plant PR and the next plant release.
- Plant's release notes list what changed in the card, in their own section.

## Non-goals

- Moving the card's source, issues or README into this repository. `lovelace-flower-card` stays
  the card's development home: source, history, issues, README, tests, CI.
- Releasing card fixes independently of plant. Card fixes wait for the next plant release.
- Brand images for `plant`. Skipped for now.

## Anti-goals (a failure even if everything else works)

- **A dashboard that needs editing.** The bundled card must work on an existing dashboard without
  any edits. The element name stays `flower-card` (`type: custom:flower-card`), every config option
  stays the same, the visual editor (`getConfigForm`) and the card-picker entry stay the same.
- **A broken dashboard right after updating plant**, for example because two copies of the card
  race to register the same element.
- **Plant deleting files or resources HACS owns.**

## Constraints

- The card is built only by flower-card's CI. Never commit a locally built `flower-card.js`.
- Plant releases come from the Auto Release workflow (a `manifest.json` version change merged to
  `main`), with GitHub-generated release notes bucketed by PR label (`.github/release.yml`).
  Version bumps are their own PR.
- Dashboard resources can be managed in storage (the UI) or in YAML. Both must work.
- Minimum HA version is whatever `hacs.json` says at the time. Do not raise it for this.

## Design

### 1. Serving and registering the card (plant)

- The built card lives at `custom_components/plant/www/flower-card.js`, with the card version it was
  built from recorded next to it (for example `custom_components/plant/www/flower-card.version`).
- In `async_setup` (once per HA start, not per config entry), plant serves `www/` at its own URL
  path (for example `/plant/flower-card.js`) with `hass.http.async_register_static_paths`.
- The resource URL carries the card version as a cache buster: `/plant/flower-card.js?v=<version>`.
- **Storage-mode resources:** if no plant resource exists, create one (`res_type: module`). If one
  exists with a different `?v=`, update it in place. Never create a second one.
- **YAML-mode resources:** the list cannot be written, so load the card with
  `frontend.add_extra_js_url` instead.
- Lovelace may load after plant. Registration must wait for it rather than fail.
  Precedent: `ha_washdata/frontend.py` (installed in ha-config) does all of the above.

### 2. Coexisting with a HACS copy (plant)

- **Detecting it:** any dashboard resource, other than plant's own, whose path ends in
  `flower-card.js`. That covers `/hacsfiles/lovelace-flower-card/flower-card.js` and hand-installed
  copies under `/local/`. Ignore the query string.
- **While one is present:** plant does **not** register its own copy, and it removes its own
  resource if one exists. The dashboard keeps working on the other copy.
- **The repair:** an issue in Settings → Repairs saying the card now comes with plant and asking the
  user to remove the other copy (from HACS, or from Resources for a hand-installed one). It only
  informs. Plant never deletes the other copy's files or resource.
- **When it goes away:** plant watches the resource collection (the way Spook's
  `dashboard_resources.async_watch_resources` does), registers its own copy and clears the repair,
  without an HA restart. The user needs a browser refresh.
- YAML-mode resources cannot change at runtime, so there detection runs at setup only.

### 3. A second copy must never throw (flower-card)

`@customElement(CARD_NAME)` calls `customElements.define`, which throws if the name is already
defined. Replace it with a define that does nothing when the name is taken. `flower-card` is the
only element the card defines; the editor is HA's own form from `getConfigForm()`. Push the `window.customCards` entry only once. This is insurance for anything
detection misses, such as a browser that has the old file cached.

### 4. Delivering a card release to plant (flower-card CI)

flower-card's Auto Release already builds `flower-card.js`. After tagging, it additionally:

- opens a PR on `Olen/homeassistant-plant` that updates `custom_components/plant/www/flower-card.js`
  and the recorded card version;
- titles it `Flower card <version>` and gives it the label `flower-card`;
- puts the card release's notes (the generated notes of the flower-card release just published) in
  the PR body, between markers the plant release workflow can find.

**Card betas (Olen's decision):** beta card releases open plant PRs too, so testers get them
through plant betas. The PR title says so (`Flower card <version> (beta)`). Merging one is fine
while plant itself is in beta. Plant's release workflow **refuses to publish a stable plant
version whose recorded card version contains `-beta`**, so a test build never reaches everyone.
A plant beta may carry either.

**A card release while the previous card PR is still open (Claude's call):** the workflow reuses
that PR. It force-pushes the new build to the same branch, retitles it to the new version, and
appends the new release's notes to the ones already between the markers. That way no card change
drops out of the plant changelog, and two PRs never fight over the same file.

This needs a token with write access to the plant repo, stored as a secret in flower-card. Olen
creates it (fine-grained PAT or GitHub App). The PR is merged by hand like any other plant PR.

### 5. The plant changelog

- `.github/release.yml` gets a `🌸 Flower card` category for the `flower-card` label, so the PR
  shows up in its own section.
- That alone gives one line per card release. To list each card change, plant's release workflow
  takes the card notes from the bodies of the `flower-card` PRs merged since the previous plant tag
  and adds them under that section of the plant release.

### 6. The flower-card repository afterwards

- **Its README's installation section is rewritten (Olen's decision):** the card comes with the
  plant integration, there is nothing to install separately, and existing users move over by
  removing the HACS copy when the repair asks (or from Resources, for a hand-installed copy). The
  rest of the README (configuration, options, screenshots) stays as it is.
- **`hacs.json` and the HACS validation workflow stay (Olen's decision)**, so HACS problems show up
  in the card repo before a build reaches plant. The repo is no longer advertised as a HACS install,
  but it keeps working as a HACS custom repository. Anyone who still installs it that way gets the
  repair from section 2.
- Plant's README gets one line pointing to the flower-card repository for card documentation.

## Left to the builder

- Exact file and URL names (`www/`, `/plant/flower-card.js`, how the version is recorded).
- How plant reads the card version (a file next to the JS, or a constant updated by the PR).
- The marker format in the PR body, and how the plant release workflow merges the notes.
- The repair's wording and translation keys.
- Whether `lovelace`/`frontend`/`http` go in `dependencies` or `after_dependencies`.
- Tests: detection of the other copy, and create/update/no-duplicate of plant's own resource.
