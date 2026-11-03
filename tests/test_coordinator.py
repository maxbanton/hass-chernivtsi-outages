"""When the site is fetched, what is kept, and how changes are reported."""

from __future__ import annotations

from datetime import date, timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from custom_components.chernivtsi_outages.api import FetchError
from custom_components.chernivtsi_outages.const import (
    DOMAIN,
    SITE_NEXT_URL,
    SITE_URL,
    SOURCE_SITE,
    SOURCE_TELEGRAM,
    TELEGRAM_URL,
)
from custom_components.chernivtsi_outages.coordinator import OutageCoordinator
from custom_components.chernivtsi_outages.model import encode

from .common import DAY, TOMORROW, advance, cycles, kyiv, setup
from .helpers import (
    FakeWeb,
    codes,
    empty_site_page,
    fixture,
    image_text,
    quiet_text,
    schedule_text,
    site_page,
    telegram_page,
)

EVENT = "event.outage_group_12_schedule_change"
A = {12: codes(off=(40, 44))}
B = {12: codes(off=(39, 44))}


def channel(*posts: tuple[int, int, int, date, dict[int, str] | None]) -> str:
    """Posts as (id, hour, minute, day, rows); rows None posts "no outages"."""
    return telegram_page(
        [
            (pid, kyiv(h, m), schedule_text(day, rows) if rows is not None else quiet_text(day))
            for pid, h, m, day, rows in posts
        ]
    )


async def test_first_refresh_reads_both_and_then_only_the_channel(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, fixture("site_schedule.html"))
    web.set(TELEGRAM_URL, fixture("telegram_text.html"))
    entry = await setup(hass)
    c: OutageCoordinator = entry.runtime_data
    assert (web.count(SITE_URL), web.count(TELEGRAM_URL)) == (1, 1)
    assert c.last_post_id == 3950
    assert c.days[DAY].source == SOURCE_SITE
    assert c.events == {}
    assert all(post.day != date(2026, 10, 1) for post in c.posts)

    await advance(hass, freezer)
    assert (web.count(SITE_URL), web.count(TELEGRAM_URL)) == (1, 2)
    # Safety fetch once an hour while outages are scheduled.
    await cycles(hass, freezer, 11)
    assert web.count(SITE_URL) == 2


async def test_new_post_fetches_the_site_and_reports_the_change(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, site_page(DAY, "18:30", A))
    web.set(TELEGRAM_URL, channel((100, 18, 30, DAY, A)))
    entry = await setup(hass)
    assert hass.states.get(EVENT).state == "unknown"

    web.set(SITE_URL, site_page(DAY, "19:00", B))
    web.set(TELEGRAM_URL, channel((100, 18, 30, DAY, A), (101, 18, 52, DAY, B)))
    await advance(hass, freezer)
    assert web.count(SITE_URL) == 2
    state = hass.states.get(EVENT)
    assert state.attributes["event_type"] == "outage_earlier"
    assert state.attributes["date"] == "2026-11-03"
    assert state.attributes["changes"][0]["start"] == kyiv(19, 30).isoformat()
    assert entry.runtime_data.revisions[DAY] == 1

    # Agreeing with the post, the page is not asked again.
    await advance(hass, freezer)
    assert web.count(SITE_URL) == 2


async def test_site_lagging_the_post_is_asked_a_bounded_number_of_times(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, site_page(DAY, "18:30", A))
    web.set(TELEGRAM_URL, channel((100, 18, 30, DAY, A)))
    await setup(hass)
    web.set(TELEGRAM_URL, channel((100, 18, 30, DAY, A), (101, 18, 52, DAY, B)))
    await cycles(hass, freezer, 4)
    assert web.count(SITE_URL) == 4


async def test_tomorrow_comes_from_the_channel_until_the_site_has_it(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(20, 0))
    web.set(SITE_URL, site_page(DAY, "18:30", A))
    web.set(SITE_NEXT_URL, site_page(DAY, "18:30", A))
    web.set(TELEGRAM_URL, channel((100, 18, 30, DAY, A)))
    entry = await setup(hass)
    c: OutageCoordinator = entry.runtime_data

    rows = {12: codes(off=(16, 20))}
    web.set(TELEGRAM_URL, channel((100, 18, 30, DAY, A), (101, 20, 3, TOMORROW, rows)))
    await advance(hass, freezer)
    assert c.days[TOMORROW].source == SOURCE_TELEGRAM and c.days[TOMORROW].degraded
    assert hass.states.get(EVENT).attributes["event_type"] == "schedule_published"
    await cycles(hass, freezer, 4)
    assert web.count(SITE_NEXT_URL) == 3

    # The site's version with a possible-outage slot replaces it without news.
    web.set(SITE_NEXT_URL, site_page(TOMORROW, "20:30", {12: codes(off=(16, 19), maybe=19)}))
    web.set(
        TELEGRAM_URL,
        channel((100, 18, 30, DAY, A), (101, 20, 3, TOMORROW, rows), (102, 20, 35, TOMORROW, rows)),
    )
    fired = hass.states.get(EVENT).last_changed
    await advance(hass, freezer)
    assert c.days[TOMORROW].source == SOURCE_SITE
    assert encode(c.days[TOMORROW].groups[12])[16:21] == "ooosu"
    assert hass.states.get(EVENT).last_changed == fired


async def test_no_outages_slows_the_safety_fetch(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(10, 0))
    web.set(SITE_URL, empty_site_page())
    entry = await setup(hass)
    c: OutageCoordinator = entry.runtime_data
    assert c.days[DAY].active is False
    await advance(hass, freezer, timedelta(hours=5))
    assert web.count(SITE_URL) == 1
    await advance(hass, freezer, timedelta(hours=1, minutes=1))
    assert web.count(SITE_URL) == 2


async def test_missing_table_after_a_day_with_outages_is_unknown(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(23, 50))
    web.set(SITE_URL, site_page(DAY, "18:30", A))
    entry = await setup(hass)
    c: OutageCoordinator = entry.runtime_data

    web.set(SITE_URL, empty_site_page())
    await advance(hass, freezer, timedelta(hours=1, minutes=1))
    assert web.count(SITE_URL) == 2
    assert TOMORROW not in c.days
    assert hass.states.get("sensor.outage_group_12_schedule_now").state == "unknown"

    web.set(TELEGRAM_URL, channel((200, 0, 55, TOMORROW, None)))
    await advance(hass, freezer)
    assert c.days[TOMORROW].active is False
    assert hass.states.get("sensor.outage_group_12_schedule_now").state == "on"


async def test_site_failures_back_off_and_the_channel_fills_in(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, site_page(DAY, "18:30", A))
    web.set(TELEGRAM_URL, channel((100, 18, 30, DAY, A)))
    entry = await setup(hass)
    c: OutageCoordinator = entry.runtime_data

    web.set(SITE_URL, FetchError("HTTP 503"))
    web.set(TELEGRAM_URL, channel((100, 18, 30, DAY, A), (101, 18, 52, DAY, B)))
    await advance(hass, freezer)
    assert (web.count(SITE_URL), c.site_errors) == (2, 1)
    assert c.days[DAY].source == SOURCE_TELEGRAM
    assert hass.states.get(EVENT).attributes["event_type"] == "outage_earlier"

    await advance(hass, freezer)
    assert (web.count(SITE_URL), c.site_errors) == (3, 2)
    await advance(hass, freezer)
    assert web.count(SITE_URL) == 3

    web.set(SITE_URL, FetchError("HTTP 429", retry_after=3600))
    await advance(hass, freezer, timedelta(minutes=6))
    assert web.count(SITE_URL) == 4
    await advance(hass, freezer, timedelta(minutes=50))
    assert web.count(SITE_URL) == 4

    web.set(SITE_URL, site_page(DAY, "19:00", B))
    await advance(hass, freezer, timedelta(minutes=11))
    assert (web.count(SITE_URL), c.site_errors) == (5, 0)
    assert c.days[DAY].source == SOURCE_SITE


async def test_layout_changes_raise_repair_issues(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, "<html>new site</html>")
    web.set(TELEGRAM_URL, fixture("telegram_text.html"))
    entry = await setup(hass)
    issues = ir.async_get(hass)
    assert issues.async_get_issue(DOMAIN, "site_layout")
    assert entry.runtime_data.days[DAY].source == SOURCE_TELEGRAM

    web.set(SITE_URL, fixture("site_schedule.html"))
    web.set(TELEGRAM_URL, "<html>new telegram</html>")
    await advance(hass, freezer, timedelta(minutes=6))
    assert issues.async_get_issue(DOMAIN, "site_layout") is None
    assert issues.async_get_issue(DOMAIN, "telegram_layout")
    assert entry.runtime_data.telegram_ok is False

    # Without the channel the page is checked every 30 minutes.
    calls = web.count(SITE_URL)
    await cycles(hass, freezer, 6)
    assert web.count(SITE_URL) == calls + 1

    web.set(TELEGRAM_URL, fixture("telegram_text.html"))
    await advance(hass, freezer)
    assert issues.async_get_issue(DOMAIN, "telegram_layout") is None
    assert entry.runtime_data.telegram_ok


async def test_unreachable_channel_is_not_a_layout_issue(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, fixture("site_schedule.html"))
    web.set(TELEGRAM_URL, FetchError("timeout"))
    entry = await setup(hass)
    assert entry.runtime_data.telegram_ok is False
    assert ir.async_get(hass).async_get_issue(DOMAIN, "telegram_layout") is None


async def test_setup_retries_when_both_sources_fail(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, FetchError("down"))
    web.set(TELEGRAM_URL, FetchError("down"))
    entry = await setup(hass)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_passed_slots_keep_their_hours(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(13, 1))
    morning = {12: codes(off=(20, 24))}
    web.set(SITE_URL, site_page(DAY, "13:00", morning))
    web.set(TELEGRAM_URL, channel((100, 9, 0, DAY, morning)))
    await setup(hass)
    hours = "sensor.outage_group_12_scheduled_outage_hours_today"
    assert hass.states.get(hours).state == "2.0"

    web.set(SITE_URL, site_page(DAY, "13:05", {12: codes(off=(36, 38))}))
    web.set(
        TELEGRAM_URL,
        channel((100, 9, 0, DAY, morning), (101, 13, 4, DAY, {12: codes(off=(36, 38))})),
    )
    await advance(hass, freezer)
    state = hass.states.get(hours)
    assert state.state == "3.0"
    assert state.attributes["revisions_today"] == 1
    assert state.attributes["originally_scheduled_hours"] == 2.0
    assert hass.states.get(EVENT).attributes["event_type"] == "outage_added"


async def test_trimmed_page_keeps_known_past_slots(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, site_page(DAY, "18:30", {12: codes(off=(2, 4))}))
    web.set(TELEGRAM_URL, channel((100, 18, 30, DAY, {12: codes(off=(2, 4))})))
    entry = await setup(hass)
    rows = {g: codes(off=(2, 4))[37:] for g in range(1, 13)}
    web.set(SITE_URL, site_page(DAY, "19:00", rows))
    await advance(hass, freezer, timedelta(hours=1, minutes=1))
    assert encode(entry.runtime_data.days[DAY].groups[12])[:6] == "uuoouu"


async def test_restart_restores_what_was_known(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, fixture("site_schedule.html"))
    web.set(TELEGRAM_URL, fixture("telegram_text.html"))
    entry = await setup(hass)
    c: OutageCoordinator = entry.runtime_data
    await advance(hass, freezer, timedelta(minutes=31))
    saved = c._serialize()

    restored = OutageCoordinator(hass, entry, c.client, [12])
    restored._store.async_load = _returns(saved)
    await restored.async_load()
    assert restored.days[DAY].groups == c.days[DAY].groups
    assert restored.days[DAY].updated == c.days[DAY].updated
    assert restored.frozen[DAY][12][:37] == c.frozen[DAY][12][:37]
    assert restored.last_post_id == 3950
    assert restored.last_site == c.last_site

    # Days older than yesterday are dropped.
    freezer.move_to(kyiv(1, 0, DAY + timedelta(days=3)))
    restored = OutageCoordinator(hass, entry, c.client, [12])
    restored._store.async_load = _returns(saved)
    await restored.async_load()
    assert restored.days == {}


def _returns(value):
    async def load():
        return value

    return load


async def test_picture_posts_trigger_a_fetch_but_carry_no_hours(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, site_page(DAY, "18:30", A))
    web.set(TELEGRAM_URL, channel((100, 18, 30, DAY, A)))
    entry = await setup(hass)
    web.set(SITE_URL, FetchError("HTTP 502"))
    web.set(
        TELEGRAM_URL,
        telegram_page(
            [(100, kyiv(18, 30), schedule_text(DAY, A)), (101, kyiv(18, 52), image_text(DAY))]
        ),
    )
    await advance(hass, freezer)
    assert web.count(SITE_URL) == 2
    assert entry.runtime_data.days[DAY].source == SOURCE_SITE
    assert encode(entry.runtime_data.days[DAY].groups[12]) == A[12]


async def test_an_unconfirmed_post_is_dropped_at_midnight(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(23, 49))
    web.set(SITE_URL, site_page(DAY, "23:30", A))
    web.set(TELEGRAM_URL, channel((100, 23, 30, DAY, A)))
    await setup(hass)
    web.set(TELEGRAM_URL, channel((100, 23, 30, DAY, A), (101, 23, 52, DAY, B)))
    await advance(hass, freezer)
    assert web.count(SITE_URL) == 2
    await advance(hass, freezer, timedelta(minutes=10))
    assert web.count(SITE_URL) == 2


async def test_changed_at_follows_content_not_the_site_stamp(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, site_page(DAY, "18:30", A))
    web.set(TELEGRAM_URL, channel((100, 18, 20, DAY, A)))
    entry = await setup(hass)
    c: OutageCoordinator = entry.runtime_data
    assert c.days[DAY].changed == kyiv(18, 20)

    # Re-stamped without changes: same version.
    web.set(SITE_URL, site_page(DAY, "19:30", A))
    await advance(hass, freezer, timedelta(hours=1, minutes=1))
    assert c.days[DAY].updated == kyiv(19, 30)
    assert c.days[DAY].changed == kyiv(18, 20)

    # A revision announced by a post takes the post's time.
    web.set(SITE_URL, site_page(DAY, "20:00", B))
    web.set(TELEGRAM_URL, channel((100, 18, 20, DAY, A), (101, 19, 55, DAY, B)))
    await advance(hass, freezer)
    assert c.days[DAY].changed == kyiv(19, 55)

    # A revision no post describes takes the site's time.
    web.set(SITE_URL, site_page(DAY, "21:00", {12: codes(off=(42, 46))}))
    await advance(hass, freezer, timedelta(hours=1, minutes=1))
    assert c.days[DAY].changed == kyiv(21, 0)


async def test_changed_at_of_a_quiet_day_is_its_post(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(10, 0))
    web.set(SITE_URL, empty_site_page())
    web.set(TELEGRAM_URL, channel((300, 9, 0, DAY, None), (301, 9, 5, TOMORROW, A)))
    entry = await setup(hass)
    assert entry.runtime_data.days[DAY].changed == kyiv(9, 0)
    assert entry.runtime_data.days[TOMORROW].changed == kyiv(9, 5)


async def test_changed_at_falls_back_to_the_fetch_time(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(10, 0))
    web.set(SITE_URL, site_page(DAY, "09:30", A).replace("станом на", "на"))
    entry = await setup(hass)
    assert entry.runtime_data.days[DAY].changed == kyiv(10, 0)
