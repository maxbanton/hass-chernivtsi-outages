"""Parsers for the oblenergo schedule page and the oblenergo Telegram channel."""
from __future__ import annotations

import html as htmllib
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from .const import GROUPS, KYIV, SOURCE_TELEGRAM
from .model import SLOTS, DaySchedule, Slot, Slots


class LayoutError(Exception):
    """The page does not look the way the parser expects any more."""


_TAGS = {"u": Slot.ON, "o": Slot.OFF, "s": Slot.MAYBE}
_TABLE = re.compile(r'id="gsv"')
_DATE = re.compile(r"<p>\s*(\d{2})\.(\d{2})\.(\d{4})\s*</p>")
_STAMP = re.compile(r"станом на\s*<b>\s*(\d{1,2}):(\d{2})")
_CELL = re.compile(r"<([ous])\b[^>]*>[^<]*</\1>")


def _group_row(page: str, group: int) -> str | None:
    match = re.search(rf'<div id="inf{group}"[^>]*>(.*?)</div>', page, re.S)
    return match.group(1) if match else None


def parse_site(page: str, now: datetime) -> tuple[DaySchedule | None, int]:
    """The schedule on an oblenergo shutdowns page.

    Returns the schedule (None when the page has no schedule table, which is how
    the site shows that no outages are planned) and how many leading slots the
    page left out. The server sends all 48 today and the browser hides past
    hours; if the server ever trims them instead, the cells line up with the
    end of the day and the missing ones are filled in as maybe.
    """
    if not _TABLE.search(page):
        if "<title>Відключення" in page:
            return None, 0
        raise LayoutError("not the shutdowns page")
    found = _DATE.search(page)
    if not found:
        raise LayoutError("no schedule date")
    day = date(int(found.group(3)), int(found.group(2)), int(found.group(1)))

    groups: dict[int, Slots] = {}
    missing = 0
    for group in GROUPS:
        row = _group_row(page, group)
        if row is None:
            raise LayoutError(f"no row for group {group}")
        cells = [_TAGS[tag] for tag in _CELL.findall(row)]
        if not cells or len(cells) > SLOTS:
            raise LayoutError(f"group {group} has {len(cells)} slots")
        missing = max(missing, SLOTS - len(cells))
        groups[group] = (Slot.MAYBE,) * (SLOTS - len(cells)) + tuple(cells)

    return DaySchedule(day, groups, updated=_stamp(page, day, now)), missing


def _stamp(page: str, day: date, now: datetime) -> datetime | None:
    found = _STAMP.search(page)
    if not found:
        return None
    stamp = datetime.combine(day, time(int(found.group(1)), int(found.group(2))), KYIV)
    # Tomorrow's schedule is published the evening before, with that evening's time.
    while stamp > now + timedelta(hours=1):
        stamp -= timedelta(days=1)
    return stamp


@dataclass(frozen=True)
class Post:
    """A schedule announcement in the channel."""

    id: int
    posted: datetime
    day: date
    # False: "Електропостачання без обмежень для всіх груп".
    outages: bool
    # Per-group slots, None when the schedule was posted as a picture.
    groups: dict[int, Slots] | None

    def schedule(self) -> DaySchedule | None:
        """The post as a schedule; posts only list powered hours, so the rest is off."""
        if not self.outages:
            return DaySchedule.quiet(self.day, GROUPS, SOURCE_TELEGRAM)
        if self.groups is None:
            return None
        return DaySchedule(
            self.day, dict(self.groups), source=SOURCE_TELEGRAM, updated=self.posted,
            degraded=True,
        )


_MESSAGE = re.compile(r'data-post="[^"/]+/(\d+)"(.*?)(?=data-post="|\Z)', re.S)
_POSTED = re.compile(r'<time[^>]*datetime="([^"]+)"')
_TEXT = re.compile(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S)
_HEADER = re.compile(r"графік\s+заживлення[^\n]*?(\d{2})\.(\d{2})\.(\d{4})", re.I)
_NO_OUTAGES = re.compile(r"На\s+(\d{2})\.(\d{2})\.(\d{4})[^\n]*?без\s+обмежень", re.I)
# A group with no powered hours would have no lines, so blank lines end a block
# and are never part of the heading.
_GROUP = re.compile(r"Група[ \t]*(\d{1,2})[ \t]*\n(.*?)(?=\n[ \t]*\n|💡|Група[ \t]*\d|\Z)", re.S)
_WINDOW = re.compile(r"^(\d{1,2}):(\d{2})\s*[-\u2013\u2014]\s*(\d{1,2}):(\d{2})$")
_FROM = re.compile(r"^з\s*(\d{1,2}):(\d{2})$")
_UNTIL = re.compile(r"^до\s*(\d{1,2}):(\d{2})$")


def _text(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", "\n", fragment)
    return htmllib.unescape(re.sub(r"<[^>]+>", "", fragment))


def _index(hour: str, minute: str) -> int:
    h, m = int(hour), int(minute)
    if m not in (0, 30) or not 0 <= h <= 24 or (h == 24 and m):
        raise ValueError
    return h * 2 + m // 30


def _group_slots(body: str) -> Slots:
    slots = [Slot.OFF] * SLOTS
    for raw in body.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if "без обмежень" in line:
            return (Slot.ON,) * SLOTS
        if window := _WINDOW.match(line):
            start, end = _index(*window.group(1, 2)), _index(*window.group(3, 4))
            end = SLOTS if end <= start else end
        elif since := _FROM.match(line):
            start, end = _index(*since.groups()), SLOTS
        elif until := _UNTIL.match(line):
            start, end = 0, _index(*until.groups())
        else:
            raise ValueError(line)
        slots[start:end] = [Slot.ON] * (end - start)
    return tuple(slots)


def _groups(text: str) -> dict[int, Slots] | None:
    groups: dict[int, Slots] = {}
    for number, body in _GROUP.findall(text):
        try:
            groups[int(number)] = _group_slots(body)
        except ValueError:
            return None
    return groups if set(groups) == set(GROUPS) else None


def _day(match: re.Match[str]) -> date:
    return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))


def parse_telegram(page: str) -> list[Post]:
    """Schedule announcements on the channel's public web page, oldest first."""
    if "tgme_widget_message" not in page:
        raise LayoutError("not a channel page")
    posts = []
    for number, body in _MESSAGE.findall(page):
        posted, content = _POSTED.search(body), _TEXT.search(body)
        if not posted or not content:
            continue
        text = _text(content.group(1))
        moment = datetime.fromisoformat(posted.group(1))
        if header := _HEADER.search(text):
            posts.append(Post(int(number), moment, _day(header), True, _groups(text)))
        elif quiet := _NO_OUTAGES.search(text):
            posts.append(Post(int(number), moment, _day(quiet), False, None))
    return sorted(posts, key=lambda post: post.id)
