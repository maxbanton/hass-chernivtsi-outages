"""Binary sensor platform for Chernivtsi Power Schedule."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
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
    """Set up power schedule binary sensors from config entry."""
    coordinator: PowerScheduleCoordinator = hass.data[DOMAIN][entry.entry_id]
    group = entry.data.get(CONF_GROUP)

    # Create binary sensor for the configured group
    async_add_entities([PowerConnectivitySensor(coordinator, group, entry)])


class PowerConnectivitySensor(
    CoordinatorEntity[PowerScheduleCoordinator],
    BinarySensorEntity
):
    """Binary sensor showing if power is ON."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.POWER

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

        self._attr_unique_id = f"{entry.entry_id}_power"
        self._attr_name = "Power"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}")},
            name="CV",
            manufacturer="Chernivtsi Region",
            model=f"Group {group}",
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if power is on."""
        if self.coordinator.data:
            schedule = self.coordinator.data.get_group(self._group)
            if schedule:
                state = schedule.get_current_state()
                # ON or MAYBE = True, OFF = False
                return state != STATE_OFF
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}

        schedule = self.coordinator.data.get_group(self._group)
        if not schedule:
            return {}

        state = schedule.get_current_state()

        attrs = {
            "group": self._group,
            "state": state,
            "state_text": STATE_TRANSLATIONS.get(state, "Unknown"),
            "schedule_date": schedule.date.isoformat(),
        }

        # Add next change info
        next_change = schedule.get_next_change()
        if next_change:
            slot, next_state = next_change
            attrs["next_change"] = slot.time_str
            attrs["next_state"] = next_state

        return attrs

    @property
    def icon(self) -> str:
        """Return icon based on state."""
        if self.is_on:
            return "mdi:power-plug"
        return "mdi:power-plug-off"
