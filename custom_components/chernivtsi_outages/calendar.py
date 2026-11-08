"""Calendar of scheduled outages and possibly powered hours."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.translation import async_get_translations

from . import OutageConfigEntry
from .const import DOMAIN
from .coordinator import OutageCoordinator
from .entity import GroupEntity
from .model import Period, Slot

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: OutageConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(OutageCalendar(coordinator, group) for group in coordinator.groups)


class OutageCalendar(GroupEntity, CalendarEntity):
    def __init__(self, coordinator: OutageCoordinator, group: int) -> None:
        super().__init__(coordinator, group, "outages")
        self._names: dict[Slot, str] = {Slot.OFF: "Outage", Slot.MAYBE: "Possibly powered"}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Event titles follow the server language, like the sensor's state names.
        strings = await async_get_translations(
            self.hass, self.hass.config.language, "entity", {DOMAIN}
        )
        for slot in (Slot.OFF, Slot.MAYBE):
            key = f"component.{DOMAIN}.entity.sensor.schedule.state.{slot.value}"
            if key in strings:
                self._names[slot] = strings[key]

    def _event(self, period: Period) -> CalendarEvent:
        return CalendarEvent(start=period.start, end=period.end, summary=self._names[period.state])

    def _events(self) -> list[CalendarEvent]:
        return [self._event(p) for p in self.line if p.state is not Slot.ON]

    @property
    def event(self) -> CalendarEvent | None:
        now = self.now
        return next((e for e in self._events() if e.end > now), None)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return [e for e in self._events() if e.start < end_date and e.end > start_date]
