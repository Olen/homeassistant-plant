"""Care event entities: one per care type (watered, fertilized, repotted, pruned)."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_CARE_EVENTS, ATTR_PLANT, CARE_EVENT_TYPES, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add one care event entity per care type for this plant."""
    plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]
    care_events = {
        care: PlantCareEvent(entry, plant, care) for care in CARE_EVENT_TYPES
    }
    hass.data[DOMAIN][entry.entry_id][ATTR_CARE_EVENTS] = care_events
    plant.care_events = care_events
    async_add_entities(list(care_events.values()))


class PlantCareEvent(EventEntity):
    """Fires when one kind of care was given to the plant."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, plant: Entity, care: str) -> None:
        self._plant = plant
        event_type = CARE_EVENT_TYPES[care]
        self._event_type = event_type
        self._attr_event_types = [event_type]
        self._attr_translation_key = event_type
        self._attr_unique_id = f"{entry.entry_id}-{event_type}"

    @property
    def device_info(self) -> DeviceInfo:
        """Device info for devices"""
        return DeviceInfo(
            identifiers={(DOMAIN, self._plant.unique_id)},
            name=self._plant.name,
        )

    @callback
    def report(self) -> None:
        """Record one care event."""
        if self.hass is None:
            # The entity is disabled
            return
        self._trigger_event(self._event_type)
        self.async_write_ha_state()
