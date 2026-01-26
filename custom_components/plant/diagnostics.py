"""Diagnostics support for Plant Monitor."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    ATTR_PLANT,
    ATTR_SENSORS,
    ATTR_THRESHOLDS,
    DOMAIN,
)

REDACTED = "**REDACTED**"


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data: dict[str, Any] = {
        "config_entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "domain": entry.domain,
            "title": entry.title,
            "data": _redact_config_data(dict(entry.data)),
            "options": dict(entry.options),
        },
    }

    # Get plant data if available
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        entry_data = hass.data[DOMAIN][entry.entry_id]

        # Plant entity info
        if ATTR_PLANT in entry_data:
            plant = entry_data[ATTR_PLANT]
            data["plant"] = {
                "entity_id": plant.entity_id,
                "name": plant.name,
                "state": plant.state,
                "species": plant.species,
                "display_species": plant.display_species,
                "plant_complete": plant.plant_complete,
                "data_source": plant._data_source,
            }

            # Thresholds
            data["thresholds"] = {}
            threshold_attrs = [
                ("max_moisture", "min_moisture"),
                ("max_temperature", "min_temperature"),
                ("max_conductivity", "min_conductivity"),
                ("max_illuminance", "min_illuminance"),
                ("max_humidity", "min_humidity"),
                ("max_dli", "min_dli"),
            ]
            for max_attr, min_attr in threshold_attrs:
                max_entity = getattr(plant, max_attr, None)
                min_entity = getattr(plant, min_attr, None)
                if max_entity:
                    data["thresholds"][max_attr] = {
                        "entity_id": max_entity.entity_id,
                        "state": (
                            hass.states.get(max_entity.entity_id).state
                            if hass.states.get(max_entity.entity_id)
                            else None
                        ),
                    }
                if min_entity:
                    data["thresholds"][min_attr] = {
                        "entity_id": min_entity.entity_id,
                        "state": (
                            hass.states.get(min_entity.entity_id).state
                            if hass.states.get(min_entity.entity_id)
                            else None
                        ),
                    }

            # Trigger settings
            data["triggers"] = {
                "moisture": plant.moisture_trigger,
                "temperature": plant.temperature_trigger,
                "conductivity": plant.conductivity_trigger,
                "illuminance": plant.illuminance_trigger,
                "humidity": plant.humidity_trigger,
                "dli": plant.dli_trigger,
            }

        # Sensor entities info
        if ATTR_SENSORS in entry_data:
            data["sensors"] = []
            for sensor in entry_data[ATTR_SENSORS]:
                sensor_state = hass.states.get(sensor.entity_id)
                data["sensors"].append(
                    {
                        "entity_id": sensor.entity_id,
                        "name": sensor.name,
                        "state": sensor_state.state if sensor_state else None,
                        "external_sensor": getattr(sensor, "external_sensor", None),
                        "device_class": (
                            str(sensor.device_class) if sensor.device_class else None
                        ),
                    }
                )

        # Threshold entities info
        if ATTR_THRESHOLDS in entry_data:
            data["threshold_entities"] = []
            for threshold in entry_data[ATTR_THRESHOLDS]:
                threshold_state = hass.states.get(threshold.entity_id)
                data["threshold_entities"].append(
                    {
                        "entity_id": threshold.entity_id,
                        "name": threshold.name,
                        "state": threshold_state.state if threshold_state else None,
                        "native_min_value": threshold.native_min_value,
                        "native_max_value": threshold.native_max_value,
                    }
                )

    return data


def _redact_config_data(data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive information from config data."""
    # Currently no sensitive data to redact, but this function
    # provides a place to add redaction if needed in the future
    return data
