"""Shared metadata for the plant.* trigger/condition surface.

Pure data — safe to import on any Home Assistant version. The 2026.7-only
trigger/condition helper APIs are imported lazily inside trigger.py /
condition.py, never here.
"""

from __future__ import annotations

from typing import NamedTuple


class Measurement(NamedTuple):
    """One plant measurement and how the automation surface reaches it."""

    key: str
    """Name fragment and status-attribute prefix, e.g. "moisture"."""
    status_attr: str
    """Plant entity attribute holding Low/High/ok, e.g. "moisture_status"."""
    device_sensor_attr: str | None
    """PlantDevice attribute holding the external source sensor entity, or
    None for derived measurements (dli, vpd) that have no source of their own."""


# The 9 measurements that expose a <key>_status attribute (Low / High / ok).
STATUS_MEASUREMENTS: tuple[Measurement, ...] = (
    Measurement("moisture", "moisture_status", "sensor_moisture"),
    Measurement("conductivity", "conductivity_status", "sensor_conductivity"),
    Measurement("temperature", "temperature_status", "sensor_temperature"),
    Measurement(
        "soil_temperature", "soil_temperature_status", "sensor_soil_temperature"
    ),
    Measurement("humidity", "humidity_status", "sensor_humidity"),
    Measurement("illuminance", "illuminance_status", "sensor_illuminance"),
    Measurement("co2", "co2_status", "sensor_co2"),
    Measurement("dli", "dli_status", None),
    Measurement("vpd", "vpd_status", None),
)

# The 7 externally-sourced measurements (can go stale independently).
EXTERNAL_MEASUREMENTS: tuple[Measurement, ...] = tuple(
    m for m in STATUS_MEASUREMENTS if m.device_sensor_attr is not None
)
