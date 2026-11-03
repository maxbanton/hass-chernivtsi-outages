"""Keeps the published schedule and decides when the site is worth asking again.

The oblenergo page is an uncached PHP page and every install multiplies what we
ask of it, so it is fetched only when the oblenergo Telegram channel announces a
schedule, plus a slow safety fetch. Slot boundaries are computed locally.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import Client, FetchError
from .const import (
    DOMAIN,
    GROUPS,
    KYIV,
    REPO_URL,
    SITE_BACKOFF_MAX,
    SITE_NEXT_URL,
    SITE_SAFETY_ACTIVE,
    SITE_SAFETY_NO_TELEGRAM,
    SITE_SAFETY_QUIET,
    SITE_URL,
    SOURCE_TELEGRAM,
    STORAGE_VERSION,
    TELEGRAM_INTERVAL,
    TELEGRAM_URL,
    VERIFY_ATTEMPTS,
)
from .model import SLOTS, DaySchedule, Period, Slot, Slots, decode, diff, encode, slot_at, timeline
from .parsers import LayoutError, Post, parse_site, parse_telegram

_LOGGER = logging.getLogger(__package__)

SITE_BACKOFF_START = timedelta(minutes=5)
KEEP_EVENTS = 10


@dataclass(frozen=True)
class ScheduleEvent:
    serial: int
    kind: str
    attributes: dict[str, Any]


def _kyiv_day(moment: datetime) -> date:
    return moment.astimezone(KYIV).date()


def _plausible(post: Post) -> bool:
    """A post dated the day it was posted or the next one.

    The channel has carried typos (a post on 17.10 dated 01.10), which would
    otherwise overwrite another day.
    """
    posted = _kyiv_day(post.posted)
    return post.day in (posted, posted + timedelta(days=1))


def _powered(slots: Slots) -> tuple[bool, ...]:
    return tuple(slot is Slot.ON for slot in slots)


class OutageCoordinator(DataUpdateCoordinator[dict[date, DaySchedule]]):
    """Polls the channel, fetches the site when needed, keeps the days it knows."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: Client, groups: list[int]
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=TELEGRAM_INTERVAL,
        )
        self.client = client
        self.groups = groups
        self.days: dict[date, DaySchedule] = {}
        self.frozen: dict[date, dict[int, list[Slot | None]]] = {}
        self.first: dict[date, dict[int, Slots]] = {}
        self.revisions: dict[date, int] = {}
        self.events: dict[int, list[ScheduleEvent]] = {}
        self.posts: list[Post] = []
        self.telegram_ok = True
        self.telegram_error: str | None = None
        self.last_post_id: int | None = None
        self.last_site: datetime | None = None
        self.site_errors = 0
        self.site_error: str | None = None
        self.site_retry_at: datetime | None = None
        self._expect: Post | None = None
        self._expect_attempts = 0
        self._serial = 0
        self._started = False
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )

    # Persistence

    async def async_load(self) -> None:
        """Restore what was known before a restart."""
        stored = await self._store.async_load() or {}
        for iso, raw in stored.get("days", {}).items():
            day = date.fromisoformat(iso)
            updated = raw.get("updated")
            self.days[day] = DaySchedule(
                day,
                {int(g): decode(code) for g, code in raw["groups"].items()},
                raw["active"],
                raw["source"],
                datetime.fromisoformat(updated) if updated else None,
                raw.get("degraded", False),
            )
        for iso, groups in stored.get("frozen", {}).items():
            self.frozen[date.fromisoformat(iso)] = {
                int(g): [None if code == "-" else decode(code)[0] for code in row]
                for g, row in groups.items()
            }
        for iso, groups in stored.get("first", {}).items():
            self.first[date.fromisoformat(iso)] = {
                int(g): decode(code) for g, code in groups.items()
            }
        self.revisions = {date.fromisoformat(d): n for d, n in stored.get("revisions", {}).items()}
        self.last_post_id = stored.get("last_post_id")
        if last := stored.get("last_site"):
            self.last_site = datetime.fromisoformat(last)
        self._roll(dt_util.now())

    def _serialize(self) -> dict[str, Any]:
        return {
            "days": {
                day.isoformat(): {
                    "groups": {str(g): encode(s) for g, s in schedule.groups.items()},
                    "active": schedule.active,
                    "source": schedule.source,
                    "updated": schedule.updated.isoformat() if schedule.updated else None,
                    "degraded": schedule.degraded,
                }
                for day, schedule in self.days.items()
            },
            "frozen": {
                day.isoformat(): {
                    str(g): "".join("-" if s is None else encode((s,)) for s in row)
                    for g, row in groups.items()
                }
                for day, groups in self.frozen.items()
            },
            "first": {
                day.isoformat(): {str(g): encode(s) for g, s in groups.items()}
                for day, groups in self.first.items()
            },
            "revisions": {day.isoformat(): n for day, n in self.revisions.items()},
            "last_post_id": self.last_post_id,
            "last_site": self.last_site.isoformat() if self.last_site else None,
        }

    # Update cycle

    async def _async_update_data(self) -> dict[date, DaySchedule]:
        now = dt_util.now()
        self._freeze(now)
        posts = await self._poll_telegram()
        pages = self._pages_due(now, posts or [])
        if posts:
            self.last_post_id = max(self.last_post_id or 0, posts[-1].id)
        for url in pages:
            if not await self._fetch_site(url, now):
                break
        self._apply_posts(now)
        self._roll(now)
        self._store.async_delay_save(self._serialize, 5)
        if not self.days and self.last_site is None and posts is None:
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="no_source")
        self._started = True
        return dict(self.days)

    async def _poll_telegram(self) -> list[Post] | None:
        try:
            posts = parse_telegram(await self.client.fetch(TELEGRAM_URL))
        except LayoutError as err:
            self._issue("telegram_layout")
            self._telegram_down(err)
            return None
        except FetchError as err:
            self._telegram_down(err)
            return None
        ir.async_delete_issue(self.hass, DOMAIN, "telegram_layout")
        if not self.telegram_ok:
            _LOGGER.info("The oblenergo Telegram channel is readable again")
        self.telegram_ok, self.telegram_error = True, None
        self.posts = [post for post in posts if _plausible(post)]
        return self.posts

    def _telegram_down(self, err: Exception) -> None:
        if self.telegram_ok:
            _LOGGER.warning(
                "Cannot read the oblenergo Telegram channel, checking the schedule page "
                "every %s minutes instead: %s",
                int(SITE_SAFETY_NO_TELEGRAM.total_seconds() // 60),
                err,
            )
        self.telegram_ok, self.telegram_error = False, str(err)

    def _pages_due(self, now: datetime, posts: list[Post]) -> list[str]:
        if self.site_retry_at and now < self.site_retry_at:
            return []
        today = _kyiv_day(now)
        pages: set[str] = set()
        if self.last_post_id is not None:
            for post in posts:
                if post.id > self.last_post_id and post.day >= today:
                    pages.add(SITE_URL if post.day == today else SITE_NEXT_URL)
                    if post.groups is not None:
                        self._expect, self._expect_attempts = post, 0
        if self._expect is not None and self._expect.day < today:
            self._expect = None
        if (expected := self._expected_url(now)) is not None:
            pages.add(expected)
        if not self.telegram_ok:
            interval = SITE_SAFETY_NO_TELEGRAM
        elif self._active(today):
            interval = SITE_SAFETY_ACTIVE
        else:
            interval = SITE_SAFETY_QUIET
        if self.last_site is None or now - self.last_site >= interval:
            pages.add(SITE_URL)
        # Today's page first: it decides whether today is quiet.
        return sorted(pages, key=lambda url: url != SITE_URL)

    async def _fetch_site(self, url: str, now: datetime) -> bool:
        try:
            schedule, missing = parse_site(await self.client.fetch(url), now)
        except LayoutError as err:
            self._issue("site_layout")
            self._site_failed(now, err, None)
            return False
        except FetchError as err:
            self._site_failed(now, err, err.retry_after)
            return False
        ir.async_delete_issue(self.hass, DOMAIN, "site_layout")
        if self.site_errors:
            _LOGGER.info("The oblenergo schedule page is reachable again")
        self.site_errors, self.site_error, self.site_retry_at = 0, None, None
        self.last_site = now
        if schedule is not None:
            self._store_day(schedule, now, missing)
        elif url == SITE_URL:
            self._no_table(now)
        self._check_expected(url, schedule, now)
        return True

    def _site_failed(self, now: datetime, err: Exception, retry_after: float | None) -> None:
        self.site_errors += 1
        self.site_error = str(err)
        if retry_after is not None:
            delay = timedelta(seconds=retry_after)
        else:
            delay = SITE_BACKOFF_START * 2 ** (self.site_errors - 1)
        self.site_retry_at = now + min(delay, SITE_BACKOFF_MAX)
        if self.site_errors == 1:
            _LOGGER.warning("Cannot read the oblenergo schedule page: %s", err)

    def _issue(self, key: str) -> None:
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            key,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=key,
            learn_more_url=f"{REPO_URL}/issues",
        )

    # Schedule bookkeeping

    def _recently_active(self, today: date) -> bool:
        yesterday = today - timedelta(days=1)
        if (schedule := self.days.get(yesterday)) is not None and schedule.active:
            return True
        return any(post.outages and post.day >= yesterday for post in self.posts)

    def _active(self, today: date) -> bool:
        return any(
            schedule.active for day, schedule in self.days.items() if day >= today
        ) or self._recently_active(today)

    def _no_table(self, now: datetime) -> None:
        """The page shows no schedule: no outages, or today is not published yet.

        Right after a day with outages a missing table is read as "not published
        yet" and today stays unknown, because calling it a day without outages
        would be the dangerous mistake.
        """
        today = _kyiv_day(now)
        if today in self.days or self._recently_active(today):
            return
        self._store_day(DaySchedule.quiet(today, GROUPS), now, 0)

    def _apply_posts(self, now: datetime) -> None:
        """Use the channel where the site has nothing newer."""
        today = _kyiv_day(now)
        latest: dict[date, Post] = {}
        for post in self.posts:
            if post.day >= today:
                latest[post.day] = post
        for day, post in sorted(latest.items()):
            schedule = post.schedule()
            if schedule is None:
                continue
            known = self.days.get(day)
            if (
                known is None
                or (known.source == SOURCE_TELEGRAM and known.updated != schedule.updated)
                or (
                    self.site_errors
                    and post.outages
                    and known.updated is not None
                    and known.updated < post.posted
                )
            ):
                self._store_day(schedule, now, 0)

    def _store_day(self, schedule: DaySchedule, now: datetime, missing: int) -> None:
        day = schedule.day
        old = self.days.get(day)
        if missing:
            for group, slots in schedule.groups.items():
                known = old.groups[group] if old else self._frozen_row(day, group)
                schedule.groups[group] = tuple(
                    known[i] or slots[i] if i < missing else slots[i] for i in range(SLOTS)
                )
        changed = old is None or any(old.groups[g] != schedule.groups[g] for g in GROUPS)
        if changed:
            self._announce(old, schedule, now)
        if old is not None and changed:
            self.revisions[day] = self.revisions.get(day, 0) + 1
        self.first.setdefault(day, {g: schedule.groups[g] for g in GROUPS})
        self.days[day] = schedule

    def _frozen_row(self, day: date, group: int) -> list[Slot | None]:
        return self.frozen.get(day, {}).get(group, [None] * SLOTS)

    def _announce(self, old: DaySchedule | None, new: DaySchedule, now: datetime) -> None:
        for group in self.groups:
            slots = new.groups[group]
            if old is None:
                if new.active:
                    self._fire(group, "schedule_published", {"date": new.day.isoformat()})
                continue
            if old.degraded and _powered(old.groups[group]) == _powered(slots):
                # The site's detail replacing the channel's on/off only version.
                continue
            change = diff(new.day, old.groups[group], slots, now)
            if change.changed:
                self._fire(
                    group,
                    change.kind or "schedule_changed",
                    {
                        "date": new.day.isoformat(),
                        "changes": [c.as_dict() for c in change.changes],
                    },
                )

    def _fire(self, group: int, kind: str, attributes: dict[str, Any]) -> None:
        # Nothing fires on the first update after setup: a restart is not news.
        if not self._started:
            return
        self._serial += 1
        events = self.events.setdefault(group, [])
        events.append(ScheduleEvent(self._serial, kind, attributes))
        del events[:-KEEP_EVENTS]

    def _expected_url(self, now: datetime) -> str | None:
        if self._expect is None:
            return None
        return SITE_URL if self._expect.day == _kyiv_day(now) else SITE_NEXT_URL

    def _check_expected(self, url: str, schedule: DaySchedule | None, now: datetime) -> None:
        """Compare the site with the post that announced it.

        The channel can be a few minutes ahead of the site, and the page for
        tomorrow can lag the post; while they disagree the page is asked again
        on the next cycles, a bounded number of times.
        """
        post = self._expect
        if post is None or post.groups is None or url != self._expected_url(now):
            return
        if schedule is not None and schedule.day == post.day and all(
            _powered(post.groups[g]) == _powered(schedule.groups[g]) for g in GROUPS
        ):
            self._expect = None
            return
        self._expect_attempts += 1
        if self._expect_attempts >= VERIFY_ATTEMPTS:
            _LOGGER.debug("The schedule page still differs from post %s, keeping the page", post.id)
            self._expect = None

    def _freeze(self, now: datetime) -> None:
        """Keep each passed slot as it was scheduled when it passed."""
        day, index = slot_at(now)
        if (schedule := self.days.get(day)) is None:
            return
        groups = self.frozen.setdefault(day, {})
        for group in self.groups:
            row = groups.setdefault(group, [None] * SLOTS)
            for i in range(index):
                if row[i] is None:
                    row[i] = schedule.groups[group][i]

    def _roll(self, now: datetime) -> None:
        oldest = _kyiv_day(now) - timedelta(days=1)
        for store in (self.days, self.frozen, self.first, self.revisions):
            for day in [d for d in store if d < oldest]:
                del store[day]

    @callback
    def async_tick(self, now: datetime) -> None:
        """At every slot boundary: no fetch, only new states."""
        self._freeze(now)
        self._roll(now)
        self.async_update_listeners()

    # Read access for entities

    def line(self, group: int) -> list[Period]:
        return timeline({day: s.groups[group] for day, s in self.days.items()})

    def today(self, now: datetime) -> DaySchedule | None:
        return self.days.get(_kyiv_day(now))

    def tomorrow(self, now: datetime) -> DaySchedule | None:
        return self.days.get(_kyiv_day(now) + timedelta(days=1))

    def effective(self, group: int, now: datetime) -> list[Slot] | None:
        """Today as it was scheduled for passed slots and as it is now for the rest."""
        day, index = slot_at(now)
        if (schedule := self.days.get(day)) is None:
            return None
        row = self._frozen_row(day, group)
        current = schedule.groups[group]
        return [row[i] or current[i] if i < index else current[i] for i in range(SLOTS)]

    def events_after(self, group: int, serial: int) -> list[ScheduleEvent]:
        return [event for event in self.events.get(group, []) if event.serial > serial]
