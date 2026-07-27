"""The trigger/condition platforms must be import-clean and return {} when the
2026.7 purpose-trigger API is unavailable (HA 2025.8-2026.6)."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.plant import condition, trigger

# trigger_impl/condition_impl are only importable when the full settled API is
# present (they import homeassistant.helpers.automation.DomainSpec at module
# level). Import them lazily/conditionally so this file stays import-clean and
# ungated on every HA version, per the platform's own contract.
if trigger._has_purpose_trigger_api():
    from custom_components.plant import trigger_impl
else:
    trigger_impl = None

if condition._has_purpose_condition_api():
    from custom_components.plant import condition_impl
else:
    condition_impl = None


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


@pytest.mark.skipif(
    trigger_impl is None,
    reason="trigger_impl is only importable when the full purpose-trigger API is present",
)
async def test_triggers_degrade_to_empty_on_build_import_error(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A build-time ImportError (e.g. a residual missing symbol) must degrade to
    {} instead of propagating and crashing platform discovery."""

    def _raise() -> dict[str, type]:
        raise ImportError("simulated residual missing symbol")

    monkeypatch.setattr(trigger, "_has_purpose_trigger_api", lambda: True)
    monkeypatch.setattr(trigger_impl, "build_triggers", _raise)
    monkeypatch.setattr(trigger, "_TRIGGERS_CACHE", None)
    assert await trigger.async_get_triggers(hass) == {}


@pytest.mark.skipif(
    condition_impl is None,
    reason="condition_impl is only importable when the full purpose-condition API is present",
)
async def test_conditions_degrade_to_empty_on_build_import_error(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mirror of the trigger degradation test for the condition platform."""

    def _raise() -> dict[str, type]:
        raise ImportError("simulated residual missing symbol")

    monkeypatch.setattr(condition, "_has_purpose_condition_api", lambda: True)
    monkeypatch.setattr(condition_impl, "build_conditions", _raise)
    monkeypatch.setattr(condition, "_CONDITIONS_CACHE", None)
    assert await condition.async_get_conditions(hass) == {}
