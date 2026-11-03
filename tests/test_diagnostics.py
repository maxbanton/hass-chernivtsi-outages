"""Diagnostics and the User-Agent."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant

from custom_components.chernivtsi_outages import user_agent
from custom_components.chernivtsi_outages.const import SITE_URL, TELEGRAM_URL
from custom_components.chernivtsi_outages.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .common import kyiv, setup
from .helpers import FakeWeb, fixture


async def test_diagnostics(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, fixture("site_schedule.html"))
    web.set(TELEGRAM_URL, fixture("telegram_text.html"))
    entry = await setup(hass)
    report = await async_get_config_entry_diagnostics(hass, entry)
    assert report["groups"] == [12]
    assert report["site"]["errors"] == 0 and report["site"]["last_fetch"]
    assert report["telegram"]["last_post_id"] == 3950
    assert report["telegram"]["posts"][-1]["text_schedule"] is True
    day = report["days"]["2026-11-03"]
    assert day["source"] == "site" and day["groups"][12].startswith("u" * 35 + "oooo")


async def test_user_agent_names_the_project(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, fixture("site_schedule.html"))
    await setup(hass)
    agent = user_agent(hass)
    assert agent.startswith(f"HomeAssistant/{HA_VERSION} hass-chernivtsi-outages/")
    assert agent.endswith("(+https://github.com/maxbanton/hass-chernivtsi-outages)")
