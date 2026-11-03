"""Sensors: scheduled state, next outage, when power is back, scheduled hours."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OutageConfigEntry
from .coordinator import OutageCoordinator
from .entity import GroupEntity
from .model import DaySchedule, Slot, hours, next_outage, outage_end, periods

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: OutageConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        entity
        for group in coordinator.groups
        for entity in (
            ScheduleSensor(coordinator, group),
            NextOutageSensor(coordinator, group),
            PowerBackSensor(coordinator, group),
            HoursSensor(coordinator, group, "outage_hours", Slot.OFF),
            HoursSensor(coordinator, group, "possible_outage_hours", Slot.MAYBE),
            ChangedSensor(coordinator, group),
        )
    )


def _day_periods(schedule: DaySchedule | None, group: int) -> list[dict[str, str]] | None:
    if schedule is None:
        return None
    return [
        {
            "start": p.start.strftime("%H:%M"),
            "end": "24:00" if p.end.date() != p.start.date() else p.end.strftime("%H:%M"),
            "state": p.state.value,
        }
        for p in periods(schedule.day, schedule.groups[group])
    ]


class ScheduleSensor(GroupEntity, SensorEntity):
    """On, off or maybe, as scheduled right now."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [slot.value for slot in Slot]
    _unrecorded_attributes = frozenset({"today", "tomorrow"})

    def __init__(self, coordinator: OutageCoordinator, group: int) -> None:
        super().__init__(coordinator, group, "schedule")

    @property
    def native_value(self) -> str | None:
        state = self.state_now
        return state.value if state else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        today = self.coordinator.today(self.now)
        tomorrow = self.coordinator.tomorrow(self.now)
        return {
            "group": self.outage_group,
            "date": today.day.isoformat() if today else None,
            "schedule_active": today.active if today else None,
            "source": today.source if today else None,
            "degraded": today.degraded if today else None,
            "today": _day_periods(today, self.outage_group),
            "tomorrow": _day_periods(tomorrow, self.outage_group),
        }


class NextOutageSensor(GroupEntity, SensorEntity):
    """Start of the next outage that has not begun yet."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: OutageCoordinator, group: int) -> None:
        super().__init__(coordinator, group, "next_outage")

    @property
    def native_value(self) -> datetime | None:
        period = next_outage(self.line, self.now)
        return period.start if period else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        line = self.line
        period = next_outage(line, self.now)
        ends = period is not None and any(p.start == period.end for p in line)
        return {
            "end": period.end.isoformat() if period and ends else None,
            "duration_hours": period.hours if period and ends else None,
        }


class PowerBackSensor(GroupEntity, SensorEntity):
    """When the current, or else the next, outage ends."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: OutageCoordinator, group: int) -> None:
        super().__init__(coordinator, group, "power_back")

    @property
    def native_value(self) -> datetime | None:
        end = outage_end(self.line, self.now)
        return end[0] if end else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        end = outage_end(self.line, self.now)
        return {"then": end[1].value if end else None}


class HoursSensor(GroupEntity, SensorEntity):
    """Scheduled hours of a state today, as they were scheduled when they passed."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(
        self, coordinator: OutageCoordinator, group: int, key: str, state: Slot
    ) -> None:
        super().__init__(coordinator, group, key)
        self._state = state

    @property
    def native_value(self) -> float | None:
        slots = self.coordinator.effective(self.outage_group, self.now)
        return hours(slots, self._state) if slots is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        today = self.coordinator.today(self.now)
        if today is None:
            return {}
        first = self.coordinator.first.get(today.day, {}).get(self.outage_group)
        return {
            "revisions_today": self.coordinator.revisions.get(today.day, 0),
            "originally_scheduled_hours": hours(first, self._state) if first else None,
            "degraded": today.degraded,
        }


class ChangedSensor(GroupEntity, SensorEntity):
    """When today's schedule last changed, not when it was last re-stamped."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: OutageCoordinator, group: int) -> None:
        super().__init__(coordinator, group, "changed")

    @property
    def native_value(self) -> datetime | None:
        today = self.coordinator.today(self.now)
        return today.changed if today else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        today = self.coordinator.today(self.now)
        updated = today.updated if today else None
        return {"as_of": updated.isoformat() if updated else None}
