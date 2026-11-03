"""Slots, periods and how outages changed."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from custom_components.chernivtsi_outages.const import KYIV
from custom_components.chernivtsi_outages.model import (
    SLOTS,
    DaySchedule,
    Slot,
    current,
    decode,
    diff,
    encode,
    hours,
    next_outage,
    outage_end,
    periods,
    slot_at,
    slot_start,
    timeline,
)

from .helpers import codes

DAY = date(2026, 11, 3)


def at(hour: int, minute: int = 0, day: date = DAY) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=KYIV)


def test_codes_round_trip() -> None:
    row = codes(off=(2, 6), maybe=6)
    assert encode(decode(row)) == row


def test_slot_times() -> None:
    assert slot_start(DAY, 0) == at(0)
    assert slot_start(DAY, 37) == at(18, 30)
    assert slot_start(DAY, SLOTS) == at(0, day=DAY + timedelta(days=1))
    assert slot_at(at(18, 49)) == (DAY, 37)
    assert slot_at(datetime(2026, 11, 3, 22, 10, tzinfo=KYIV).astimezone(KYIV)) == (DAY, 44)


def test_daylight_saving_day_keeps_wall_clock_slots() -> None:
    spring = date(2026, 3, 29)
    assert slot_start(spring, 8).hour == 4
    night = periods(spring, decode("o" * 8 + "u" * 40))[0]
    assert night.hours == 3


def test_periods_and_timeline_across_midnight() -> None:
    today = decode(codes(off=(44, 48)))
    tomorrow = decode(codes(off=(0, 4), maybe=4))
    assert [p.state for p in periods(DAY, today)] == [Slot.ON, Slot.OFF]
    line = timeline({DAY: today, DAY + timedelta(days=1): tomorrow})
    outage = line[1]
    assert (outage.start, outage.end, outage.hours) == (
        at(22),
        at(2, day=DAY + timedelta(days=1)),
        4,
    )
    assert line[2].state is Slot.MAYBE


def test_next_outage_skips_the_one_in_progress() -> None:
    line = timeline({DAY: decode(codes(off=(36, 40)))})
    assert current(line, at(18, 30)).state is Slot.OFF
    assert next_outage(line, at(18, 30)) is None
    assert next_outage(line, at(17)).start == at(18)
    assert current(line, at(0, day=DAY + timedelta(days=2))) is None


def test_outage_end() -> None:
    row = list(codes(off=(36, 39), maybe=39))
    line = timeline({DAY: decode("".join(row))})
    assert outage_end(line, at(18, 10)) == (at(19, 30), Slot.MAYBE)
    assert outage_end(line, at(10)) == (at(19, 30), Slot.MAYBE)
    assert outage_end(line, at(21)) is None
    # An outage running to the end of what is published has no known end.
    late = timeline({DAY: decode(codes(off=(44, 48)))})
    assert outage_end(late, at(23)) is None


def test_hours() -> None:
    slots = decode(codes(off=(10, 14), maybe=20))
    assert hours(slots, Slot.OFF) == 2
    assert hours(slots, Slot.MAYBE) == 0.5
    assert hours([None, Slot.OFF], Slot.OFF) == 0.5


def test_quiet_day() -> None:
    quiet = DaySchedule.quiet(DAY, [1, 2])
    assert not quiet.active and quiet.groups[2] == (Slot.ON,) * SLOTS


@pytest.mark.parametrize(
    ("old", "new", "kind"),
    [
        (codes(off=(36, 40)), codes(off=(34, 40)), "outage_earlier"),
        (codes(off=(36, 40)), codes(off=(38, 42)), "outage_later"),
        (codes(off=(36, 40)), codes(off=(36, 42)), "outage_longer"),
        (codes(off=(36, 40)), codes(off=(36, 38)), "outage_shorter"),
        (codes(), codes(off=(40, 44)), "outage_added"),
        (codes(off=(40, 44)), codes(), "outage_removed"),
        (codes(off=(36, 40)), codes(off=(36, 40), maybe=44), None),
    ],
)
def test_diff_kinds(old: str, new: str, kind: str | None) -> None:
    result = diff(DAY, decode(old), decode(new), at(12))
    assert result.changed
    assert result.kind == kind


def test_diff_most_urgent_kind_wins_and_lists_all() -> None:
    old = codes(off=(30, 32))[:40] + "oooo" + "uuuu"
    new = codes(off=(28, 32))
    result = diff(DAY, decode(old), decode(new), at(10))
    assert result.kind == "outage_earlier"
    assert {c.kind for c in result.changes} == {"outage_earlier", "outage_removed"}
    removed = next(c for c in result.changes if c.kind == "outage_removed")
    assert removed.as_dict() == {
        "type": "outage_removed",
        "start": None,
        "end": None,
        "old_start": at(20).isoformat(),
        "old_end": at(22).isoformat(),
    }


def test_diff_ignores_what_already_passed() -> None:
    result = diff(DAY, decode(codes(off=(10, 12))), decode(codes()), at(12))
    assert not result.changed and result.kind is None


def test_diff_unchanged() -> None:
    row = decode(codes(off=(36, 40)))
    assert not diff(DAY, row, row, at(1)).changed
