"""Every advertised trigger/condition key must have a UI description block."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from homeassistant.const import __version__ as HA_VERSION

_p = HA_VERSION.split(".")
if (int(_p[0]), int(_p[1])) < (2026, 7):
    pytest.skip("requires HA 2026.7+", allow_module_level=True)

from homeassistant.core import HomeAssistant

from custom_components.plant.condition import async_get_conditions
from custom_components.plant.trigger import async_get_triggers

_ROOT = Path("custom_components/plant")


def _described_keys(filename: str) -> set[str]:
    doc = yaml.safe_load((_ROOT / filename).read_text())
    return {k for k in doc if not k.startswith(".")}


async def test_every_trigger_has_a_description(hass: HomeAssistant) -> None:
    assert set(await async_get_triggers(hass)) <= _described_keys("triggers.yaml")


async def test_every_condition_has_a_description(hass: HomeAssistant) -> None:
    assert set(await async_get_conditions(hass)) <= _described_keys("conditions.yaml")
