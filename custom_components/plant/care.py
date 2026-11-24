"""Care tasks for a plant, kept in a Home Assistant to-do list.

The plant stores nothing itself: open items are reminders, completed items are
the history. Each item carries a marker line in its description so a plant can
find its own items in a shared list.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.const import ATTR_ENTITY_ID, STATE_OK, STATE_UNAVAILABLE
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    CARE_FERTILIZE,
    CARE_MODE_INTERVAL,
    CARE_MODE_NONE,
    CARE_MODE_SENSOR,
    CARE_PRUNE,
    CARE_REPOT,
    CARE_WATER,
    FLOW_CARE_TODO,
    FLOW_FERTILIZE_INTERVAL,
    FLOW_PRUNE_INTERVAL,
    FLOW_REPOT_INTERVAL,
    FLOW_WATER_INTERVAL,
    STATE_HIGH,
    STATE_LOW,
)

if TYPE_CHECKING:
    from .event import PlantCareEvent

_LOGGER = logging.getLogger(__name__)

TODO_DOMAIN = "todo"
MARKER_SEPARATOR = " · "
STATUS_OPEN = "needs_action"
STATUS_COMPLETED = "completed"

SUMMARIES = {
    CARE_WATER: "Water {name}",
    CARE_FERTILIZE: "Fertilize {name}",
    CARE_REPOT: "Repot {name}",
    CARE_PRUNE: "Prune {name}",
}


def _marker(plant_entity_id: str, care: str) -> str:
    """The description line that marks an item as one plant's care item."""
    return f"{plant_entity_id}{MARKER_SEPARATOR}{care}"


INTERVAL_OPTIONS = {
    CARE_WATER: FLOW_WATER_INTERVAL,
    CARE_FERTILIZE: FLOW_FERTILIZE_INTERVAL,
    CARE_REPOT: FLOW_REPOT_INTERVAL,
    CARE_PRUNE: FLOW_PRUNE_INTERVAL,
}


@dataclass(frozen=True)
class CareSettings:
    """The options that care tasks are built from; a change needs a reload."""

    todo: str | None
    intervals: dict[str, int]


def care_settings(options: Mapping[str, Any]) -> CareSettings:
    """Read the care options; an interval that is not set counts as 0."""
    intervals = {}
    for care, option in INTERVAL_OPTIONS.items():
        intervals[care] = int(options.get(option, 0))
    return CareSettings(todo=options.get(FLOW_CARE_TODO), intervals=intervals)


def _care_mode(interval: int, has_sensor: bool, trigger: bool) -> str:
    if has_sensor and trigger:
        return CARE_MODE_SENSOR
    if interval > 0:
        return CARE_MODE_INTERVAL
    return CARE_MODE_NONE


def care_modes(
    settings: CareSettings,
    moisture_sensor: bool,
    conductivity_sensor: bool,
    moisture_trigger: bool,
    conductivity_trigger: bool,
) -> dict[str, str]:
    """How each care type is tracked: by its sensor, by interval, or not at all."""
    intervals = settings.intervals
    return {
        CARE_WATER: _care_mode(
            intervals[CARE_WATER], moisture_sensor, moisture_trigger
        ),
        CARE_FERTILIZE: _care_mode(
            intervals[CARE_FERTILIZE], conductivity_sensor, conductivity_trigger
        ),
        CARE_REPOT: _care_mode(intervals[CARE_REPOT], False, False),
        CARE_PRUNE: _care_mode(intervals[CARE_PRUNE], False, False),
    }


def _due_date(due: str) -> date:
    """The local date of a to-do item's due date or due time."""
    if len(due) == len("YYYY-MM-DD"):
        return date.fromisoformat(due)
    return dt_util.as_local(datetime.fromisoformat(due)).date()


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


class CareTasks:
    """Keep one plant's care items in a to-do list and report completed care."""

    def __init__(
        self,
        hass: HomeAssistant,
        plant_entity_id: str,
        plant_name: Callable[[], str],
        todo_entity_id: str,
        intervals: dict[str, int],
        modes: dict[str, str],
        care_events: dict[str, PlantCareEvent],
        moisture_status: Callable[[], str | None],
        conductivity_status: Callable[[], str | None],
    ) -> None:
        self._hass = hass
        self._moisture_status = moisture_status
        self._conductivity_status = conductivity_status
        self._plant_entity_id = plant_entity_id
        self._plant_name = plant_name
        self._todo_entity_id = todo_entity_id
        self._intervals = intervals
        self._modes = modes
        self._care_events = care_events
        # uid -> care type of our items that were open at the last look
        self._open_items: dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._unsubscribe: list[Callable[[], None]] = []
        # Set by async_stop; queued work checks it under the lock and does nothing
        self._stopped = False

    async def async_start(self) -> None:
        """Read the list once and follow its changes and the plant's name."""
        self._unsubscribe = [
            async_track_state_change_event(
                self._hass, [self._todo_entity_id], self._todo_changed
            ),
            async_track_state_change_event(
                self._hass, [self._plant_entity_id], self._plant_changed
            ),
        ]
        await self._async_sync(report_completed=False)
        # The sensors may have changed before we listened: match the list to them.
        # A status still restored from before a restart reads as None; the plant
        # then catches up on its first live reading.
        if self._modes[CARE_WATER] == CARE_MODE_SENSOR:
            moisture_status = self._moisture_status()
            if moisture_status == STATE_LOW:
                await self.async_moisture_low()
            elif moisture_status in (STATE_OK, STATE_HIGH):
                # Watered while we were not listening: the item is done
                await self._async_complete_open(CARE_WATER)
        if self._modes[CARE_FERTILIZE] == CARE_MODE_SENSOR:
            conductivity_status = self._conductivity_status()
            if conductivity_status == STATE_LOW:
                await self.async_conductivity_low()
            elif conductivity_status in (STATE_OK, STATE_HIGH):
                await self._async_complete_open(CARE_FERTILIZE)

    @property
    def todo_entity_id(self) -> str:
        """The to-do list this plant's care items live in."""
        return self._todo_entity_id

    @property
    def modes(self) -> dict[str, str]:
        """How each care type is tracked."""
        return self._modes

    @property
    def intervals(self) -> dict[str, int]:
        """Days between care of each type, for the types tracked by interval."""
        return self._intervals

    async def async_remove_open_items(self, cares: set[str] | None = None) -> None:
        """Remove this plant's open items, of all care types or just `cares`.

        Completed items stay as history.
        """
        async with self._lock:
            items = await self._async_own_items()
            uids = [
                item["uid"]
                for item in items
                if item["status"] == STATUS_OPEN
                and (cares is None or item["care"] in cares)
            ]
            if not uids:
                return
            await self._hass.services.async_call(
                TODO_DOMAIN,
                "remove_item",
                {ATTR_ENTITY_ID: self._todo_entity_id, "item": uids},
                blocking=True,
            )

    async def async_shift_open_items(self, shift_days: dict[str, int]) -> None:
        """Move the due date of open items by a number of days per care type."""
        async with self._lock:
            items = await self._async_own_items()
            for item in items:
                days = shift_days.get(item["care"])
                if not days or item["status"] != STATUS_OPEN or not item.get("due"):
                    continue
                due = _due_date(item["due"]) + timedelta(days=days)
                await self._hass.services.async_call(
                    TODO_DOMAIN,
                    "update_item",
                    {
                        ATTR_ENTITY_ID: self._todo_entity_id,
                        "item": item["uid"],
                        "due_date": due,
                    },
                    blocking=True,
                )

    @callback
    def async_stop(self) -> None:
        """Stop following the list and the plant, and drop work still queued.

        async_remove_open_items and async_shift_open_items still work afterwards,
        for cleaning up.
        """
        self._stopped = True
        for unsubscribe in self._unsubscribe:
            unsubscribe()
        self._unsubscribe = []

    async def async_move_items(self, new_plant_entity_id: str) -> None:
        """Point all of this plant's items at its new entity_id."""
        async with self._lock:
            items = await self._async_own_items()
            for item in items:
                description = item["description"].replace(
                    self._marker(item["care"]),
                    _marker(new_plant_entity_id, item["care"]),
                )
                await self._hass.services.async_call(
                    TODO_DOMAIN,
                    "update_item",
                    {
                        ATTR_ENTITY_ID: self._todo_entity_id,
                        "item": item["uid"],
                        "description": description,
                    },
                    blocking=True,
                )
            self._plant_entity_id = new_plant_entity_id

    async def async_moisture_low(self) -> None:
        """Add a watering item unless one is already open; only in sensor mode."""
        if self._modes[CARE_WATER] != CARE_MODE_SENSOR:
            return
        async with self._lock:
            if self._stopped:
                return
            items = await self._async_own_items()
            if self._open_of(items, CARE_WATER):
                return
            await self._async_add(CARE_WATER, dt_util.now().date())

    async def async_conductivity_low(self) -> None:
        """Add a fertilize item unless one is already open; only in sensor mode."""
        if self._modes[CARE_FERTILIZE] != CARE_MODE_SENSOR:
            return
        async with self._lock:
            if self._stopped:
                return
            items = await self._async_own_items()
            if self._open_of(items, CARE_FERTILIZE):
                return
            await self._async_add(CARE_FERTILIZE, dt_util.now().date())

    async def async_fertilized(self) -> None:
        """Tick off the open fertilize item, or report the fertilizing directly."""
        completed = await self._async_complete_open(CARE_FERTILIZE)
        if completed == 0 and not self._stopped:
            self._care_events[CARE_FERTILIZE].report()

    async def async_watered(self) -> None:
        """Tick off the open watering item, or report the watering directly."""
        completed = await self._async_complete_open(CARE_WATER)
        if completed == 0 and not self._stopped:
            self._care_events[CARE_WATER].report()

    async def _async_complete_open(self, care: str) -> int:
        """Tick off this plant's open items of one care type; return how many."""
        async with self._lock:
            if self._stopped:
                return 0
            items = await self._async_own_items()
            open_items = self._open_of(items, care)
            for item in open_items:
                # The list change that follows reports the care event
                await self._hass.services.async_call(
                    TODO_DOMAIN,
                    "update_item",
                    {
                        ATTR_ENTITY_ID: self._todo_entity_id,
                        "item": item["uid"],
                        "status": STATUS_COMPLETED,
                    },
                    blocking=True,
                )
        return len(open_items)

    @callback
    def _todo_changed(self, event: Event[EventStateChangedData]) -> None:
        self._hass.async_create_task(self._async_sync(report_completed=True))

    @callback
    def _plant_changed(self, event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        if old_state is None or new_state is None:
            return
        if old_state.name == new_state.name:
            return
        self._hass.async_create_task(self._async_rename_open_items())

    async def _async_rename_open_items(self) -> None:
        """Give open items the plant's current name; completed ones keep theirs."""
        async with self._lock:
            if self._stopped:
                return
            items = await self._async_own_items()
            for item in items:
                if item["status"] != STATUS_OPEN:
                    continue
                summary = SUMMARIES[item["care"]].format(name=self._plant_name())
                if item["summary"] == summary:
                    continue
                await self._hass.services.async_call(
                    TODO_DOMAIN,
                    "update_item",
                    {
                        ATTR_ENTITY_ID: self._todo_entity_id,
                        "item": item["uid"],
                        "rename": summary,
                    },
                    blocking=True,
                )

    async def _async_sync(self, report_completed: bool) -> None:
        """Report items completed since the last look, then plan interval items."""
        async with self._lock:
            if self._stopped:
                return
            items = await self._async_own_items()
            by_uid = {item["uid"]: item for item in items}
            just_completed = set()
            if report_completed:
                for uid, care in self._open_items.items():
                    item = by_uid.get(uid)
                    if item is not None and item["status"] == STATUS_COMPLETED:
                        just_completed.add(care)
                        self._care_events[care].report()
            self._open_items = {
                item["uid"]: item["care"]
                for item in items
                if item["status"] == STATUS_OPEN
            }
            await self._async_plan_interval_items(items, just_completed)

    async def _async_plan_interval_items(
        self, items: list[dict[str, Any]], just_completed: set[str]
    ) -> None:
        """Make sure every care type tracked by interval has an open item."""
        today = dt_util.now().date()
        for care, days in self._intervals.items():
            if self._modes[care] != CARE_MODE_INTERVAL or self._open_of(items, care):
                continue
            last_done = self._last_completed(items, care)
            if last_done is None and care in just_completed:
                # Lists without a completion time: we just saw it happen
                last_done = today
            due = today if last_done is None else last_done + timedelta(days=days)
            await self._async_add(care, due)

    async def _async_add(self, care: str, due: date) -> None:
        summary = SUMMARIES[care].format(name=self._plant_name())
        _LOGGER.debug("Adding '%s' due %s to %s", summary, due, self._todo_entity_id)
        await self._hass.services.async_call(
            TODO_DOMAIN,
            "add_item",
            {
                ATTR_ENTITY_ID: self._todo_entity_id,
                "item": summary,
                "due_date": due,
                "description": self._marker(care),
            },
            blocking=True,
        )

    async def _async_own_items(self) -> list[dict[str, Any]]:
        """This plant's items in the list, each with its care type added."""
        response = await self._hass.services.async_call(
            TODO_DOMAIN,
            "get_items",
            {ATTR_ENTITY_ID: self._todo_entity_id},
            blocking=True,
            return_response=True,
        )
        own = []
        for item in response[self._todo_entity_id]["items"]:
            care = self._care_of(item)
            if care is not None:
                own.append({**item, "care": care})
        return own

    def _marker(self, care: str) -> str:
        return _marker(self._plant_entity_id, care)

    def _care_of(self, item: dict[str, Any]) -> str | None:
        """The care type of one of our items, or None for anything else."""
        for line in item.get("description", "").splitlines():
            entity_id, separator, care = line.strip().partition(MARKER_SEPARATOR)
            if separator and entity_id == self._plant_entity_id and care in SUMMARIES:
                return care
        return None

    @staticmethod
    def _open_of(items: list[dict[str, Any]], care: str) -> list[dict[str, Any]]:
        return [
            item
            for item in items
            if item["care"] == care and item["status"] == STATUS_OPEN
        ]

    @staticmethod
    def _last_completed(items: list[dict[str, Any]], care: str) -> date | None:
        """Date of the newest completed item of this care type."""
        dates = []
        for item in items:
            if item["care"] != care or item["status"] != STATUS_COMPLETED:
                continue
            if "completed" not in item:
                continue
            completed = dt_util.as_local(datetime.fromisoformat(item["completed"]))
            dates.append(completed.date())
        return max(dates) if dates else None
