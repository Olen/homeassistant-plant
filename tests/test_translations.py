"""Verify every config/options flow form field is translated.

Mirrors Home Assistant core's flow-translation pylint checks
(config-flow-field-not-translated / options-flow-field-not-translated): every
voluptuous field in a flow step must have a ``<flow>.step.<step>.data.<field>``
entry. We additionally require the same entry in ``translations/en.json`` (what
HA actually reads at runtime), not just ``strings.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

from homeassistant import config_entries
from homeassistant.const import ATTR_NAME
from homeassistant.core import HomeAssistant

from custom_components.plant.const import ATTR_SEARCH_FOR, ATTR_SPECIES, DOMAIN

COMPONENT = Path(__file__).resolve().parent.parent / "custom_components" / "plant"


def _load(name: str) -> dict:
    return json.loads((COMPONENT / name).read_text(encoding="utf-8"))


def _field_names(data_schema) -> set[str]:
    """Return the field keys of a voluptuous schema (markers or plain keys)."""
    return {str(getattr(marker, "schema", marker)) for marker in data_schema.schema}


def _translated_keys(translations: dict, flow: str, step: str) -> set[str]:
    node = translations.get(flow, {}).get("step", {}).get(step, {})
    keys = set(node.get("data", {}).keys())
    for section in node.get("sections", {}).values():
        keys |= set(section.get("data", {}).keys())
    return keys


def _assert_step_translated(flow: str, step: str, data_schema) -> None:
    fields = _field_names(data_schema)
    for filename, data in (
        ("strings.json", _load("strings.json")),
        ("translations/en.json", _load("translations/en.json")),
    ):
        missing = fields - _translated_keys(data, flow, step)
        assert not missing, (
            f"{filename}: {flow}.step.{step} is missing data labels for "
            f"{sorted(missing)}"
        )


async def test_config_flow_fields_translated(
    hass: HomeAssistant,
    mock_openplantbook_services,
) -> None:
    """Every config flow step's form fields are translated."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    _assert_step_translated("config", "user", result["data_schema"])

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {ATTR_NAME: "My Monstera", ATTR_SPECIES: "monstera"}
    )
    assert result["step_id"] == "select_species"
    _assert_step_translated("config", "select_species", result["data_schema"])

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {ATTR_SEARCH_FOR: "monstera", ATTR_SPECIES: "monstera deliciosa"},
    )
    assert result["step_id"] == "sensors"
    _assert_step_translated("config", "sensors", result["data_schema"])

    # No sensors selected -> limits step shows every threshold field.
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "limits"
    _assert_step_translated("config", "limits", result["data_schema"])


async def test_options_flow_fields_translated(
    hass: HomeAssistant,
    mock_openplantbook_services,
    init_integration,
) -> None:
    """Every options flow step's form fields are translated."""
    for step in ("plant_properties", "replace_sensor"):
        result = await hass.config_entries.options.async_init(init_integration.entry_id)
        assert result["step_id"] == "init"  # menu, no data fields
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": step}
        )
        assert result["step_id"] == step
        _assert_step_translated("options", step, result["data_schema"])
