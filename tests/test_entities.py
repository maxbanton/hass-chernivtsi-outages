"""Entity states for a real published day, across slot edges and days."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.chernivtsi_outages.const import (
    CONF_GROUPS,
    DOMAIN,
    SITE_URL,
    TELEGRAM_URL,
)
from custom_components.chernivtsi_outages.entity import device_identifier

from .common import DAY, TOMORROW, advance, kyiv, setup
from .helpers import FakeWeb, codes, fixture, site_page

SENSOR = "sensor.outage_group_12_"


def state(hass: HomeAssistant, entity_id: str):
    return hass.states.get(entity_id)


async def _real_day(hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory):
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, fixture("site_schedule.html"))
    web.set(TELEGRAM_URL, fixture("telegram_text.html"))
    return await setup(hass)


async def test_states_during_an_outage(
    hass: HomeAssistant,
    web: FakeWeb,
    freezer: FrozenDateTimeFactory,
    entity_registry_enabled_by_default: None,
) -> None:
    await _real_day(hass, web, freezer)
    schedule = state(hass, f"{SENSOR}schedule_now")
    assert schedule.state == "off"
    assert schedule.attributes["options"] == ["on", "off", "maybe"]
    assert schedule.attributes["schedule_active"] is True
    assert schedule.attributes["source"] == "site"
    assert schedule.attributes["today"][1] == {"start": "17:30", "end": "19:30", "state": "off"}
    assert schedule.attributes["today"][-1] == {"start": "20:00", "end": "24:00", "state": "on"}
    assert schedule.attributes["tomorrow"] is None
    assert state(hass, "binary_sensor.outage_group_12_scheduled_power").state == "off"
    assert state(hass, f"{SENSOR}expected_next_outage").state == "unknown"
    back = state(hass, f"{SENSOR}power_expected_back")
    assert back.state == "2026-11-03T17:30:00+00:00"
    assert back.attributes["then"] == "maybe"
    assert state(hass, f"{SENSOR}scheduled_outage_hours_today").state == "2.0"
    assert state(hass, f"{SENSOR}possible_outage_hours_today").state == "0.5"
    # Published by post 3950 at 18:33; the site re-stamps it every 30 minutes.
    changed = state(hass, f"{SENSOR}last_schedule_change")
    assert changed.state == "2026-11-03T16:33:52+00:00"
    assert changed.attributes["as_of"] == "2026-11-03T18:30:00+02:00"


async def test_states_change_at_slot_edges_without_fetching(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    await _real_day(hass, web, freezer)
    site_calls = web.count(SITE_URL)
    freezer.move_to(kyiv(19, 30))
    await advance(hass, freezer, timedelta(seconds=0))
    assert state(hass, f"{SENSOR}schedule_now").state == "maybe"
    assert state(hass, "binary_sensor.outage_group_12_scheduled_power").state == "off"
    assert state(hass, f"{SENSOR}power_expected_back").state == "unknown"
    assert web.count(SITE_URL) == site_calls
    freezer.move_to(kyiv(20))
    await advance(hass, freezer, timedelta(seconds=0))
    assert state(hass, f"{SENSOR}schedule_now").state == "on"
    assert state(hass, "binary_sensor.outage_group_12_scheduled_power").state == "on"


async def test_next_outage_and_its_end(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(10, 0))
    web.set(SITE_URL, site_page(DAY, "09:30", {12: codes(off=(36, 40), maybe=40)}))
    await setup(hass)
    nxt = state(hass, f"{SENSOR}expected_next_outage")
    assert nxt.state == "2026-11-03T16:00:00+00:00"
    assert nxt.attributes == {
        **nxt.attributes,
        "end": kyiv(20, 0).isoformat(),
        "duration_hours": 2.0,
    }
    assert state(hass, f"{SENSOR}power_expected_back").state == "2026-11-03T18:00:00+00:00"


async def test_outage_running_into_an_unpublished_day_has_no_end(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(10, 0))
    web.set(SITE_URL, site_page(DAY, "09:30", {12: codes(off=(44, 48))}))
    await setup(hass)
    nxt = state(hass, f"{SENSOR}expected_next_outage")
    assert nxt.state == "2026-11-03T20:00:00+00:00"
    assert nxt.attributes["end"] is None and nxt.attributes["duration_hours"] is None
    assert state(hass, f"{SENSOR}power_expected_back").state == "unknown"


async def test_possible_outage_hours_disabled_by_default(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    await _real_day(hass, web, freezer)
    entry = er.async_get(hass).async_get(f"{SENSOR}possible_outage_hours_today")
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert state(hass, f"{SENSOR}possible_outage_hours_today") is None
    assert state(hass, f"{SENSOR}scheduled_outage_hours_today") is not None


async def test_unknown_day_leaves_states_unknown(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    await _real_day(hass, web, freezer)
    freezer.move_to(kyiv(0, 10, TOMORROW))
    await advance(hass, freezer, timedelta(seconds=0))
    for key in ("schedule_now", "scheduled_outage_hours_today", "last_schedule_change"):
        assert state(hass, f"{SENSOR}{key}").state == "unknown"
    assert state(hass, "binary_sensor.outage_group_12_scheduled_power").state == "unknown"
    hours = state(hass, f"{SENSOR}scheduled_outage_hours_today")
    assert hours.attributes.get("revisions_today") is None


async def test_calendar(hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory) -> None:
    await _real_day(hass, web, freezer)
    calendar = state(hass, "calendar.outage_group_12_scheduled_outages")
    assert calendar.state == "on"
    assert calendar.attributes["message"] == "Outage"
    result = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": "calendar.outage_group_12_scheduled_outages",
            "start_date_time": kyiv(0).isoformat(),
            "end_date_time": kyiv(23, 59).isoformat(),
        },
        blocking=True,
        return_response=True,
    )
    events = result["calendar.outage_group_12_scheduled_outages"]["events"]
    assert [(e["summary"], e["start"][11:16], e["end"][11:16]) for e in events] == [
        ("Outage", "17:30", "19:30"),
        ("Possibly powered", "19:30", "20:00"),
    ]


async def test_calendar_titles_follow_the_server_language(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    hass.config.language = "uk"
    entry = await _real_day(hass, web, freezer)
    entity_id = er.async_get(hass).async_get_entity_id(
        "calendar", DOMAIN, f"{entry.entry_id}_12_outages"
    )
    assert state(hass, entity_id).attributes["message"] == "Відключено"


async def test_changing_groups_adds_and_removes_devices(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    entry = await _real_day(hass, web, freezer)
    devices = dr.async_get(hass)
    hass.config_entries.async_update_entry(entry, options={CONF_GROUPS: [1, 12]})
    await hass.async_block_till_done()
    assert state(hass, "sensor.outage_group_1_schedule_now").state == "on"
    assert devices.async_get_device({device_identifier(1)})

    hass.config_entries.async_update_entry(entry, options={CONF_GROUPS: [1]})
    await hass.async_block_till_done()
    assert devices.async_get_device({device_identifier(12)}) is None
    device = devices.async_get_device({device_identifier(1)})
    assert device.configuration_url == "https://oblenergo.cv.ua/shutdowns/"


async def test_unload_and_remove(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory, hass_storage
) -> None:
    entry = await _real_day(hass, web, freezer)
    await advance(hass, freezer, timedelta(seconds=30))
    assert f"{DOMAIN}.{entry.entry_id}" in hass_storage
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert f"{DOMAIN}.{entry.entry_id}" not in hass_storage
