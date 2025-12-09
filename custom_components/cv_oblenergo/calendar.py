"""Calendar platform for Chernivtsi Power Schedule."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    ATTRIBUTION,
    CONF_GROUP,
)
from .coordinator import PowerScheduleCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up power schedule calendar from config entry."""
    coordinator: PowerScheduleCoordinator = hass.data[DOMAIN][entry.entry_id]
    group = entry.data.get(CONF_GROUP)

    # Create calendar for the configured group
    async_add_entities([PowerScheduleCalendar(coordinator, group, entry)])


class PowerScheduleCalendar(
    CoordinatorEntity[PowerScheduleCoordinator],
    CalendarEntity,
):
    """Calendar showing power outage schedule."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PowerScheduleCoordinator,
        group: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._group = group
        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_name = "Outages"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}")},
            name="CV",
            manufacturer="Chernivtsi Region",
            model=f"Group {group}",
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming event."""
        if not self.coordinator.data:
            return None

        schedule = self.coordinator.data.get_group(self._group)
        if not schedule:
            return None

        now = dt_util.now()
        events = self._get_events_for_schedule(schedule, now.date())

        # Find current or next event
        for event in events:
            if event.start <= now < event.end:
                return event
            if event.start > now:
                return event

        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        if not self.coordinator.data:
            return []

        schedule = self.coordinator.data.get_group(self._group)
        if not schedule:
            return []

        # Only return events for the schedule date (we only have current day)
        schedule_date = schedule.date
        if start_date.date() <= schedule_date <= end_date.date():
            return self._get_events_for_schedule(schedule, schedule_date)

        return []

    def _get_events_for_schedule(
        self,
        schedule,
        event_date,
    ) -> list[CalendarEvent]:
        """Generate calendar events from schedule."""
        events = []

        # Get OFF periods and create events for them
        off_periods = schedule.get_off_periods()

        for start_time, end_time in off_periods:
            start_h, start_m = map(int, start_time.split(":"))
            end_h, end_m = map(int, end_time.split(":"))

            start_dt = datetime.combine(
                event_date,
                datetime.min.time().replace(hour=start_h, minute=start_m),
            )
            start_dt = dt_util.as_local(start_dt.replace(tzinfo=None))

            # Handle midnight crossing
            if end_time == "00:00":
                end_dt = datetime.combine(
                    event_date + timedelta(days=1),
                    datetime.min.time(),
                )
            else:
                end_dt = datetime.combine(
                    event_date,
                    datetime.min.time().replace(hour=end_h, minute=end_m),
                )
            end_dt = dt_util.as_local(end_dt.replace(tzinfo=None))

            events.append(CalendarEvent(
                start=start_dt,
                end=end_dt,
                summary="Відключення електроенергії",
                description=f"Планове відключення електроенергії (група {self._group})",
            ))

        return sorted(events, key=lambda e: e.start)
