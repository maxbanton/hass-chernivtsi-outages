"""Event entity: the schedule was published or changed."""
from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OutageConfigEntry
from .coordinator import OutageCoordinator
from .entity import GroupEntity
from .model import CHANGE_KINDS

PARALLEL_UPDATES = 0

EVENT_TYPES = ["schedule_published", *CHANGE_KINDS, "schedule_changed"]


async def async_setup_entry(
    hass: HomeAssistant, entry: OutageConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(ScheduleChangeEvent(coordinator, group) for group in coordinator.groups)


class ScheduleChangeEvent(GroupEntity, EventEntity):
    _attr_event_types = EVENT_TYPES

    def __init__(self, coordinator: OutageCoordinator, group: int) -> None:
        super().__init__(coordinator, group, "change")
        self._seen = max((e.serial for e in coordinator.events.get(group, [])), default=0)

    @callback
    def _handle_coordinator_update(self) -> None:
        for event in self.coordinator.events_after(self.outage_group, self._seen):
            self._seen = event.serial
            self._trigger_event(event.kind, event.attributes)
            self.async_write_ha_state()
