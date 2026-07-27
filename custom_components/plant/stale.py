"""Per-measurement stale/fresh source-sensor tracking for plant.* triggers.

A stale trigger targets the *plant* entity; it resolves that measurement's
external source sensor from the PlantDevice and watches that sensor. "Stale" =
unavailable/unknown, or no update within `for` (default 24h). Imported lazily
by trigger_impl.py — only on HA with the 2026.7 API.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

import voluptuous as vol
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_FOR,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, State, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.condition import Condition, ConditionConfig
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.target import (
    TargetStateChangedData,
    async_track_target_selector_state_change_event,
)
from homeassistant.helpers.trigger import Trigger, TriggerActionRunner, TriggerConfig
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .automation_meta import Measurement
from .const import ATTR_PLANT, DOMAIN

DEFAULT_STALE_FOR = timedelta(hours=24)
_EXCLUDED = {STATE_UNAVAILABLE, STATE_UNKNOWN}


def resolve_external_sensor(
    hass: HomeAssistant, plant_entity_id: str, device_sensor_attr: str
) -> str | None:
    """Return the external source sensor entity_id for a plant measurement."""
    for data in hass.data.get(DOMAIN, {}).values():
        if not isinstance(data, dict) or ATTR_PLANT not in data:
            continue
        plant = data[ATTR_PLANT]
        if plant.entity_id != plant_entity_id:
            continue
        sensor = getattr(plant, device_sensor_attr, None)
        return getattr(sensor, "external_sensor", None) if sensor else None
    return None


def make_stale_trigger(measurement: Measurement, *, fresh: bool) -> type[Trigger]:
    """Build a stale (fresh=False) or fresh (fresh=True) trigger for a measurement."""

    class _PlantStaleTrigger(Trigger):
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
            return cls._schema(config)

        def __init__(self, hass: HomeAssistant, config: TriggerConfig) -> None:
            super().__init__(hass, config)
            self._target = config.target
            self._duration: timedelta = (config.options or {}).get(
                CONF_FOR
            ) or DEFAULT_STALE_FOR

        @callback
        def _sources(self, entities: set[str]) -> set[str]:
            """Map targeted plant entities to their external source sensor."""
            resolved: set[str] = set()
            for entity_id in entities:
                if not entity_id.startswith(f"{DOMAIN}."):
                    continue
                source = resolve_external_sensor(
                    self._hass, entity_id, measurement.device_sensor_attr
                )
                if source:
                    resolved.add(source)
            return resolved

        async def async_attach_runner(
            self, run_action: TriggerActionRunner, did_not_trigger: Any | None = None
        ) -> CALLBACK_TYPE:
            timers: dict[str, CALLBACK_TYPE] = {}
            stale: set[str] = set()

            @callback
            def _fire(entity_id: str, reason: str | None) -> None:
                data = {ATTR_ENTITY_ID: entity_id, "measurement": measurement.key}
                if not fresh:
                    data["reason"] = reason  # "unavailable" | "no_update"
                run_action(data, f"{measurement.key} sensor {entity_id}", None)

            @callback
            def _mark_stale(entity_id: str, reason: str) -> None:
                timer = timers.pop(entity_id, None)
                if timer is not None:
                    timer()
                if entity_id not in stale:
                    stale.add(entity_id)
                    if not fresh:
                        _fire(entity_id, reason)

            @callback
            def _arm(entity_id: str) -> None:
                was_stale = entity_id in stale
                stale.discard(entity_id)
                timer = timers.pop(entity_id, None)
                if timer is not None:
                    timer()
                if fresh and was_stale:
                    _fire(entity_id, None)

                @callback
                def _expired(_now: datetime) -> None:
                    timers.pop(entity_id, None)
                    if entity_id not in stale:
                        stale.add(entity_id)
                        if not fresh:
                            _fire(entity_id, "no_update")

                timers[entity_id] = async_call_later(
                    self._hass, self._duration, _expired
                )

            @callback
            def _consider(entity_id: str, state: State | None) -> None:
                if state is None or state.state in _EXCLUDED:
                    _mark_stale(entity_id, "unavailable")
                else:
                    _arm(entity_id)

            @callback
            def _on_state_change(d: TargetStateChangedData) -> None:
                ev = d.state_change_event
                _consider(ev.data["entity_id"], ev.data["new_state"])

            @callback
            def _on_entities_update(
                added: set[str],
                removed: set[str],
                entity_states: Mapping[str, State | None],
            ) -> None:
                for entity_id in removed:
                    timer = timers.pop(entity_id, None)
                    if timer is not None:
                        timer()
                    stale.discard(entity_id)
                for entity_id in added:
                    _consider(entity_id, entity_states.get(entity_id))

            unsub = await async_track_target_selector_state_change_event(
                self._hass,
                self._target,
                _on_state_change,
                self._sources,
                _on_entities_update,
            )

            @callback
            def _remove() -> None:
                unsub()
                for timer in timers.values():
                    timer()
                timers.clear()
                stale.clear()

            return _remove

    return _PlantStaleTrigger


def make_stale_condition(measurement: Measurement) -> type[Condition]:
    """True when the measurement's external source sensor is currently stale."""

    class _PlantStaleCondition(Condition):
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
            return cls._schema(config)

        def __init__(self, hass: HomeAssistant, config: ConditionConfig) -> None:
            super().__init__(hass, config)
            self._target = config.target
            self._duration: timedelta = (config.options or {}).get(
                CONF_FOR
            ) or DEFAULT_STALE_FOR

        def _async_check(self, **kwargs: Any) -> bool:
            from homeassistant.helpers.target import (
                TargetSelection,
                async_extract_referenced_entity_ids,
            )

            selection = TargetSelection(self._target)
            selected = async_extract_referenced_entity_ids(
                self._hass, selection, expand_group=False
            )
            plant_ids = selected.referenced | selected.indirectly_referenced
            now = dt_util.utcnow()
            for plant_id in plant_ids:
                if not plant_id.startswith(f"{DOMAIN}."):
                    continue
                source = resolve_external_sensor(
                    self._hass, plant_id, measurement.device_sensor_attr
                )
                if not source:
                    continue
                state = self._hass.states.get(source)
                if state is None or state.state in _EXCLUDED:
                    return True
                if now - state.last_updated > self._duration:
                    return True
            return False

    return _PlantStaleCondition
