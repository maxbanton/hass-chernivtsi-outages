"""Data update coordinator for Chernivtsi power schedule."""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PowerScheduleApiClient, ScheduleData
from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class PowerScheduleCoordinator(DataUpdateCoordinator[ScheduleData]):
    """Class to manage fetching power schedule data."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        group: int | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=DEFAULT_UPDATE_INTERVAL),
        )
        self.api = PowerScheduleApiClient(session)
        self.group = group

    async def _async_update_data(self) -> ScheduleData:
        """Fetch data from API."""
        try:
            return await self.api.async_get_schedule()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
