"""Text entity for plant notes."""
from __future__ import annotations

import logging

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up plant text entities from a config entry."""
    plant = hass.data[DOMAIN][entry.entry_id]["plant"]
    async_add_entities([PlantNotesTextEntity(plant)])


class PlantNotesTextEntity(TextEntity):
    """Representation of a text entity for plant notes."""

    _attr_icon = "mdi:note-text-outline"
    _attr_should_poll = False
    # This translation key tells HA to look up translations under "component.plant.plant_notes"
    _attr_translation_key = "plant_notes"

    def __init__(self, plant) -> None:
        """Initialize the text entity."""
        self.plant = plant
        # Form a unique ID using the plant device’s unique_id.
        self._attr_unique_id = f"{plant.unique_id}-notes"
        # Initialize with the current notes from the plant device (or an empty string).
        self._attr_native_value = plant.notes or ""

    @property
    def name(self) -> str:
        """Return the display name of the plant notes entity.

        This combines the plant’s name with the fixed label "Notes".
        """
        return f"{self.plant.name} Notes"

    async def async_set_value(self, value: str) -> None:
        """Update the plant notes value when changed in the frontend."""
        _LOGGER.debug("Updating notes for %s to: %s", self.entity_id, value)
        self._attr_native_value = value
        # Update the underlying plant device’s notes attribute.
        self.plant.notes = value
        self.async_write_ha_state()
