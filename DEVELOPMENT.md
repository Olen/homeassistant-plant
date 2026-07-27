# 🛠️ Development Guide

How to set up a development environment and run tests for the Plant Monitor integration.

---

## 📑 Table of Contents

- [🛠️ Development Guide](#️-development-guide)
  - [📋 Prerequisites](#-prerequisites)
  - [⚙️ Setup](#️-setup)
  - [🧪 Running Tests](#-running-tests)
  - [🧹 Linting and Formatting](#-linting-and-formatting)
  - [📁 Project Structure](#-project-structure)
  - [🔄 Continuous Integration](#-continuous-integration)
  - [❓ Troubleshooting](#-troubleshooting)

---

## 📋 Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) — Fast Python package installer and resolver

### Installing uv

```bash
# On Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv

# Or with Homebrew (macOS)
brew install uv
```

---

## ⚙️ Setup

Create a virtual environment and install dependencies:

```bash
# Create virtual environment
uv venv

# Install test dependencies from pyproject.toml
uv pip install $(python3 -c "import tomllib; print(' '.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['optional-dependencies']['test']))")

# Remove uv.lock if it exists (can cause editable install issues)
rm -f uv.lock
```

> [!IMPORTANT]
> - Do **not** install the package itself (`uv pip install .` or `uv pip install ".[test]"`) — this creates editable install artifacts that conflict with pytest-homeassistant-custom-component's discovery mechanism
> - Delete `uv.lock` if tests fail — it may contain editable install references
> - The test framework automatically discovers `custom_components/` in the project root

---

## 🧪 Running Tests

| Command | Description |
|---------|-------------|
| `.venv/bin/pytest tests/ -v` | Run all tests |
| `.venv/bin/pytest tests/ --cov=custom_components/plant --cov-report=term-missing` | Run with coverage report |
| `.venv/bin/pytest tests/test_init.py -v` | Run a specific test file |
| `.venv/bin/pytest tests/test_init.py::TestIntegrationSetup -v` | Run a specific test class |
| `.venv/bin/pytest tests/test_init.py::TestIntegrationSetup::test_setup_entry -v` | Run a specific test method |
| `.venv/bin/pytest tests/ --tb=short` | Short output (useful for CI) |
| `.venv/bin/pytest tests/ -n auto` | Run in parallel (faster) |

> [!NOTE]
> Use `.venv/bin/pytest` directly instead of `uv run pytest` to avoid `uv run` syncing from `uv.lock`, which can reinstall editable packages.

---

## 🧹 Linting and Formatting

### Black (code formatting)

```bash
# Check formatting (no changes)
.venv/bin/black . --check --fast --diff

# Apply formatting
.venv/bin/black .
```

---

## 📁 Project Structure

```
├── custom_components/
│   └── plant/                # Main integration code
│       ├── __init__.py       # Integration setup, PlantDevice
│       ├── config_flow.py    # Configuration flow
│       ├── const.py          # Constants and defaults
│       ├── number.py         # Threshold entities
│       ├── plant_helpers.py  # OpenPlantbook helper
│       └── sensor.py         # Sensor entities
├── tests/                    # Test suite
│   ├── conftest.py           # Shared fixtures
│   ├── common.py             # Test utilities
│   ├── fixtures/             # Mock data
│   ├── test_init.py          # Integration setup tests
│   ├── test_config_flow.py   # Config flow tests
│   ├── test_sensor.py        # Sensor tests
│   ├── test_number.py        # Threshold tests
│   ├── test_plant_helpers.py # Helper tests
│   ├── test_services.py      # Service tests
│   └── test_websocket.py     # Websocket API tests
├── pyproject.toml            # Project configuration
└── pytest.ini                # Pytest configuration
```

---

## 🔄 Continuous Integration

The project uses GitHub Actions for CI. The workflow runs:

1. Code formatting check with Black
2. Linting with Ruff
3. Full test suite with pytest against a minimum and the latest Home Assistant

---

## 🏷️ Pull Requests & Releases

The contribution workflow, the **PR label convention** (which drives categorized
release notes), and the automated release process live in
[CONTRIBUTING.md](CONTRIBUTING.md).

---

## ❓ Troubleshooting

<details>
<summary><strong>Tests fail with import errors</strong></summary>

Make sure `pytest-homeassistant-custom-component` is installed:

```bash
uv pip install pytest-homeassistant-custom-component
```
</details>

<details>
<summary><strong>Tests fail with FileNotFoundError about editable install</strong></summary>

This is caused by editable install artifacts. Fix by:

1. Remove `uv.lock`:
   ```bash
   rm -f uv.lock
   ```

2. Clear the uv cache:
   ```bash
   rm -rf ~/.cache/uv/sdists-v9/editable
   find ~/.cache/uv -name "*home_assistant_plant*" -exec rm -rf {} + 2>/dev/null
   ```

3. Recreate the virtual environment:
   ```bash
   rm -rf .venv
   uv venv
   uv pip install $(python3 -c "import tomllib; print(' '.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['optional-dependencies']['test']))")
   ```
</details>

<details>
<summary><strong>uv command not found</strong></summary>

Ensure uv is installed and in your PATH. See [Prerequisites](#-prerequisites).
</details>

<details>
<summary><strong>Slow test runs</strong></summary>

Run tests in parallel:

```bash
.venv/bin/pytest tests/ -n auto
```
</details>
