# Development Guide

This guide explains how to set up a development environment and run tests and linters for the Home Assistant Plant integration.

## Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) - Fast Python package installer and resolver

### Installing uv

```bash
# On Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv

# Or with Homebrew (macOS)
brew install uv
```

## Setup

Create a virtual environment and install dependencies:

```bash
# Create virtual environment
uv venv

# Install test dependencies from pyproject.toml
uv pip install $(python3 -c "import tomllib; print(' '.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['optional-dependencies']['test']))")

# Remove uv.lock if it exists (it can cause editable install issues)
rm -f uv.lock
```

**Important:**
- Do not install the package itself (`uv pip install .` or `uv pip install ".[test]"`) as this creates editable install artifacts that conflict with pytest-homeassistant-custom-component's discovery mechanism.
- The `uv.lock` file can also cause issues if it contains editable install references. Delete it if tests fail.
- The test framework automatically discovers the `custom_components` directory in the project root.

## Running Tests

Run all tests:

```bash
.venv/bin/pytest tests/ -v
```

Run tests with coverage report:

```bash
.venv/bin/pytest tests/ --cov=custom_components/plant --cov-report=term-missing
```

Run a specific test file:

```bash
.venv/bin/pytest tests/test_init.py -v
```

Run a specific test class or method:

```bash
.venv/bin/pytest tests/test_init.py::TestIntegrationSetup -v
.venv/bin/pytest tests/test_init.py::TestIntegrationSetup::test_setup_entry -v
```

Run tests with short output (useful for CI):

```bash
.venv/bin/pytest tests/ --tb=short
```

**Note:** Use `.venv/bin/pytest` directly instead of `uv run pytest` to avoid `uv run` syncing from `uv.lock` which can reinstall editable packages.

## Linting and Formatting

### Code Formatting with Black

Check formatting without making changes:

```bash
.venv/bin/black . --check --fast --diff
```

Format all code:

```bash
.venv/bin/black .
```

## Project Structure

```
├── custom_components/
│   └── plant/              # Main integration code
│       ├── __init__.py     # Integration setup, PlantDevice
│       ├── config_flow.py  # Configuration flow
│       ├── const.py        # Constants and defaults
│       ├── number.py       # Threshold entities
│       ├── plant_helpers.py# OpenPlantbook helper
│       └── sensor.py       # Sensor entities
├── tests/                  # Test suite
│   ├── conftest.py         # Shared fixtures
│   ├── common.py           # Test utilities
│   ├── fixtures/           # Mock data
│   ├── test_init.py        # Integration setup tests
│   ├── test_config_flow.py # Config flow tests
│   ├── test_sensor.py      # Sensor tests
│   ├── test_number.py      # Threshold tests
│   ├── test_plant_helpers.py # Helper tests
│   ├── test_services.py    # Service tests
│   └── test_websocket.py   # Websocket API tests
├── pyproject.toml          # Project configuration
└── pytest.ini              # Pytest configuration
```

## Continuous Integration

The project uses GitHub Actions for CI. The workflow runs:

1. Code formatting check with Black
2. Test suite with pytest

## Troubleshooting

### Tests fail with import errors

Make sure pytest-homeassistant-custom-component is installed:

```bash
uv pip install pytest-homeassistant-custom-component
```

### Tests fail with FileNotFoundError about editable install

If you see errors mentioning `__editable__` paths, this is caused by editable install artifacts. Fix by:

1. Remove the `uv.lock` file (it may contain editable install references):
```bash
rm -f uv.lock
```

2. Clear the uv cache for this package:
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

### uv command not found

Ensure uv is installed and in your PATH. See the Prerequisites section above.

### Slow test runs

Run tests in parallel (pytest-xdist is already included):

```bash
.venv/bin/pytest tests/ -n auto
```
