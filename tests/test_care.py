"""Tests for care tasks kept in a to-do list."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry, ConfigFlow
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from custom_components.plant.const import (
    DOMAIN,
    FLOW_CARE_TODO,
    FLOW_FERTILIZE_INTERVAL,
    FLOW_REPOT_INTERVAL,
)

from .common import set_sensor_state, update_plant_sensors
from .conftest import TEST_ENTRY_ID, TEST_PLANT_NAME
from .ha_common import (
    MockConfigEntry,
    MockModule,
    MockPlatform,
    mock_config_flow,
    mock_integration,
    mock_platform,
)

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

    async def async_setup_entry_init(hass: HomeAssistant, entry: ConfigEntry) -> bool:
        await hass.config_entries.async_forward_entry_setups(entry, [Platform.TODO])
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


def _care_events(hass: HomeAssistant) -> list[str]:
    """Event types recorded on the plant's care entity, oldest first."""
    entity_id = er.async_get(hass).async_get_entity_id(
        "event", DOMAIN, f"{TEST_ENTRY_ID}-care"
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
    await hass.async_block_till_done()


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

    async def test_detected_watering_ticks_the_item_off(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        await _setup_plant(hass, plant_config_data, {FLOW_CARE_TODO: TODO_ENTITY_ID})
        await _set_moisture(hass, 10)

        await _set_moisture(hass, 45)

        items = _own(todo_list)
        assert [item.status for item in items] == [TodoItemStatus.COMPLETED]
        assert _care_events(hass) == ["watered"]

    async def test_watering_without_an_open_item_is_still_reported(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass)
        await _setup_plant(hass, plant_config_data, {FLOW_CARE_TODO: TODO_ENTITY_ID})
        await _set_moisture(hass, 30)

        await _set_moisture(hass, 45)

        assert _own(todo_list) == []
        assert _care_events(hass) == ["watered"]

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

        assert _care_events(hass) == ["watered"]


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
            {FLOW_CARE_TODO: TODO_ENTITY_ID, FLOW_FERTILIZE_INTERVAL: 30},
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
            {FLOW_CARE_TODO: TODO_ENTITY_ID, FLOW_FERTILIZE_INTERVAL: 30},
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
            {FLOW_CARE_TODO: TODO_ENTITY_ID, FLOW_FERTILIZE_INTERVAL: 30},
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
        assert _care_events(hass) == ["fertilized"]

    async def test_list_without_completion_time_counts_from_today(
        self, hass: HomeAssistant, plant_config_data: dict[str, Any]
    ) -> None:
        todo_list = await _setup_todo_list(hass, records_completed_time=False)
        await _setup_plant(
            hass,
            plant_config_data,
            {FLOW_CARE_TODO: TODO_ENTITY_ID, FLOW_FERTILIZE_INTERVAL: 30},
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

        assert other_plant.status == TodoItemStatus.NEEDS_ACTION
        assert own_note.status == TodoItemStatus.NEEDS_ACTION
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
    entry = await _setup_plant(hass, plant_config_data, {})

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
