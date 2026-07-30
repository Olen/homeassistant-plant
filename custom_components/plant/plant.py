"""Config-entry platform for the plant.<name> device entity.

The ``plant.<name>`` entity lives on the ``plant`` domain, which this
integration owns (it shadows Home Assistant's built-in plant component). Adding
it through a real config-entry platform - rather than the shared component's
default, config-entry-less platform - gives the entity's ``EntityPlatform`` a
``config_entry``. Home Assistant then attaches the entity's device and registers
the entity registry entry to that config entry natively
(``entity_platform.async_add_entities``), so the integration no longer needs to
patch the device/entity registries by hand, and HA Core 2026.8 no longer warns
that a device is attached to an entity without a config entry.

The ``PlantDevice`` instance is created in ``__init__.async_setup_entry`` (it is
needed there for the utility sensor wiring) and stashed under the entry's data;
this platform just hands that same instance to the config-entry-bound
``async_add_entities``. ``__init__.async_setup_entry`` drives this module via
``component.async_setup_entry(entry)`` on the single shared EntityComponent, so
the entity still always has a valid, stable platform (issue #487).
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_PLANT, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the PlantDevice for this config entry to its bound platform."""
    plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]
    async_add_entities([plant])
