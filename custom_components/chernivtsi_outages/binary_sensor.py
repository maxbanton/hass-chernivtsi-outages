"""Binary sensor: an outage is scheduled right now."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OutageConfigEntry
from .coordinator import OutageCoordinator
from .entity import GroupEntity
from .model import Slot

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: OutageConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(OutageBinarySensor(coordinator, group) for group in coordinator.groups)


class OutageBinarySensor(GroupEntity, BinarySensorEntity):
    """On during scheduled outages; possible outages are not outages."""

    def __init__(self, coordinator: OutageCoordinator, group: int) -> None:
        super().__init__(coordinator, group, "outage")

    @property
    def is_on(self) -> bool | None:
        state = self.state_now
        return None if state is None else state is Slot.OFF
