"""Plant entities take entity_id changes in place (#539)."""

from __future__ import annotations

import importlib
import inspect
import pkgutil

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity as entity_helper
from homeassistant.helpers.entity import Entity
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.plant as plant_package
from custom_components.plant.const import ATTR_PLANT, DOMAIN

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
