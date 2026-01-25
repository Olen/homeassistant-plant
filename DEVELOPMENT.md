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

# Install test dependencies (the custom_components directory is discovered automatically)
uv pip install pytest pytest-asyncio pytest-cov pytest-timeout pytest-homeassistant-custom-component syrupy black
```

The `pytest-homeassistant-custom-component` package automatically discovers the `custom_components` directory in the project root.

## Running Tests

Run all tests:

```bash
uv run pytest tests/ -v
```

Run tests with coverage report:

```bash
uv run pytest tests/ --cov=custom_components/plant --cov-report=term-missing
```

Run a specific test file:

```bash
uv run pytest tests/test_init.py -v
```

Run a specific test class or method:

```bash
uv run pytest tests/test_init.py::TestIntegrationSetup -v
uv run pytest tests/test_init.py::TestIntegrationSetup::test_setup_entry -v
```

Run tests with short output (useful for CI):

```bash
uv run pytest tests/ --tb=short
```

## Linting and Formatting

### Code Formatting with Black

Check formatting without making changes:

```bash
uv run black . --check --fast --diff
```

Format all code:

```bash
uv run black .
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

If you see errors mentioning `__editable__` paths, remove any leftover editable install artifacts:

```bash
rm -f .venv/lib/python*/site-packages/__editable__*
rm -rf .venv/lib/python*/site-packages/__pycache__/__editable__*
```

Or recreate the virtual environment:

```bash
rm -rf .venv
uv venv
uv pip install pytest pytest-asyncio pytest-cov pytest-timeout pytest-homeassistant-custom-component syrupy black
```

### uv command not found

Ensure uv is installed and in your PATH. See the Prerequisites section above.

### Slow test runs

Run tests in parallel (if you have pytest-xdist installed):

```bash
uv pip install pytest-xdist
uv run pytest tests/ -n auto
```
