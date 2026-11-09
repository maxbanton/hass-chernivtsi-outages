"""Parsers against real pages and the formats the channel has used."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from custom_components.chernivtsi_outages.const import KYIV
from custom_components.chernivtsi_outages.model import Slot, encode
from custom_components.chernivtsi_outages.parsers import (
    LayoutError,
    parse_site,
    parse_telegram,
)

from .helpers import (
    codes,
    empty_site_page,
    fixture,
    image_text,
    quiet_text,
    schedule_text,
    site_page,
    telegram_page,
)

NOW = datetime(2026, 11, 3, 18, 49, tzinfo=KYIV)
DAY = date(2026, 11, 3)


def test_real_site_page() -> None:
    schedule, missing = parse_site(fixture("site_schedule.html"), NOW)
    assert missing == 0
    assert schedule.day == DAY
    assert schedule.updated == datetime(2026, 11, 3, 18, 30, tzinfo=KYIV)
    assert encode(schedule.groups[12]) == "u" * 35 + "oooo" + "s" + "u" * 8
    assert encode(schedule.groups[1]) == "u" * 30 + "ooooo" + "s" + "u" * 6 + "oooo" + "su"
    assert set(schedule.groups) == set(range(1, 13))


def test_site_without_table_means_no_schedule() -> None:
    assert parse_site(empty_site_page(), NOW) == (None, 0)


@pytest.mark.parametrize(
    "page",
    [
        "<html><title>Something else</title></html>",
        '<html><title>Відключення</title><div id="gsv">no date</div></html>',
        site_page(DAY, "18:30").replace('<div id="inf7"', '<div id="x7"'),
        site_page(DAY, "18:30", {3: ""}),
        site_page(DAY, "18:30", {3: ON_TOO_LONG}) if (ON_TOO_LONG := "u" * 49) else "",
    ],
)
def test_site_layout_errors(page: str) -> None:
    with pytest.raises(LayoutError):
        parse_site(page, NOW)


def test_site_trimmed_rows_line_up_with_the_end_of_the_day() -> None:
    rows = dict.fromkeys(range(1, 13), "u" * 10 + "o" * 10)
    schedule, missing = parse_site(site_page(DAY, "18:30", rows), NOW)
    assert missing == 28
    assert schedule.groups[5][:28] == (Slot.MAYBE,) * 28
    assert encode(schedule.groups[5][28:]) == "u" * 10 + "o" * 10


def test_site_stamp_of_tomorrows_page_is_the_evening_before() -> None:
    schedule, _ = parse_site(site_page(date(2026, 11, 4), "21:30"), NOW.replace(hour=21, minute=40))
    assert schedule.updated == datetime(2026, 11, 3, 21, 30, tzinfo=KYIV)


def test_site_without_stamp() -> None:
    schedule, _ = parse_site(site_page(DAY, "18:30").replace("станом на", "на"), NOW)
    assert schedule.updated is None


def test_real_channel_page() -> None:
    posts = parse_telegram(fixture("telegram_text.html"))
    assert [p.id for p in posts] == sorted(p.id for p in posts)
    last = posts[-1]
    assert last.id == 3950
    assert last.day == DAY
    assert last.outages
    site, _ = parse_site(fixture("site_schedule.html"), NOW)
    for group in range(1, 13):
        assert [s is Slot.ON for s in last.groups[group]] == [
            s is Slot.ON for s in site.groups[group]
        ]
    quiet = next(p for p in posts if p.id == 3939)
    assert (quiet.day, quiet.outages) == (date(2026, 10, 18), False)
    # Posted on 17.10 but dated 01.10: kept by the parser, rejected by the coordinator.
    assert any(p.day == date(2026, 10, 1) for p in posts)


def test_channel_formats() -> None:
    posted = datetime(2026, 11, 3, 20, 0, tzinfo=KYIV)
    tomorrow = date(2026, 11, 4)
    rows = {1: codes(off=(16, 20)), 2: codes(off=(40, 48)), 3: "o" * 48}
    page = telegram_page(
        [
            (10, posted, image_text(tomorrow)),
            (11, posted, quiet_text(tomorrow)),
            (12, posted, schedule_text(tomorrow, rows)),
            (13, posted, "Шановні абоненти! Передайте показники."),
            (14, posted, f"На {tomorrow:%d.%m.%Y} електропостачання без обмежень"),
        ]
    )
    image, quiet, text, inline = parse_telegram(page)
    assert (image.id, image.day, image.outages, image.groups) == (10, tomorrow, True, None)
    assert image.schedule() is None
    assert (quiet.outages, quiet.groups) == (False, None)
    assert quiet.schedule().active is False
    assert (inline.day, inline.outages) == (tomorrow, False)
    assert encode(text.groups[1]) == codes(off=(16, 20))
    assert encode(text.groups[2]) == codes(off=(40, 48))
    assert encode(text.groups[3]) == "o" * 48
    schedule = text.schedule()
    assert schedule.degraded and schedule.source == "telegram" and schedule.updated == posted


def test_channel_group_lines() -> None:
    posted = datetime(2026, 11, 3, 20, 0, tzinfo=KYIV)
    body = schedule_text(DAY)
    body = body.replace("💡 Група 4\nз 00:00", "💡 Група 4\nЕлектропостачання без обмежень")
    body = body.replace("💡 Група 5\nз 00:00", "💡 Група 5\nдо 08:00\n20:00 - 24:00")
    body = body.replace("💡 Група 6\nз 00:00", "💡 Група 6\n22:00 \u2013 00:00")
    (post,) = parse_telegram(telegram_page([(1, posted, body)]))
    assert encode(post.groups[4]) == "u" * 48
    assert encode(post.groups[5]) == "u" * 16 + "o" * 24 + "u" * 8
    assert encode(post.groups[6]) == "o" * 44 + "u" * 4


@pytest.mark.parametrize(
    ("find", "replace"),
    [
        ("💡 Група 7\nз 00:00", "💡 Група 7\nз 00:15"),
        ("💡 Група 7\nз 00:00", "💡 Група 7\nвідключено цілодобово"),
        ("💡 Група 7\nз 00:00", "💡 Група 7\n25:00 - 26:00"),
        ("💡 Група 12\nз 00:00", ""),
    ],
)
def test_channel_unreadable_groups_drop_the_hours(find: str, replace: str) -> None:
    posted = datetime(2026, 11, 3, 20, 0, tzinfo=KYIV)
    (post,) = parse_telegram(
        telegram_page([(1, posted, schedule_text(DAY).replace(find, replace))])
    )
    assert post.groups is None


def test_channel_skips_messages_without_text_or_time() -> None:
    page = (
        telegram_page([])
        + '<div data-post="oe_cv_ua/5"><div class="tgme_widget_message_photo"></div></div>'
    )
    assert parse_telegram(page.replace("<section", '<section class="tgme_widget_message"')) == []


def test_channel_layout_error() -> None:
    with pytest.raises(LayoutError):
        parse_telegram("<html>Telegram changed everything</html>")
