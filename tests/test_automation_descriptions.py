"""Every advertised trigger/condition key must have a UI description block."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from custom_components.plant.trigger import _has_purpose_trigger_api

if not _has_purpose_trigger_api():
    pytest.skip(
        "plant purpose-trigger API not available on this HA",
        allow_module_level=True,
    )

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
