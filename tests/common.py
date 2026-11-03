"""Setting up the integration and moving time in tests."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.chernivtsi_outages.const import CONF_GROUPS, DOMAIN, KYIV

DAY = date(2026, 11, 3)
TOMORROW = DAY + timedelta(days=1)
CYCLE = timedelta(minutes=5, seconds=1)


def kyiv(hour: int, minute: int = 0, day: date = DAY) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=KYIV)


async def setup(hass: HomeAssistant, groups: list[int] | None = None) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_GROUPS: groups or [12]}, title="Chernivtsi Power Outages"
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def advance(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, delta: timedelta = CYCLE
) -> None:
    freezer.tick(delta)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def cycles(hass: HomeAssistant, freezer: FrozenDateTimeFactory, count: int) -> None:
    for _ in range(count):
        await advance(hass, freezer)
