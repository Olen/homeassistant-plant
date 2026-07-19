"""Trigger platform for the plant integration (Home Assistant 2026.7+).

PROTOTYPE / strawman for discussion — see the linked feedback issue.

Exposes purpose-specific ``plant.*`` triggers that build on the integration's
existing, species-threshold-aware problem detection. Nothing here is imported
on Home Assistant versions without the trigger platform (< 2026.7), so the file
is inert on older installs and does not raise the integration's minimum version.

Three families:
  * Aggregate plant state — ``plant.became_problem`` / ``plant.became_ok``.
  * Per-measurement (auto-threshold) — e.g. ``plant.moisture_became_low``,
    firing off the plant's own ``<measurement>_status`` attribute. The threshold
    is the plant's configured min/max (with hysteresis); the user never supplies
    a number. Only moisture is wired here as the representative example.
  * Stale source sensor — ``plant.sensor_became_stale``: a plant's source sensor
    is unavailable or has not produced an update within a (default 24h) window.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

import voluptuous as vol
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_FOR,
    STATE_OK,
    STATE_PROBLEM,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, State, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.automation import DomainSpec
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.target import (
    TargetStateChangedData,
    async_track_target_selector_state_change_event,
)
from homeassistant.helpers.trigger import (
    Trigger,
    TriggerActionRunner,
    TriggerConfig,
    make_entity_target_state_trigger,
)
from homeassistant.helpers.typing import ConfigType

from .const import ATTR_MOISTURE, DOMAIN, STATE_HIGH, STATE_LOW

# Some plant sensors update very infrequently; default the staleness window high
# so the trigger flags genuinely dead/silent sensors, not slow ones.
DEFAULT_STALE_FOR = timedelta(hours=24)

_EXCLUDED = {STATE_UNAVAILABLE, STATE_UNKNOWN}


def _status_trigger(measurement: str, to_state: str) -> type[Trigger]:
    """Trigger that fires when a plant's <measurement>_status attribute reaches a state.

    Reuses the core entity-target-state machinery, but tracks the plant's own
    per-measurement status attribute (Low/High/ok) instead of the entity state.
    The plant computes that status from its configured min/max thresholds with
    hysteresis — so this fires on the plant's threshold, with no user input.
    """
    return make_entity_target_state_trigger(
        {DOMAIN: DomainSpec(value_source=f"{measurement}_status")},
        to_state,
    )


class PlantSensorStaleTrigger(Trigger):
    """Fire when a plant's source sensor goes stale.

    "Stale" = the sensor is unavailable/unknown, OR it has not produced any
    update within the configured ``for`` window (default 24h). Target the plant
    device; it expands to the plant's sensors, which are filtered to here.
    """

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

    def __init__(self, hass: HomeAssistant, config: TriggerConfig) -> None:
        """Initialize the stale-sensor trigger."""
        super().__init__(hass, config)
        self._target = config.target
        self._duration: timedelta = (config.options or {}).get(
            CONF_FOR
        ) or DEFAULT_STALE_FOR

    @callback
    def _only_sensors(self, entities: set[str]) -> set[str]:
        """Restrict the expanded target to plant source-sensor entities."""
        return {e for e in entities if e.split(".", 1)[0] == SENSOR_DOMAIN}

    async def async_attach_runner(
        self,
        run_action: TriggerActionRunner,
        did_not_trigger: Any | None = None,
    ) -> CALLBACK_TYPE:
        """Attach the trigger."""
        timers: dict[str, CALLBACK_TYPE] = {}
        stale: set[str] = set()

        @callback
        def _fire(entity_id: str, reason: str) -> None:
            run_action(
                {
                    ATTR_ENTITY_ID: entity_id,
                    "reason": reason,  # "unavailable" | "no_update"
                    "for": self._duration,
                },
                f"{entity_id} stale ({reason})",
                None,
            )

        @callback
        def _mark_stale(entity_id: str, reason: str) -> None:
            timer = timers.pop(entity_id, None)
            if timer is not None:
                timer()
            if entity_id not in stale:
                stale.add(entity_id)
                _fire(entity_id, reason)

        @callback
        def _arm(entity_id: str) -> None:
            """(Re)start the freshness countdown for a healthy sensor."""
            stale.discard(entity_id)
            timer = timers.pop(entity_id, None)
            if timer is not None:
                timer()

            @callback
            def _expired(_now: datetime) -> None:
                timers.pop(entity_id, None)
                if entity_id not in stale:
                    stale.add(entity_id)
                    _fire(entity_id, "no_update")

            timers[entity_id] = async_call_later(self._hass, self._duration, _expired)

        @callback
        def _consider(entity_id: str, state: State | None) -> None:
            if state is None or state.state in _EXCLUDED:
                _mark_stale(entity_id, "unavailable")
            else:
                _arm(entity_id)

        @callback
        def _on_state_change(data: TargetStateChangedData) -> None:
            event = data.state_change_event
            _consider(event.data["entity_id"], event.data["new_state"])

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
            self._only_sensors,
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


TRIGGERS: dict[str, type[Trigger]] = {
    # Aggregate plant health (entity state problem/ok).
    "became_problem": make_entity_target_state_trigger(DOMAIN, STATE_PROBLEM),
    "became_ok": make_entity_target_state_trigger(DOMAIN, STATE_OK),
    # Per-measurement, auto-thresholded (representative example: moisture).
    "moisture_became_low": _status_trigger(ATTR_MOISTURE, STATE_LOW),
    "moisture_became_high": _status_trigger(ATTR_MOISTURE, STATE_HIGH),
    # Source-sensor staleness.
    "sensor_became_stale": PlantSensorStaleTrigger,
}


async def async_get_triggers(hass: HomeAssistant) -> dict[str, type[Trigger]]:
    """Return the triggers provided by the plant integration."""
    return TRIGGERS
