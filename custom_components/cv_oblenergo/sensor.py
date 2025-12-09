"""Sensor platform for Chernivtsi Power Schedule."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ATTRIBUTION,
    STATE_OFF,
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

    entities = [
        PowerStateSensor(coordinator, group, entry),
        NextOnSensor(coordinator, group, entry),
        NextOffSensor(coordinator, group, entry),
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
            name="CV Power",
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
    """Sensor showing current power state (on/off, maybe treated as on)."""

    def __init__(
        self,
        coordinator: PowerScheduleCoordinator,
        group: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, group, entry)
        self._attr_unique_id = f"{entry.entry_id}_state"
        self._attr_name = "State"

    @property
    def native_value(self) -> str | None:
        """Return the current state (on/off, maybe treated as on)."""
        schedule = self.group_schedule
        if schedule:
            state = schedule.get_current_state()
            # Treat "maybe" as "on"
            return "off" if state == STATE_OFF else "on"
        return None

    @property
    def icon(self) -> str:
        """Return dynamic icon based on state."""
        if self.native_value == "off":
            return "mdi:flash-off"
        return "mdi:flash"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        schedule = self.group_schedule
        if not schedule:
            return {}

        # Count total hours (maybe is treated as on)
        on_slots = sum(1 for s in schedule.slots if s.state != STATE_OFF)
        off_slots = sum(1 for s in schedule.slots if s.state == STATE_OFF)

        return {
            "schedule_date": schedule.date.isoformat(),
            "group": self._group,
            "hours_with_power": on_slots * 0.5,
            "hours_without_power": off_slots * 0.5,
        }


class NextOnSensor(PowerScheduleBaseSensor):
    """Sensor showing next turn ON time."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:flash"

    def __init__(
        self,
        coordinator: PowerScheduleCoordinator,
        group: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, group, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_on"
        self._attr_name = "Next ON"

    @property
    def native_value(self) -> datetime | None:
        """Return the next ON time."""
        schedule = self.group_schedule
        if schedule:
            # Get next slot that is not OFF (on or maybe = on)
            next_on = schedule.get_next_on_or_maybe()
            if next_on:
                now = datetime.now()
                return now.replace(
                    hour=next_on.hour,
                    minute=next_on.minute,
                    second=0,
                    microsecond=0,
                )
        return None


class NextOffSensor(PowerScheduleBaseSensor):
    """Sensor showing next turn OFF time."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:flash-off"

    def __init__(
        self,
        coordinator: PowerScheduleCoordinator,
        group: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, group, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_off"
        self._attr_name = "Next OFF"

    @property
    def native_value(self) -> datetime | None:
        """Return the next OFF time."""
        schedule = self.group_schedule
        if schedule:
            next_off = schedule.get_next_off()
            if next_off:
                now = datetime.now()
                return now.replace(
                    hour=next_off.hour,
                    minute=next_off.minute,
                    second=0,
                    microsecond=0,
                )
        return None
