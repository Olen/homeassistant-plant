"""Tests for care tasks kept in a to-do list."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest
import voluptuous as vol
from awesomeversion import AwesomeVersion
from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry, ConfigFlow
from homeassistant.const import Platform, __version__ as HA_VERSION
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from custom_components.plant.care import CareSettings, CareTasks, care_modes
from custom_components.plant.care_trigger import is_new_care_event
from custom_components.plant.const import (
    CARE_FERTILIZE,
    CARE_MODE_INTERVAL,
    CARE_MODE_NONE,
    CARE_MODE_SENSOR,
    CARE_PRUNE,
    CARE_REPOT,
    CARE_WATER,
    DOMAIN,
    FLOW_CARE_TODO,
    FLOW_CONDUCTIVITY_TRIGGER,
    FLOW_FERTILIZE_INTERVAL,
    FLOW_MOISTURE_TRIGGER,
    FLOW_PRUNE_INTERVAL,
    FLOW_REPOT_INTERVAL,
    FLOW_WATER_INTERVAL,
    STATE_LOW,
)
from custom_components.plant.trigger import _has_purpose_trigger_api

from .common import set_sensor_state, update_plant_sensors
from .conftest import TEST_ENTRY_ID, TEST_PLANT_NAME
from .ha_common import (
    MockConfigEntry,
    MockModule,
    MockPlatform,
    async_capture_events,
    mock_config_flow,
    mock_integration,
    mock_platform,
)

# HA 2026.11 wants None from async_setup_entry; older versions want True
SETUP_ENTRY_RETURNS_NONE = AwesomeVersion(HA_VERSION) >= AwesomeVersion("2026.11.0")

TODO_ENTITY_ID = "todo.plants"
PLANT_ENTITY_ID = "plant.test_plant"
MOISTURE = "sensor.test_moisture"


class FakeTodoList(TodoListEntity):
    """A to-do list kept in memory, like Local To-do."""

    _attr_name = "Plants"
    _attr_unique_id = "plants"
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.SET_DUE_DATE_ON_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(self, records_completed_time: bool) -> None:
        self._attr_todo_items = []
        self._records_completed_time = records_completed_time

    async def async_create_todo_item(self, item: TodoItem) -> None:
        item.uid = uuid4().hex
        item.status = item.status or TodoItemStatus.NEEDS_ACTION
        self._attr_todo_items.append(item)
        self.async_write_ha_state()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        for index, existing in enumerate(self._attr_todo_items):
            if existing.uid != item.uid:
                continue
            if (
                self._records_completed_time
                and item.status == TodoItemStatus.COMPLETED
                and item.completed is None
            ):
                item.completed = dt_util.now()
            self._attr_todo_items[index] = item
        self.async_write_ha_state()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        self._attr_todo_items = [i for i in self._attr_todo_items if i.uid not in uids]
        self.async_write_ha_state()

    def add_existing(self, **fields: Any) -> TodoItem:
        """Put an item in the list as if it had been there already."""
        item = TodoItem(uid=uuid4().hex, **fields)
        self._attr_todo_items.append(item)
        self.async_write_ha_state()
        return item


async def _setup_todo_list(
    hass: HomeAssistant, records_completed_time: bool = True
) -> FakeTodoList:
    todo_list = FakeTodoList(records_completed_time)

    async def async_setup_entry_init(
        hass: HomeAssistant, entry: ConfigEntry
    ) -> bool | None:
        await hass.config_entries.async_forward_entry_setups(entry, [Platform.TODO])
        if SETUP_ENTRY_RETURNS_NONE:
            return None
        return True

    async def async_setup_entry_platform(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
    ) -> None:
        async_add_entities([todo_list])

    mock_integration(hass, MockModule("test", async_setup_entry=async_setup_entry_init))
    mock_platform(hass, "test.config_flow")
    mock_platform(
        hass, "test.todo", MockPlatform(async_setup_entry=async_setup_entry_platform)
    )
    assert await async_setup_component(hass, "todo", {})
    entry = MockConfigEntry(domain="test")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(TODO_ENTITY_ID) is not None
    return todo_list


async def _setup_plant(
    hass: HomeAssistant, plant_config_data: dict[str, Any], options: dict[str, Any]
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=TEST_PLANT_NAME,
        data=plant_config_data,
        options=options,
        entry_id=TEST_ENTRY_ID,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _care_events(hass: HomeAssistant, event_type: str) -> list[str]:
    """Event types recorded on the plant's entity for `event_type`, oldest first."""
    entity_id = er.async_get(hass).async_get_entity_id(
        "event", DOMAIN, f"{TEST_ENTRY_ID}-{event_type}"
    )
    return hass.data["care_events_seen"].get(entity_id, [])


class _TestFlow(ConfigFlow):
    """Config flow handler for the mock domain that holds the to-do list."""


@pytest.fixture(autouse=True)
def test_domain_flow():
    """Let the mock "test" domain have config entries."""
    with mock_config_flow("test", _TestFlow):
        yield


@pytest.fixture
def record_care_events(hass: HomeAssistant) -> None:
    """Collect every event type the care entity reports."""
    seen: dict[str, list[str]] = {}
    hass.data["care_events_seen"] = seen

    def _listener(event) -> None:
        new_state = event.data["new_state"]
        if new_state is None or not event.data["entity_id"].startswith("event."):
            return
        if new_state.attributes.get("event_type") is None:
            return
        seen.setdefault(event.data["entity_id"], []).append(
            new_state.attributes["event_type"]
        )

    hass.bus.async_listen("state_changed", _listener)


async def _set_moisture(hass: HomeAssistant, value: float) -> None:
    await set_sensor_state(hass, MOISTURE, value)
    await update_plant_sensors(hass, TEST_ENTRY_ID)
    # The plant hands its reaction to the loop with add_job, which is not a
    # task; let it run before waiting for what it starts.
    await asyncio.sleep(0)
    await hass.async_block_till_done()


def _current(todo_list: FakeTodoList, item: TodoItem) -> TodoItem:
    """The item as it is in the list now (updates replace the object)."""
    return next(i for i in todo_list.todo_items if i.uid == item.uid)


def _own(todo_list: FakeTodoList) -> list[TodoItem]:
    return [
        item
        for item in todo_list.todo_items
        if PLANT_ENTITY_ID in (item.description or "")
    ]


@pytest.mark.usefixtures("mock_external_sensors", "record_care_events")
class TestWatering:
    """Watering items come and go with the soil moisture."""

    async def test_dry_soil_adds_one_watering_item(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        await _setup_plant(hass, plant_config_data, {FLOW_CARE_TODO: TODO_ENTITY_ID})

        await _set_moisture(hass, 10)
        await _set_moisture(hass, 9)

        items = _own(todo_list)
        assert len(items) == 1
        assert items[0].summary == f"Water {TEST_PLANT_NAME}"
        assert items[0].status == TodoItemStatus.NEEDS_ACTION
        assert items[0].due == dt_util.now().date()
        assert items[0].description == f"{PLANT_ENTITY_ID} · water"

    async def test_plant_already_dry_gets_an_item_when_care_tasks_start(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        """The change to low happened before care tasks were listening."""
        todo_list = await _setup_todo_list(hass)
        entry = await _setup_plant(hass, plant_config_data, {})
        await _set_moisture(hass, 10)
        plant = hass.data[DOMAIN][entry.entry_id]["plant"]
        assert plant.moisture_status == STATE_LOW

        care_tasks = CareTasks(
            hass,
            plant_entity_id=PLANT_ENTITY_ID,
            plant_name=lambda: plant.name,
            todo_entity_id=TODO_ENTITY_ID,
            intervals={},
            modes={
                CARE_WATER: CARE_MODE_SENSOR,
                CARE_FERTILIZE: CARE_MODE_NONE,
                CARE_REPOT: CARE_MODE_NONE,
                CARE_PRUNE: CARE_MODE_NONE,
            },
            care_events=plant.care_events,
            moisture_status=lambda: plant.moisture_status,
        )
        await care_tasks.async_start()
        await hass.async_block_till_done()
        care_tasks.async_stop()

        assert [i.summary for i in _own(todo_list)] == [f"Water {TEST_PLANT_NAME}"]

    async def test_detected_watering_ticks_the_item_off(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        await _setup_plant(hass, plant_config_data, {FLOW_CARE_TODO: TODO_ENTITY_ID})
        await _set_moisture(hass, 10)

        await _set_moisture(hass, 45)

        items = _own(todo_list)
        assert [item.status for item in items] == [TodoItemStatus.COMPLETED]
        assert _care_events(hass, "watered") == ["watered"]

    async def test_slow_rise_out_of_dry_ticks_the_item_off(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        """Dry soil soaks water up slowly: no 10-point jump, but no longer dry."""
        todo_list = await _setup_todo_list(hass)
        await _setup_plant(hass, plant_config_data, {FLOW_CARE_TODO: TODO_ENTITY_ID})
        await _set_moisture(hass, 15)

        await _set_moisture(hass, 23)

        assert [i.status for i in _own(todo_list)] == [TodoItemStatus.COMPLETED]
        assert _care_events(hass, "watered") == ["watered"]

    async def test_item_left_open_while_away_is_ticked_off_at_start(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        """Watered while Home Assistant was down: the soil is fine at start."""
        todo_list = await _setup_todo_list(hass)
        left_open = todo_list.add_existing(
            summary=f"Water {TEST_PLANT_NAME}",
            status=TodoItemStatus.NEEDS_ACTION,
            description=f"{PLANT_ENTITY_ID} · water",
        )
        entry = await _setup_plant(hass, plant_config_data, {})
        await _set_moisture(hass, 45)

        hass.config_entries.async_update_entry(
            entry, options={FLOW_CARE_TODO: TODO_ENTITY_ID}
        )
        await hass.async_block_till_done()

        assert _current(todo_list, left_open).status == TodoItemStatus.COMPLETED

    async def test_watering_without_an_open_item_is_still_reported(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        await _setup_plant(hass, plant_config_data, {FLOW_CARE_TODO: TODO_ENTITY_ID})
        await _set_moisture(hass, 30)

        await _set_moisture(hass, 45)

        assert _own(todo_list) == []
        assert _care_events(hass, "watered") == ["watered"]

    async def test_ticking_off_by_hand_reports_watering(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        await _setup_plant(hass, plant_config_data, {FLOW_CARE_TODO: TODO_ENTITY_ID})
        await _set_moisture(hass, 10)
        item = _own(todo_list)[0]

        await hass.services.async_call(
            "todo",
            "update_item",
            {"entity_id": TODO_ENTITY_ID, "item": item.uid, "status": "completed"},
            blocking=True,
        )
        await hass.async_block_till_done()

        assert _care_events(hass, "watered") == ["watered"]


@pytest.mark.usefixtures("mock_external_sensors", "record_care_events")
class TestWateredRule:
    """Watered = a 10-point rise, or the soil leaving "low"; list or not."""

    async def test_slow_rise_out_of_dry_counts_without_a_list(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        await _setup_plant(hass, plant_config_data, {})
        await _set_moisture(hass, 15)

        await _set_moisture(hass, 23)

        assert _care_events(hass, "watered") == ["watered"]

    async def test_rise_inside_the_hysteresis_band_is_not_watered(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        """Min 20 with the 2-point moisture band: still low at 22, not at 23."""
        await _setup_plant(hass, plant_config_data, {})
        await _set_moisture(hass, 15)

        await _set_moisture(hass, 22)
        assert _care_events(hass, "watered") == []

        await _set_moisture(hass, 23)
        assert _care_events(hass, "watered") == ["watered"]

    async def test_small_rise_in_moist_soil_is_not_watered(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        await _setup_plant(hass, plant_config_data, {})
        await _set_moisture(hass, 30)

        await _set_moisture(hass, 38)

        assert _care_events(hass, "watered") == []

    async def test_jump_out_of_dry_counts_once(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        await _setup_plant(hass, plant_config_data, {})
        await _set_moisture(hass, 15)

        await _set_moisture(hass, 45)

        assert _care_events(hass, "watered") == ["watered"]


@pytest.mark.usefixtures("mock_external_sensors", "record_care_events")
class TestEventEntities:
    """Every care type has its own event entity."""

    async def test_one_event_entity_per_care_type(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        await _setup_plant(hass, plant_config_data, {})

        registry = er.async_get(hass)
        for event_type in ("watered", "fertilized", "repotted", "pruned"):
            assert registry.async_get_entity_id(
                "event", DOMAIN, f"{TEST_ENTRY_ID}-{event_type}"
            )
        assert (
            registry.async_get_entity_id("event", DOMAIN, f"{TEST_ENTRY_ID}-care")
            is None
        )

    async def test_watering_reports_only_the_watered_entity(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        await _setup_plant(hass, plant_config_data, {})
        await _set_moisture(hass, 20)

        await _set_moisture(hass, 35)

        assert _care_events(hass, "watered") == ["watered"]
        assert _care_events(hass, "fertilized") == []


@pytest.mark.usefixtures("mock_external_sensors", "record_care_events")
class TestIntervals:
    """Fertilizing follows the interval, counted from when it was done."""

    async def test_first_item_is_due_today(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        await _setup_plant(
            hass,
            plant_config_data,
            {
                FLOW_CARE_TODO: TODO_ENTITY_ID,
                FLOW_CONDUCTIVITY_TRIGGER: False,
                FLOW_FERTILIZE_INTERVAL: 30,
            },
        )

        items = _own(todo_list)
        assert [(i.summary, i.due) for i in items] == [
            (f"Fertilize {TEST_PLANT_NAME}", dt_util.now().date())
        ]

    async def test_next_item_counts_from_the_last_time_it_was_done(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        done = dt_util.now() - timedelta(days=10)
        todo_list.add_existing(
            summary="Fertilize",
            status=TodoItemStatus.COMPLETED,
            description=f"{PLANT_ENTITY_ID} · fertilize",
            completed=done,
        )

        await _setup_plant(
            hass,
            plant_config_data,
            {
                FLOW_CARE_TODO: TODO_ENTITY_ID,
                FLOW_CONDUCTIVITY_TRIGGER: False,
                FLOW_FERTILIZE_INTERVAL: 30,
            },
        )

        open_items = [
            i for i in _own(todo_list) if i.status == TodoItemStatus.NEEDS_ACTION
        ]
        assert [i.due for i in open_items] == [done.date() + timedelta(days=30)]

    async def test_completing_plans_the_next_one(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        await _setup_plant(
            hass,
            plant_config_data,
            {
                FLOW_CARE_TODO: TODO_ENTITY_ID,
                FLOW_CONDUCTIVITY_TRIGGER: False,
                FLOW_FERTILIZE_INTERVAL: 30,
            },
        )
        first = _own(todo_list)[0]

        await hass.services.async_call(
            "todo",
            "update_item",
            {"entity_id": TODO_ENTITY_ID, "item": first.uid, "status": "completed"},
            blocking=True,
        )
        await hass.async_block_till_done()

        open_items = [
            i for i in _own(todo_list) if i.status == TodoItemStatus.NEEDS_ACTION
        ]
        assert [i.due for i in open_items] == [
            dt_util.now().date() + timedelta(days=30)
        ]
        assert _care_events(hass, "fertilized") == ["fertilized"]

    async def test_list_without_completion_time_counts_from_today(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass, records_completed_time=False)
        await _setup_plant(
            hass,
            plant_config_data,
            {
                FLOW_CARE_TODO: TODO_ENTITY_ID,
                FLOW_CONDUCTIVITY_TRIGGER: False,
                FLOW_FERTILIZE_INTERVAL: 30,
            },
        )
        first = _own(todo_list)[0]

        await hass.services.async_call(
            "todo",
            "update_item",
            {"entity_id": TODO_ENTITY_ID, "item": first.uid, "status": "completed"},
            blocking=True,
        )
        await hass.async_block_till_done()

        open_items = [
            i for i in _own(todo_list) if i.status == TodoItemStatus.NEEDS_ACTION
        ]
        assert [i.due for i in open_items] == [
            dt_util.now().date() + timedelta(days=30)
        ]


@pytest.mark.usefixtures("mock_external_sensors", "record_care_events")
class TestSharedList:
    """A shared list holds other plants' items and the user's own."""

    async def test_other_items_are_left_alone(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        other_plant = todo_list.add_existing(
            summary="Water the fern",
            status=TodoItemStatus.NEEDS_ACTION,
            description="plant.fern · water",
        )
        own_note = todo_list.add_existing(
            summary="Buy soil", status=TodoItemStatus.NEEDS_ACTION
        )
        await _setup_plant(hass, plant_config_data, {FLOW_CARE_TODO: TODO_ENTITY_ID})

        # The fern's watering item must not stop ours from being added
        await _set_moisture(hass, 10)
        await _set_moisture(hass, 45)

        assert _current(todo_list, other_plant).status == TodoItemStatus.NEEDS_ACTION
        assert _current(todo_list, own_note).status == TodoItemStatus.NEEDS_ACTION
        assert [i.status for i in _own(todo_list)] == [TodoItemStatus.COMPLETED]


@pytest.mark.usefixtures("mock_external_sensors")
async def test_missing_list_leaves_the_plant_working(
    hass: HomeAssistant, plant_config_data: dict[str, Any]
) -> None:
    """A to-do list that no longer exists turns care tasks off, nothing else."""
    assert await async_setup_component(hass, "todo", {})
    entry = await _setup_plant(
        hass, plant_config_data, {FLOW_CARE_TODO: "todo.does_not_exist"}
    )

    plant = hass.data[DOMAIN][entry.entry_id]["plant"]
    assert plant.care_tasks is None
    assert hass.states.get(PLANT_ENTITY_ID) is not None


@pytest.mark.usefixtures("mock_external_sensors")
async def test_options_step_saves_the_chosen_list(
    hass: HomeAssistant, plant_config_data: dict[str, Any]
) -> None:
    """Choosing an existing list and intervals stores them and starts care tasks."""
    todo_list = await _setup_todo_list(hass)
    entry = await _setup_plant(
        hass, plant_config_data, {FLOW_CONDUCTIVITY_TRIGGER: False}
    )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "care_tasks"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            FLOW_CARE_TODO: TODO_ENTITY_ID,
            FLOW_FERTILIZE_INTERVAL: 30,
            FLOW_REPOT_INTERVAL: 0,
        },
    )
    await hass.async_block_till_done()

    assert entry.options[FLOW_CARE_TODO] == TODO_ENTITY_ID
    assert entry.options[FLOW_FERTILIZE_INTERVAL] == 30
    # The reload started care tasks, which planned the first fertilizing
    assert [i.summary for i in _own(todo_list)] == [f"Fertilize {TEST_PLANT_NAME}"]


async def _automation_on(hass: HomeAssistant, trigger: str, event: str) -> list:
    """An automation firing `event` on plant.<trigger> for the test plant."""
    events = async_capture_events(hass, event)
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "trigger": {
                    "trigger": f"plant.{trigger}",
                    "target": {"entity_id": PLANT_ENTITY_ID},
                },
                "action": {"event": event},
            }
        },
    )
    await hass.async_block_till_done()
    return events


@pytest.mark.skipif(
    not _has_purpose_trigger_api(), reason="plant.* triggers need HA 2026.7+"
)
@pytest.mark.usefixtures("mock_external_sensors")
class TestCareTriggers:
    """plant.watered / fertilized fire from the care event entity."""

    async def test_watered_fires_without_a_todo_list(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        await _setup_plant(hass, plant_config_data, {})
        watered = await _automation_on(hass, "watered", "was_watered")
        await _set_moisture(hass, 20)

        await _set_moisture(hass, 45)

        assert len(watered) == 1

    async def test_fertilized_fires_when_the_item_is_ticked_off(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        await _setup_plant(
            hass,
            plant_config_data,
            {
                FLOW_CARE_TODO: TODO_ENTITY_ID,
                FLOW_CONDUCTIVITY_TRIGGER: False,
                FLOW_FERTILIZE_INTERVAL: 30,
            },
        )
        fertilized = await _automation_on(hass, "fertilized", "was_fertilized")
        watered = await _automation_on(hass, "watered", "was_watered")

        await hass.services.async_call(
            "todo",
            "update_item",
            {
                "entity_id": TODO_ENTITY_ID,
                "item": _own(todo_list)[0].uid,
                "status": "completed",
            },
            blocking=True,
        )
        await hass.async_block_till_done()

        assert len(fertilized) == 1
        assert watered == []


def test_restored_care_event_is_not_a_new_one() -> None:
    """Restoring the last event at startup, or recovering, must not fire."""
    watered = {"event_type": "watered"}
    earlier = State("event.care", "2026-11-18T10:00:00.000+00:00", watered)
    later = State("event.care", "2026-11-19T10:00:00.000+00:00", watered)

    assert is_new_care_event(earlier, later, "watered")
    assert not is_new_care_event(None, later, "watered")
    assert not is_new_care_event(State("event.care", "unavailable"), later, "watered")
    assert not is_new_care_event(later, later, "watered")
    assert not is_new_care_event(earlier, later, "fertilized")
    # The very first event ever goes from unknown to a timestamp
    assert is_new_care_event(State("event.care", "unknown"), later, "watered")


async def _configure_care(
    hass: HomeAssistant, entry: MockConfigEntry, todo_entity_id: str | None
) -> None:
    """Submit the Care tasks options step, the way the UI does."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "care_tasks"}
    )
    user_input: dict[str, Any] = {FLOW_FERTILIZE_INTERVAL: 0, FLOW_REPOT_INTERVAL: 0}
    if todo_entity_id is not None:
        user_input[FLOW_CARE_TODO] = todo_entity_id
    await hass.config_entries.options.async_configure(result["flow_id"], user_input)
    await hass.async_block_till_done()


@pytest.mark.usefixtures("mock_external_sensors")
class TestSwitchingOff:
    """Switching care tasks off cleans up and is visible on the plant."""

    async def test_open_items_are_removed_history_stays(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        done = todo_list.add_existing(
            summary="Water",
            status=TodoItemStatus.COMPLETED,
            description=f"{PLANT_ENTITY_ID} · water",
            completed=dt_util.now() - timedelta(days=3),
        )
        other_plant = todo_list.add_existing(
            summary="Water the fern",
            status=TodoItemStatus.NEEDS_ACTION,
            description="plant.fern · water",
        )
        entry = await _setup_plant(
            hass, plant_config_data, {FLOW_CARE_TODO: TODO_ENTITY_ID}
        )
        await _set_moisture(hass, 10)
        assert len(_own(todo_list)) == 2

        await _configure_care(hass, entry, None)

        assert _own(todo_list) == [done]
        assert other_plant in todo_list.todo_items

    async def test_plant_shows_which_list_it_uses(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        await _setup_todo_list(hass)
        entry = await _setup_plant(hass, plant_config_data, {})
        assert hass.states.get(PLANT_ENTITY_ID).attributes["care_todo_list"] is None

        await _configure_care(hass, entry, TODO_ENTITY_ID)
        assert (
            hass.states.get(PLANT_ENTITY_ID).attributes["care_todo_list"]
            == TODO_ENTITY_ID
        )

        await _configure_care(hass, entry, None)
        assert hass.states.get(PLANT_ENTITY_ID).attributes["care_todo_list"] is None


@pytest.mark.usefixtures("mock_external_sensors")
async def test_items_use_the_plant_name_and_menu_the_entry_title(
    hass: HomeAssistant, plant_config_data: dict[str, Any]
) -> None:
    """Care items use the plant's displayed name; the options flow the entry title."""
    todo_list = await _setup_todo_list(hass)
    entry = await _setup_plant(
        hass, plant_config_data, {FLOW_CARE_TODO: TODO_ENTITY_ID}
    )
    er.async_get(hass).async_update_entity(PLANT_ENTITY_ID, name="Monstéra")
    await hass.async_block_till_done()

    await _set_moisture(hass, 10)
    menu = await hass.config_entries.options.async_init(entry.entry_id)

    # HA 2026.11+ shows "<device> <entity>", older versions the entity name
    shown = hass.states.get(PLANT_ENTITY_ID).name
    assert "Monstéra" in shown
    assert [i.summary for i in _own(todo_list)] == [f"Water {shown}"]
    assert menu["description_placeholders"]["plant_name"] == entry.title


async def _tick_off(hass: HomeAssistant, item: TodoItem) -> None:
    await hass.services.async_call(
        "todo",
        "update_item",
        {"entity_id": TODO_ENTITY_ID, "item": item.uid, "status": "completed"},
        blocking=True,
    )
    await hass.async_block_till_done()


@pytest.mark.usefixtures("mock_external_sensors")
class TestRenamingThePlant:
    """Renaming a plant in Home Assistant carries over to its care items."""

    async def test_new_name_goes_to_open_items_not_history(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        await _setup_plant(hass, plant_config_data, {FLOW_CARE_TODO: TODO_ENTITY_ID})
        await _set_moisture(hass, 10)
        await _tick_off(hass, _own(todo_list)[0])
        await _set_moisture(hass, 45)
        await _set_moisture(hass, 10)
        shown_before = hass.states.get(PLANT_ENTITY_ID).name

        er.async_get(hass).async_update_entity(PLANT_ENTITY_ID, name="Monstéra")
        await hass.async_block_till_done()

        shown_after = hass.states.get(PLANT_ENTITY_ID).name
        assert "Monstéra" in shown_after
        by_status = {i.status: i.summary for i in _own(todo_list)}
        assert by_status == {
            TodoItemStatus.COMPLETED: f"Water {shown_before}",
            TodoItemStatus.NEEDS_ACTION: f"Water {shown_after}",
        }

    async def test_logbook_uses_the_new_name(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        await _setup_plant(hass, plant_config_data, {})
        er.async_get(hass).async_update_entity(PLANT_ENTITY_ID, name="Monstéra")
        await hass.async_block_till_done()
        with patch("custom_components.plant.log_entry") as log_entry:
            await _set_moisture(hass, 10)

        names = [call.args[1] for call in log_entry.call_args_list]
        assert names == [hass.states.get(PLANT_ENTITY_ID).name]
        assert "Monstéra" in names[0]

    async def test_new_entity_id_keeps_items_and_history(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        fertilized = dt_util.now() - timedelta(days=10)
        todo_list.add_existing(
            summary=f"Fertilize {TEST_PLANT_NAME}",
            status=TodoItemStatus.COMPLETED,
            description=f"{PLANT_ENTITY_ID} · fertilize",
            completed=fertilized,
        )
        await _setup_plant(
            hass,
            plant_config_data,
            {
                FLOW_CARE_TODO: TODO_ENTITY_ID,
                FLOW_CONDUCTIVITY_TRIGGER: False,
                FLOW_FERTILIZE_INTERVAL: 30,
            },
        )
        await _set_moisture(hass, 10)
        before = {(i.summary, i.status, i.due) for i in todo_list.todo_items}

        er.async_get(hass).async_update_entity(
            PLANT_ENTITY_ID, new_entity_id="plant.monstera"
        )
        await hass.async_block_till_done()
        await _set_moisture(hass, 9)

        # Same items, nothing added twice, all pointing at the new entity_id
        assert {(i.summary, i.status, i.due) for i in todo_list.todo_items} == before
        assert sorted(i.description for i in todo_list.todo_items) == [
            "plant.monstera · fertilize",
            "plant.monstera · fertilize",
            "plant.monstera · water",
        ]


def _settings(**intervals: int) -> CareSettings:
    all_intervals = {
        CARE_WATER: 0,
        CARE_FERTILIZE: 0,
        CARE_REPOT: 0,
        CARE_PRUNE: 0,
    }
    all_intervals.update(intervals)
    return CareSettings(todo=TODO_ENTITY_ID, intervals=all_intervals)


@pytest.mark.parametrize(
    "care, interval, sensor, trigger, expected",
    [
        (CARE_WATER, 0, True, True, CARE_MODE_SENSOR),
        (CARE_WATER, 3, True, False, CARE_MODE_INTERVAL),
        (CARE_WATER, 3, False, True, CARE_MODE_INTERVAL),
        (CARE_WATER, 0, False, True, CARE_MODE_NONE),
        (CARE_WATER, 0, True, False, CARE_MODE_NONE),
        (CARE_WATER, 3, True, True, CARE_MODE_SENSOR),
        (CARE_FERTILIZE, 0, True, True, CARE_MODE_SENSOR),
        (CARE_FERTILIZE, 3, True, False, CARE_MODE_INTERVAL),
        (CARE_FERTILIZE, 3, False, True, CARE_MODE_INTERVAL),
        (CARE_FERTILIZE, 0, False, True, CARE_MODE_NONE),
        (CARE_FERTILIZE, 3, True, True, CARE_MODE_SENSOR),
        (CARE_REPOT, 365, True, True, CARE_MODE_INTERVAL),
        (CARE_REPOT, 0, True, True, CARE_MODE_NONE),
        (CARE_PRUNE, 30, True, True, CARE_MODE_INTERVAL),
        (CARE_PRUNE, 0, True, True, CARE_MODE_NONE),
    ],
)
def test_care_modes(
    care: str, interval: int, sensor: bool, trigger: bool, expected: str
) -> None:
    """A checked trigger with its sensor wins; otherwise the interval decides."""
    modes = care_modes(
        _settings(**{care: interval}),
        moisture_sensor=sensor if care == CARE_WATER else False,
        conductivity_sensor=sensor if care == CARE_FERTILIZE else False,
        moisture_trigger=trigger if care == CARE_WATER else False,
        conductivity_trigger=trigger if care == CARE_FERTILIZE else False,
    )
    assert modes[care] == expected


def _open(todo_list: FakeTodoList, care: str) -> list[TodoItem]:
    return [
        i
        for i in _own(todo_list)
        if i.status == TodoItemStatus.NEEDS_ACTION
        and i.description.endswith(f" · {care}")
    ]


async def _submit_plant_properties(
    hass: HomeAssistant, entry: MockConfigEntry, changes: dict[str, Any]
) -> None:
    """Submit the plant properties step with the form's defaults plus `changes`."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "plant_properties"}
    )
    defaults = {
        str(key): key.default()
        for key in result["data_schema"].schema
        if key.default is not vol.UNDEFINED
    }
    await hass.config_entries.options.async_configure(
        result["flow_id"], {**defaults, **changes}
    )
    await hass.async_block_till_done()


@pytest.mark.usefixtures("record_care_events")
class TestCareModes:
    """The trigger checkboxes and intervals decide how each care is tracked."""

    async def test_water_interval_mode_plans_items(
        self,
        hass: HomeAssistant,
        plant_config_data_no_sensors: dict[str, Any],
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        await _setup_plant(
            hass,
            plant_config_data_no_sensors,
            {FLOW_CARE_TODO: TODO_ENTITY_ID, FLOW_WATER_INTERVAL: 7},
        )

        first = _open(todo_list, CARE_WATER)
        assert [(i.summary, i.due) for i in first] == [
            (f"Water {TEST_PLANT_NAME}", dt_util.now().date())
        ]

        await _tick_off(hass, first[0])

        assert [i.due for i in _open(todo_list, CARE_WATER)] == [
            dt_util.now().date() + timedelta(days=7)
        ]

    @pytest.mark.usefixtures("mock_external_sensors")
    async def test_water_interval_mode_ignores_dry_soil(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        await _setup_plant(
            hass,
            plant_config_data,
            {
                FLOW_CARE_TODO: TODO_ENTITY_ID,
                FLOW_MOISTURE_TRIGGER: False,
                FLOW_WATER_INTERVAL: 7,
            },
        )

        await _set_moisture(hass, 10)

        assert len(_open(todo_list, CARE_WATER)) == 1

    @pytest.mark.usefixtures("mock_external_sensors")
    async def test_water_interval_mode_detected_watering_completes_item(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        await _setup_plant(
            hass,
            plant_config_data,
            {
                FLOW_CARE_TODO: TODO_ENTITY_ID,
                FLOW_MOISTURE_TRIGGER: False,
                FLOW_WATER_INTERVAL: 7,
            },
        )
        await _set_moisture(hass, 10)
        interval_item = _open(todo_list, CARE_WATER)[0]

        await _set_moisture(hass, 45)

        assert _current(todo_list, interval_item).status == TodoItemStatus.COMPLETED
        assert _care_events(hass, "watered") == ["watered"]

    @pytest.mark.usefixtures("mock_external_sensors")
    async def test_mode_change_removes_open_items_of_that_type(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        entry = await _setup_plant(
            hass,
            plant_config_data,
            {
                FLOW_CARE_TODO: TODO_ENTITY_ID,
                FLOW_CONDUCTIVITY_TRIGGER: False,
                FLOW_FERTILIZE_INTERVAL: 15,
                FLOW_REPOT_INTERVAL: 365,
            },
        )
        fertilize_item = _open(todo_list, CARE_FERTILIZE)[0]
        repot_item = _open(todo_list, CARE_REPOT)[0]

        await _submit_plant_properties(hass, entry, {FLOW_CONDUCTIVITY_TRIGGER: True})

        assert fertilize_item not in todo_list.todo_items
        assert repot_item in todo_list.todo_items

    @pytest.mark.usefixtures("mock_external_sensors")
    async def test_plant_properties_step_keeps_the_care_options(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        await _setup_todo_list(hass)
        entry = await _setup_plant(
            hass,
            plant_config_data,
            {
                FLOW_CARE_TODO: TODO_ENTITY_ID,
                FLOW_WATER_INTERVAL: 7,
                FLOW_PRUNE_INTERVAL: 30,
            },
        )

        await _submit_plant_properties(hass, entry, {FLOW_MOISTURE_TRIGGER: False})

        assert entry.options[FLOW_MOISTURE_TRIGGER] is False
        assert entry.options[FLOW_CARE_TODO] == TODO_ENTITY_ID
        assert entry.options[FLOW_WATER_INTERVAL] == 7
        assert entry.options[FLOW_PRUNE_INTERVAL] == 30

    @pytest.mark.usefixtures("mock_external_sensors")
    async def test_ticking_off_prune_item_reports_pruned(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        await _setup_plant(
            hass,
            plant_config_data,
            {FLOW_CARE_TODO: TODO_ENTITY_ID, FLOW_PRUNE_INTERVAL: 30},
        )
        first = _open(todo_list, CARE_PRUNE)
        assert [i.summary for i in first] == [f"Prune {TEST_PLANT_NAME}"]

        await _tick_off(hass, first[0])

        assert _care_events(hass, "pruned") == ["pruned"]
        assert [i.due for i in _open(todo_list, CARE_PRUNE)] == [
            dt_util.now().date() + timedelta(days=30)
        ]

    @pytest.mark.usefixtures("mock_external_sensors")
    async def test_rename_moves_prune_items(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        await _setup_plant(
            hass,
            plant_config_data,
            {FLOW_CARE_TODO: TODO_ENTITY_ID, FLOW_PRUNE_INTERVAL: 30},
        )

        er.async_get(hass).async_update_entity(PLANT_ENTITY_ID, name="Monstéra")
        await hass.async_block_till_done()

        shown = hass.states.get(PLANT_ENTITY_ID).name
        assert [i.summary for i in _open(todo_list, CARE_PRUNE)] == [f"Prune {shown}"]

    @pytest.mark.usefixtures("mock_external_sensors")
    async def test_options_step_saves_water_and_prune_intervals(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        await _setup_todo_list(hass)
        entry = await _setup_plant(hass, plant_config_data, {})

        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "care_tasks"}
        )
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                FLOW_CARE_TODO: TODO_ENTITY_ID,
                FLOW_WATER_INTERVAL: 7,
                FLOW_PRUNE_INTERVAL: 730,
            },
        )
        await hass.async_block_till_done()

        assert entry.options[FLOW_WATER_INTERVAL] == 7
        assert entry.options[FLOW_PRUNE_INTERVAL] == 730
