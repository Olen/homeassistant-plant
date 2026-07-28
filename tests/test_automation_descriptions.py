"""Every advertised trigger/condition key must have a UI description block."""

from __future__ import annotations

import json
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


_TRANSLATION_FILES = ("strings.json", "translations/en.json")


def _named_keys(translation_file: str, section: str) -> set[str]:
    """Keys under a strings.json section that carry a non-empty display name."""
    data = json.loads((_ROOT / translation_file).read_text())
    return {
        key
        for key, block in data.get(section, {}).items()
        if isinstance(block, dict) and block.get("name")
    }


@pytest.mark.parametrize("translation_file", _TRANSLATION_FILES)
async def test_every_trigger_has_a_translated_name(
    hass: HomeAssistant, translation_file: str
) -> None:
    """Every advertised trigger needs a translated name, or the automation UI
    shows "Unknown Trigger". Guards both strings.json and its en.json mirror."""
    assert set(await async_get_triggers(hass)) <= _named_keys(
        translation_file, "triggers"
    )


@pytest.mark.parametrize("translation_file", _TRANSLATION_FILES)
async def test_every_condition_has_a_translated_name(
    hass: HomeAssistant, translation_file: str
) -> None:
    """Every advertised condition needs a translated name, or the automation UI
    shows "Unknown condition". Guards both strings.json and its en.json mirror."""
    assert set(await async_get_conditions(hass)) <= _named_keys(
        translation_file, "conditions"
    )
