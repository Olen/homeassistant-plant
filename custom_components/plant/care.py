"""Care tasks for a plant, kept in a Home Assistant to-do list.

The plant stores nothing itself: open items are reminders, completed items are
the history. Each item carries a marker line in its description so a plant can
find its own items in a shared list.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    CARE_EVENT_TYPES,
    CARE_FERTILIZE,
    CARE_REPOT,
    CARE_WATER,
    FLOW_CARE_TODO,
    FLOW_FERTILIZE_INTERVAL,
    FLOW_REPOT_INTERVAL,
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
}


def care_settings(options: Mapping[str, Any]) -> tuple[str | None, int, int]:
    """The options that care tasks are built from; a change needs a reload."""
    return (
        options.get(FLOW_CARE_TODO),
        int(options.get(FLOW_FERTILIZE_INTERVAL, 0)),
        int(options.get(FLOW_REPOT_INTERVAL, 0)),
    )


class CareTasks:
    """Keep one plant's care items in a to-do list and report completed care."""

    def __init__(
        self,
        hass: HomeAssistant,
        plant_entity_id: str,
        plant_name: Callable[[], str],
        todo_entity_id: str,
        intervals: dict[str, int],
        care_event: PlantCareEvent,
        moisture_is_low: Callable[[], bool],
    ) -> None:
        self._hass = hass
        self._moisture_is_low = moisture_is_low
        self._plant_entity_id = plant_entity_id
        self._plant_name = plant_name
        self._todo_entity_id = todo_entity_id
        self._intervals = intervals
        self._care_event = care_event
        # uid -> care type of our items that were open at the last look
        self._open_items: dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._unsubscribe: Callable[[], None] | None = None

    async def async_start(self) -> None:
        """Read the list once and follow its changes."""
        self._unsubscribe = async_track_state_change_event(
            self._hass, [self._todo_entity_id], self._todo_changed
        )
        await self._async_sync(report_completed=False)
        # The plant may already be dry; the change to low happened before we listened
        if self._moisture_is_low():
            await self.async_moisture_low()

    @property
    def todo_entity_id(self) -> str:
        """The to-do list this plant's care items live in."""
        return self._todo_entity_id

    async def async_remove_open_items(self) -> None:
        """Remove this plant's open items; completed ones stay as history."""
        async with self._lock:
            items = await self._async_own_items()
            uids = [item["uid"] for item in items if item["status"] == STATUS_OPEN]
            if not uids:
                return
            await self._hass.services.async_call(
                TODO_DOMAIN,
                "remove_item",
                {ATTR_ENTITY_ID: self._todo_entity_id, "item": uids},
                blocking=True,
            )

    @callback
    def async_stop(self) -> None:
        """Stop following the list."""
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    async def async_moisture_low(self) -> None:
        """Add a watering item unless one is already open."""
        async with self._lock:
            items = await self._async_own_items()
            if self._open_of(items, CARE_WATER):
                return
            await self._async_add(CARE_WATER, dt_util.now().date())

    async def async_watering_detected(self) -> None:
        """Tick off the open watering item, or report the watering directly."""
        async with self._lock:
            items = await self._async_own_items()
            open_items = self._open_of(items, CARE_WATER)
        if not open_items:
            self._care_event.report(CARE_EVENT_TYPES[CARE_WATER])
            return
        for item in open_items:
            # The list change that follows reports the watering
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

    @callback
    def _todo_changed(self, event: Event[EventStateChangedData]) -> None:
        self._hass.async_create_task(self._async_sync(report_completed=True))

    async def _async_sync(self, report_completed: bool) -> None:
        """Report items completed since the last look, then plan interval items."""
        async with self._lock:
            items = await self._async_own_items()
            by_uid = {item["uid"]: item for item in items}
            just_completed = set()
            if report_completed:
                for uid, care in self._open_items.items():
                    item = by_uid.get(uid)
                    if item is not None and item["status"] == STATUS_COMPLETED:
                        just_completed.add(care)
                        self._care_event.report(CARE_EVENT_TYPES[care])
            self._open_items = {
                item["uid"]: item["care"]
                for item in items
                if item["status"] == STATUS_OPEN
            }
            await self._async_plan_interval_items(items, just_completed)

    async def _async_plan_interval_items(
        self, items: list[dict[str, Any]], just_completed: set[str]
    ) -> None:
        """Make sure every care type with an interval has an open item."""
        today = dt_util.now().date()
        for care, days in self._intervals.items():
            if days <= 0 or self._open_of(items, care):
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
        return f"{self._plant_entity_id}{MARKER_SEPARATOR}{care}"

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
            dates.append(datetime.fromisoformat(item["completed"]).date())
        return max(dates) if dates else None
