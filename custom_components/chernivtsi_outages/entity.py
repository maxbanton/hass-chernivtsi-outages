"""Base entity: one device per outage group."""
from __future__ import annotations

from datetime import datetime

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SEARCH_URL
from .coordinator import OutageCoordinator
from .model import Period, Slot, current


def device_identifier(group: int) -> tuple[str, str]:
    return (DOMAIN, f"group_{group}")


class GroupEntity(CoordinatorEntity[OutageCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: OutageCoordinator, group: int, key: str) -> None:
        super().__init__(coordinator)
        self.outage_group = group
        self._attr_translation_key = key
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{group}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={device_identifier(group)},
            translation_key="group",
            translation_placeholders={"group": str(group)},
            manufacturer="oblenergo.cv.ua",
            model="Outage group",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=SEARCH_URL,
        )

    @property
    def now(self) -> datetime:
        return dt_util.now()

    @property
    def line(self) -> list[Period]:
        return self.coordinator.line(self.outage_group)

    @property
    def state_now(self) -> Slot | None:
        period = current(self.line, self.now)
        return period.state if period else None
