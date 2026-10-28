"""Plant entities take entity_id changes in place (#539)."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity as entity_helper
from homeassistant.helpers.entity import Entity
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.plant as plant_package
from custom_components.plant.const import ATTR_PLANT, DOMAIN
from custom_components.plant.number import PlantMinMax

from .common import set_sensor_state

# HA 2026.11+: whether an entity_id change still removes and re-adds the entity.
_requires_readd = getattr(entity_helper, "_entity_class_requires_readd", None)


def _plant_entity_classes() -> set[type[Entity]]:
    modules = [plant_package]
    for info in pkgutil.iter_modules(
        plant_package.__path__, plant_package.__name__ + "."
    ):
        try:
            modules.append(importlib.import_module(info.name))
        except ImportError:
            # trigger_impl / condition_impl need HA 2026.7+ and hold no entities
            continue
    return {
        cls
        for module in modules
        for _, cls in inspect.getmembers(module, inspect.isclass)
        if issubclass(cls, Entity) and cls.__module__.startswith(plant_package.__name__)
    }


@pytest.mark.skipif(_requires_readd is None, reason="HA < 2026.11")
def test_no_plant_entity_is_removed_and_re_added_on_rename() -> None:
    """HA's own check: every plant entity class has opted in."""
    classes = _plant_entity_classes()
    assert classes
    assert sorted(cls.__name__ for cls in classes if _requires_readd(cls)) == []


async def test_entity_id_changed_runs_on_every_plant_entity(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Plant's hooks work on HA versions whose Entity does not define one."""
    plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
    entities = [plant] + [
        entity
        for entity in vars(plant).values()
        if isinstance(entity, Entity) and entity is not plant
    ]
    called = set()
    for entity in entities:
        if hasattr(entity, "async_entity_id_changed"):
            entity.async_entity_id_changed(f"{entity.entity_id}_old")
            called.add(type(entity).__mro__[0])
    implementers = {
        cls for cls in _plant_entity_classes() if "async_entity_id_changed" in vars(cls)
    }
    # Every class that defines the hook has an instance (or subclass) here
    assert all(any(issubclass(c, impl) for c in called) for impl in implementers)


async def test_reloaded_threshold_leaves_no_listeners_behind(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A reload (every rename reloads the plant) must not leave the old
    threshold reacting to its entity's state."""
    calls: list[object] = []
    on_state = PlantMinMax._state_changed_event

    @callback
    def spy(self, event):
        calls.append(self)
        on_state(self, event)

    with patch.object(PlantMinMax, "_state_changed_event", spy):
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        old = hass.data[DOMAIN][mock_config_entry.entry_id][ATTR_PLANT].max_moisture
        await hass.config_entries.async_reload(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        new = hass.data[DOMAIN][mock_config_entry.entry_id][ATTR_PLANT].max_moisture
        calls.clear()
        hass.states.async_set(new.entity_id, "77", {"unit_of_measurement": "%"})
        await hass.async_block_till_done()

    assert old not in calls
    assert new in calls


async def test_entity_id_changed_moves_threshold_listener(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """After the hook, edits arrive under the new entity_id only."""
    threshold = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT].max_moisture
    old_id = threshold.entity_id
    new_id = f"{old_id}_renamed"
    attributes = dict(hass.states.get(old_id).attributes)
    hass.states.async_set(new_id, hass.states.get(old_id).state, attributes)

    threshold.entity_id = new_id
    threshold.async_entity_id_changed(old_id)
    hass.states.async_set(new_id, "77", attributes)
    await hass.async_block_till_done()
    hass.states.async_set(old_id, "11", attributes)
    await hass.async_block_till_done()

    assert threshold.native_value == 77


async def test_entity_id_changed_keeps_ppfd_on_old_state_removal(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """The old id's state removal, if it arrives after the hook, is ignored."""
    plant = hass.data[DOMAIN][init_integration.entry_id][ATTR_PLANT]
    ppfd = plant.ppfd
    await set_sensor_state(hass, plant.sensor_illuminance.external_sensor, "1000")
    assert ppfd.native_value is not None
    old_id = ppfd.entity_id
    new_id = f"{old_id}_renamed"
    old_state = hass.states.get(old_id)
    hass.states.async_set(new_id, old_state.state, old_state.attributes)

    ppfd.entity_id = new_id
    ppfd.async_entity_id_changed(old_id)
    hass.states.async_remove(old_id)
    await hass.async_block_till_done()

    assert ppfd.native_value is not None
