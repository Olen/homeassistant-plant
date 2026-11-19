"""Care event entity: reports watering, fertilizing and repotting."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_PLANT, CARE_EVENT_TYPES, DOMAIN

ATTR_CARE_EVENT = "care_event"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the care event entity for this plant."""
    plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]
    care_event = PlantCareEvent(entry, plant)
    hass.data[DOMAIN][entry.entry_id][ATTR_CARE_EVENT] = care_event
    async_add_entities([care_event])


class PlantCareEvent(EventEntity):
    """Fires when the plant was watered, fertilized or repotted."""

    _attr_has_entity_name = True
    _attr_translation_key = "care"

    def __init__(self, entry: ConfigEntry, plant: Entity) -> None:
        self._plant = plant
        self._attr_event_types = list(CARE_EVENT_TYPES.values())
        self._attr_unique_id = f"{entry.entry_id}-care"

    @property
    def device_info(self) -> DeviceInfo:
        """Device info for devices"""
        return DeviceInfo(
            identifiers={(DOMAIN, self._plant.unique_id)},
            name=self._plant.name,
        )

    def report(self, event_type: str) -> None:
        """Record one care event."""
        if self.hass is None:
            # The entity is disabled
            return
        self._trigger_event(event_type)
        self.async_write_ha_state()
