"""Sensor platform for Chernivtsi Power Schedule."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ATTRIBUTION,
    STATE_ON,
    STATE_OFF,
    STATE_TRANSLATIONS,
    CONF_GROUP,
)
from .coordinator import PowerScheduleCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up power schedule sensors from config entry."""
    coordinator: PowerScheduleCoordinator = hass.data[DOMAIN][entry.entry_id]
    group = entry.data.get(CONF_GROUP)

    # Create sensors for the configured group
    entities = [
        PowerStateSensor(coordinator, group, entry),
        NextChangeSensor(coordinator, group, entry),
        OffHoursRemainingSensor(coordinator, group, entry),
        OnHoursRemainingSensor(coordinator, group, entry),
        ScheduleSensor(coordinator, group, entry),
    ]

    async_add_entities(entities)


class PowerScheduleBaseSensor(CoordinatorEntity[PowerScheduleCoordinator], SensorEntity):
    """Base class for power schedule sensors."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PowerScheduleCoordinator,
        group: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._group = group
        self._entry = entry

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}")},
            name="CV",
            manufacturer="Chernivtsi Region",
            model=f"Group {group}",
        )

    @property
    def group_schedule(self):
        """Get the schedule for this group."""
        if self.coordinator.data:
            return self.coordinator.data.get_group(self._group)
        return None


class PowerStateSensor(PowerScheduleBaseSensor):
    """Sensor showing current power state."""

    _attr_icon = "mdi:transmission-tower"

    def __init__(
        self,
        coordinator: PowerScheduleCoordinator,
        group: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, group, entry)
        self._attr_unique_id = f"{entry.entry_id}_power_state"
        self._attr_translation_key = "power_state"
        self._attr_name = "Power State"

    @property
    def native_value(self) -> str | None:
        """Return the current state."""
        schedule = self.group_schedule
        if schedule:
            return schedule.get_current_state()
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        schedule = self.group_schedule
        if not schedule:
            return {}

        attrs = {
            "group": self._group,
            "schedule_date": schedule.date.isoformat(),
            "state_text": STATE_TRANSLATIONS.get(self.native_value, "Unknown"),
        }

        # Add current slot info
        current_slot = schedule.get_current_slot()
        if current_slot:
            attrs["current_slot"] = current_slot.time_str

        return attrs

    @property
    def icon(self) -> str:
        """Return dynamic icon based on state."""
        state = self.native_value
        if state == STATE_ON:
            return "mdi:transmission-tower"
        elif state == STATE_OFF:
            return "mdi:transmission-tower-off"
        else:
            return "mdi:transmission-tower-import"


class NextChangeSensor(PowerScheduleBaseSensor):
    """Sensor showing next state change time."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-outline"

    def __init__(
        self,
        coordinator: PowerScheduleCoordinator,
        group: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, group, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_change"
        self._attr_name = "Next Change"

    @property
    def native_value(self) -> datetime | None:
        """Return the next change time."""
        schedule = self.group_schedule
        if schedule:
            next_change = schedule.get_next_change()
            if next_change:
                slot, state = next_change
                # Create datetime for today at the slot time
                now = datetime.now()
                return now.replace(
                    hour=slot.hour,
                    minute=slot.minute,
                    second=0,
                    microsecond=0,
                )
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        schedule = self.group_schedule
        if not schedule:
            return {}

        attrs = {"group": self._group}

        next_change = schedule.get_next_change()
        if next_change:
            slot, state = next_change
            attrs["next_state"] = state
            attrs["next_state_text"] = STATE_TRANSLATIONS.get(state, "Unknown")

        return attrs


class OffHoursRemainingSensor(PowerScheduleBaseSensor):
    """Sensor showing remaining off hours today."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "h"
    _attr_icon = "mdi:timer-off-outline"

    def __init__(
        self,
        coordinator: PowerScheduleCoordinator,
        group: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, group, entry)
        self._attr_unique_id = f"{entry.entry_id}_off_hours"
        self._attr_name = "Off Hours Remaining"

    @property
    def native_value(self) -> float | None:
        """Return remaining off hours."""
        schedule = self.group_schedule
        if schedule:
            return schedule.count_off_hours_remaining()
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        schedule = self.group_schedule
        if not schedule:
            return {}

        return {
            "group": self._group,
            "off_periods": schedule.get_off_periods(),
        }


class OnHoursRemainingSensor(PowerScheduleBaseSensor):
    """Sensor showing remaining on hours today."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "h"
    _attr_icon = "mdi:timer-outline"

    def __init__(
        self,
        coordinator: PowerScheduleCoordinator,
        group: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, group, entry)
        self._attr_unique_id = f"{entry.entry_id}_on_hours"
        self._attr_name = "On Hours Remaining"

    @property
    def native_value(self) -> float | None:
        """Return remaining on hours."""
        schedule = self.group_schedule
        if schedule:
            return schedule.count_on_hours_remaining()
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        schedule = self.group_schedule
        if not schedule:
            return {}

        return {
            "group": self._group,
            "on_periods": schedule.get_on_periods(),
        }


class ScheduleSensor(PowerScheduleBaseSensor):
    """Sensor showing full schedule as JSON."""

    _attr_icon = "mdi:calendar-clock"

    def __init__(
        self,
        coordinator: PowerScheduleCoordinator,
        group: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, group, entry)
        self._attr_unique_id = f"{entry.entry_id}_schedule"
        self._attr_name = "Schedule"

    @property
    def native_value(self) -> str | None:
        """Return schedule date."""
        schedule = self.group_schedule
        if schedule:
            return schedule.date.isoformat()
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return full schedule as attributes."""
        schedule = self.group_schedule
        if not schedule:
            return {}

        # Create hourly schedule dict
        hourly = {}
        for slot in schedule.slots:
            hourly[slot.time_str] = slot.state

        return {
            "group": self._group,
            "schedule_date": schedule.date.isoformat(),
            "schedule": hourly,
            "off_periods": schedule.get_off_periods(),
            "on_periods": schedule.get_on_periods(),
            "total_off_hours": sum(1 for s in schedule.slots if s.state == STATE_OFF) * 0.5,
            "total_on_hours": sum(1 for s in schedule.slots if s.state == STATE_ON) * 0.5,
        }
