"""Condition platform for the plant integration (Home Assistant 2026.7+).

PROTOTYPE / strawman for discussion — see the linked feedback issue.

Mirrors the trigger families as conditions so automations can be *gated* on
plant health, not only fired by it:
  * ``plant.is_problem`` — the plant is currently in a problem state.
  * ``plant.moisture_is_low`` — per-measurement, auto-thresholded (example).
  * ``plant.sensor_is_stale`` — a plant source sensor is unavailable or has not
    updated within the window (default 24h).

Inert on Home Assistant < 2026.7 (the condition platform is never imported).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import voluptuous as vol
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import (
    CONF_FOR,
    STATE_PROBLEM,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.automation import DomainSpec
from homeassistant.helpers.condition import (
    Condition,
    ConditionConfig,
    make_entity_state_condition,
)
from homeassistant.helpers.target import (
    TargetSelection,
    async_extract_referenced_entity_ids,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import ATTR_MOISTURE, DOMAIN, STATE_LOW
from .trigger import DEFAULT_STALE_FOR

_EXCLUDED = {STATE_UNAVAILABLE, STATE_UNKNOWN}


def _status_condition(measurement: str, state: str) -> type[Condition]:
    """Condition on a plant's <measurement>_status attribute (auto-thresholded)."""
    return make_entity_state_condition(
        {DOMAIN: DomainSpec(value_source=f"{measurement}_status")},
        state,
    )


class PlantSensorStaleCondition(Condition):
    """True when a targeted plant source sensor is currently stale."""

    _schema = vol.Schema(
        {
            vol.Required("target"): cv.TARGET_FIELDS,
            vol.Optional("options", default=dict): vol.Schema(
                {vol.Optional(CONF_FOR): cv.positive_time_period},
                extra=vol.ALLOW_EXTRA,
            ),
        },
        extra=vol.ALLOW_EXTRA,
    )

    @classmethod
    async def async_validate_config(
        cls, hass: HomeAssistant, config: ConfigType
    ) -> ConfigType:
        """Validate config."""
        return cls._schema(config)

    def __init__(self, hass: HomeAssistant, config: ConditionConfig) -> None:
        """Initialize the condition."""
        super().__init__(hass, config)
        self._target_selection = TargetSelection(config.target)
        self._duration: timedelta = (config.options or {}).get(
            CONF_FOR
        ) or DEFAULT_STALE_FOR

    def _async_check(self, **kwargs: Any) -> bool:
        """Return True if any targeted plant sensor is unavailable or silent."""
        selected = async_extract_referenced_entity_ids(
            self._hass, self._target_selection, expand_group=False
        )
        entity_ids = selected.referenced | selected.indirectly_referenced
        now = dt_util.utcnow()
        for entity_id in entity_ids:
            if entity_id.split(".", 1)[0] != SENSOR_DOMAIN:
                continue
            state = self._hass.states.get(entity_id)
            if state is None or state.state in _EXCLUDED:
                return True
            if now - state.last_updated > self._duration:
                return True
        return False


CONDITIONS: dict[str, type[Condition]] = {
    "is_problem": make_entity_state_condition(DOMAIN, STATE_PROBLEM),
    "moisture_is_low": _status_condition(ATTR_MOISTURE, STATE_LOW),
    "sensor_is_stale": PlantSensorStaleCondition,
}


async def async_get_conditions(hass: HomeAssistant) -> dict[str, type[Condition]]:
    """Return the conditions provided by the plant integration."""
    return CONDITIONS
