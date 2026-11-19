"""plant.watered / fertilized / repotted triggers, built on the care event entity.

The care event entity holds the state; these triggers only let an automation
target plants (or their areas and labels) instead of event entities.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, State, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.target import (
    TargetStateChangedData,
    async_track_target_selector_state_change_event,
)
from homeassistant.helpers.trigger import Trigger, TriggerActionRunner, TriggerConfig
from homeassistant.helpers.typing import ConfigType

from .const import ATTR_PLANT, DOMAIN
from .event import ATTR_CARE_EVENT

_CARE_SCHEMA = vol.Schema(
    {
        vol.Required("target"): cv.TARGET_FIELDS,
        vol.Optional("options", default=dict): vol.Schema({}, extra=vol.ALLOW_EXTRA),
    },
    extra=vol.ALLOW_EXTRA,
)


def resolve_care_event(hass: HomeAssistant, plant_entity_id: str) -> str | None:
    """Return the care event entity_id of a plant."""
    for data in hass.data.get(DOMAIN, {}).values():
        if not isinstance(data, dict) or ATTR_PLANT not in data:
            continue
        if data[ATTR_PLANT].entity_id != plant_entity_id:
            continue
        care_event = data.get(ATTR_CARE_EVENT)
        return care_event.entity_id if care_event is not None else None
    return None


def is_new_care_event(old: State | None, new: State | None, event_type: str) -> bool:
    """True when the care entity just reported `event_type`.

    A restore at startup (no old state) or coming back from unavailable is not
    a new event.
    """
    if old is None or new is None:
        return False
    if old.state == STATE_UNAVAILABLE or new.state == old.state:
        return False
    return new.attributes.get("event_type") == event_type


def make_care_trigger(event_type: str) -> type[Trigger]:
    """Build a trigger that fires when a targeted plant reports `event_type`."""

    class _PlantCareTrigger(Trigger):
        @classmethod
        async def async_validate_config(
            cls, hass: HomeAssistant, config: ConfigType
        ) -> ConfigType:
            return _CARE_SCHEMA(config)

        def __init__(self, hass: HomeAssistant, config: TriggerConfig) -> None:
            super().__init__(hass, config)
            self._target = config.target
            self._plant_by_event: dict[str, str] = {}

        @callback
        def _care_events(self, entities: set[str]) -> set[str]:
            """Map targeted plant entities to their care event entities."""
            plant_by_event = {}
            for entity_id in entities:
                if not entity_id.startswith(f"{DOMAIN}."):
                    continue
                care_event = resolve_care_event(self._hass, entity_id)
                if care_event is not None:
                    plant_by_event[care_event] = entity_id
            self._plant_by_event = plant_by_event
            return set(plant_by_event)

        async def async_attach_runner(
            self, run_action: TriggerActionRunner, did_not_trigger: Any | None = None
        ) -> CALLBACK_TYPE:
            @callback
            def _on_state_change(data: TargetStateChangedData) -> None:
                event = data.state_change_event
                if not is_new_care_event(
                    event.data["old_state"], event.data["new_state"], event_type
                ):
                    return
                plant = self._plant_by_event.get(event.data["entity_id"])
                run_action(
                    {ATTR_ENTITY_ID: plant, "event_type": event_type},
                    f"{plant} {event_type}",
                    None,
                )

            return await async_track_target_selector_state_change_event(
                self._hass, self._target, _on_state_change, self._care_events
            )

    return _PlantCareTrigger
