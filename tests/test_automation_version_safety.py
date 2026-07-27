"""The trigger/condition platforms must be import-clean and return {} when the
2026.7 purpose-trigger API is unavailable (HA 2025.8-2026.6)."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.plant import condition, trigger


async def test_triggers_empty_when_api_absent(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(trigger, "_has_purpose_trigger_api", lambda: False)
    assert await trigger.async_get_triggers(hass) == {}


async def test_conditions_empty_when_api_absent(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(condition, "_has_purpose_condition_api", lambda: False)
    assert await condition.async_get_conditions(hass) == {}
