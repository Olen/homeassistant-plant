# Contributing

Thanks for helping improve **Plant Monitor**! This guide covers the pull-request
workflow and — importantly — the **PR labels** that drive our release notes.

## Development setup

Environment setup, running the tests, and linting are covered in
[DEVELOPMENT.md](DEVELOPMENT.md).

## Pull requests

- Branch from `main`, open your PR against `main`.
- CI must pass: formatting (Black), linting (Ruff), and the full test suite on the
  supported Home Assistant versions.
- Keep the change focused; add tests for new behavior and bug fixes.

## PR labels (please add one)

Release notes are generated automatically from **merged-PR labels** (GitHub's
native generator, configured in [`.github/release.yml`](.github/release.yml)).
Add a label so your change lands in the right section of the changelog:

| Label | Release-notes section |
|-------|-----------------------|
| `enhancement` or `feature` | 🚀 Features & Enhancements |
| `bug` or `fix` | 🐛 Bug Fixes |
| `documentation` | 📚 Documentation |
| `dependencies`, `github_actions`, `ci`, `chore` | 🧹 Maintenance & CI |
| _(no label)_ | Other Changes |

Pick the single label that best describes the PR's primary intent. Unlabeled PRs
still appear under **Other Changes**, but a label makes the changelog readable.

### For automated agents (Claude Code, etc.)

When you open a PR, apply the matching label in the same step, e.g.:

```bash
gh pr edit <number> --add-label enhancement   # or bug / documentation / dependencies ...
```

Choose the label from the table above based on the PR's primary intent.

## Releases (maintainers)

Releases are automated. Bump the version in
`custom_components/plant/manifest.json` on `main`; on the next green CI run the
**Auto Release** workflow tags `v<version>` and publishes a GitHub release
(prerelease when the version contains `beta`), with notes categorized from the
merged-PR labels. Version format: `YYYY.M.P` (stable) or `YYYY.M.P-betaN` (beta).
