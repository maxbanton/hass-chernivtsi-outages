"""Schedule model: half-hour slots in Kyiv time and the periods they form."""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum

from .const import KYIV, SOURCE_SITE

SLOTS = 48


class Slot(StrEnum):
    """Scheduled state of one half hour."""

    ON = "on"
    OFF = "off"
    MAYBE = "maybe"


# Same letters as the tags the site marks its cells with.
_CODES = {Slot.ON: "u", Slot.OFF: "o", Slot.MAYBE: "s"}
_FROM_CODE = {code: slot for slot, code in _CODES.items()}

Slots = tuple[Slot, ...]


def encode(slots: Iterable[Slot]) -> str:
    return "".join(_CODES[slot] for slot in slots)


def decode(text: str) -> Slots:
    return tuple(_FROM_CODE[code] for code in text)


def slot_start(day: date, index: int) -> datetime:
    """When slot `index` of `day` starts; index 48 is the next midnight.

    Wall-clock based, so on daylight saving days a slot can be shorter or
    longer than 30 minutes, which is how the published schedule reads too.
    """
    if index >= SLOTS:
        return datetime.combine(day + timedelta(days=1), time(0), KYIV)
    return datetime.combine(day, time(index // 2, 30 * (index % 2)), KYIV)


def slot_at(moment: datetime) -> tuple[date, int]:
    """The day and slot index a moment falls in."""
    local = moment.astimezone(KYIV)
    return local.date(), local.hour * 2 + local.minute // 30


@dataclass(frozen=True)
class Period:
    start: datetime
    end: datetime
    state: Slot

    @property
    def hours(self) -> float:
        # Through UTC: subtracting datetimes that share a tzinfo ignores DST shifts.
        return (self.end.astimezone(UTC) - self.start.astimezone(UTC)).total_seconds() / 3600


@dataclass
class DaySchedule:
    """What is published for one day, for every group."""

    day: date
    groups: dict[int, Slots]
    # False when the publisher says there are no outages that day.
    active: bool = True
    source: str = SOURCE_SITE
    # The time the publisher says the schedule is current as of. The site moves
    # it every 30 minutes whether or not anything changed.
    updated: datetime | None = None
    degraded: bool = False
    # When this version of the schedule was published.
    changed: datetime | None = None

    @classmethod
    def quiet(cls, day: date, groups: Iterable[int], source: str = SOURCE_SITE) -> DaySchedule:
        return cls(day, dict.fromkeys(groups, (Slot.ON,) * SLOTS), False, source)


def periods(day: date, slots: Sequence[Slot]) -> list[Period]:
    """Consecutive equal slots of one day merged into periods."""
    result: list[Period] = []
    begin = 0
    for index in range(1, SLOTS + 1):
        if index == SLOTS or slots[index] != slots[begin]:
            result.append(Period(slot_start(day, begin), slot_start(day, index), slots[begin]))
            begin = index
    return result


def timeline(days: Mapping[date, Sequence[Slot]]) -> list[Period]:
    """Periods over all known days, merged across midnight where days are adjacent."""
    result: list[Period] = []
    for day in sorted(days):
        for period in periods(day, days[day]):
            last = result[-1] if result else None
            if last and last.state == period.state and last.end == period.start:
                result[-1] = Period(last.start, period.end, period.state)
            else:
                result.append(period)
    return result


def current(line: Sequence[Period], now: datetime) -> Period | None:
    return next((p for p in line if p.start <= now < p.end), None)


def next_outage(line: Sequence[Period], now: datetime) -> Period | None:
    """The next outage that has not started yet."""
    return next((p for p in line if p.state is Slot.OFF and p.start > now), None)


def outage_end(line: Sequence[Period], now: datetime) -> tuple[datetime, Slot] | None:
    """When the current, or else the next, outage ends and what follows it.

    None when the outage runs to the end of what is published, because then
    nobody knows yet when it ends.
    """
    period = current(line, now)
    if period is None or period.state is not Slot.OFF:
        period = next_outage(line, now)
    if period is None:
        return None
    after = next((p for p in line if p.start == period.end), None)
    return (period.end, after.state) if after else None


def hours(slots: Iterable[Slot | None], state: Slot) -> float:
    return sum(1 for slot in slots if slot is state) / 2


# Most urgent first: an event entity fires one type per update.
CHANGE_KINDS = (
    "outage_earlier",
    "outage_added",
    "outage_longer",
    "outage_later",
    "outage_shorter",
    "outage_removed",
)


@dataclass(frozen=True)
class Change:
    kind: str
    start: datetime | None = None
    end: datetime | None = None
    old_start: datetime | None = None
    old_end: datetime | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "type": self.kind,
            "start": _iso(self.start),
            "end": _iso(self.end),
            "old_start": _iso(self.old_start),
            "old_end": _iso(self.old_end),
        }


def _iso(moment: datetime | None) -> str | None:
    return moment.isoformat() if moment else None


@dataclass
class Diff:
    changes: list[Change] = field(default_factory=list)
    # Any slot from `after` on differs, also when no outage moved.
    changed: bool = False

    @property
    def kind(self) -> str | None:
        kinds = {change.kind for change in self.changes}
        return next((kind for kind in CHANGE_KINDS if kind in kinds), None)


def diff(day: date, old: Sequence[Slot], new: Sequence[Slot], after: datetime) -> Diff:
    """How the outages of `day` that end after `after` changed."""
    first = 0
    while first < SLOTS and slot_start(day, first + 1) <= after:
        first += 1
    result = Diff(changed=tuple(old[first:]) != tuple(new[first:]))
    if not result.changed:
        return result

    def outages(slots: Sequence[Slot]) -> list[Period]:
        return [p for p in periods(day, slots) if p.state is Slot.OFF and p.end > after]

    before, now = outages(old), outages(new)
    matched: set[Period] = set()
    for period in now:
        overlap = [o for o in before if o.start < period.end and period.start < o.end]
        if not overlap:
            result.changes.append(Change("outage_added", period.start, period.end))
            continue
        was = overlap[0]
        matched.update(overlap)
        if period.start < was.start:
            kind = "outage_earlier"
        elif period.start > was.start:
            kind = "outage_later"
        elif period.end > was.end:
            kind = "outage_longer"
        elif period.end < was.end:
            kind = "outage_shorter"
        else:
            continue
        result.changes.append(Change(kind, period.start, period.end, was.start, was.end))
    result.changes.extend(
        Change("outage_removed", old_start=o.start, old_end=o.end)
        for o in before
        if o not in matched
    )
    return result
