"""API client for Chernivtsi power schedule."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, date

import aiohttp

from .const import (
    SCHEDULE_URL,
    TAG_TO_STATE,
    STATE_ON,
    STATE_OFF,
    STATE_MAYBE,
    NUM_GROUPS,
    NUM_SLOTS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class TimeSlot:
    """Represents a single time slot in the schedule."""

    hour: int
    minute: int  # 0 or 30
    state: str  # STATE_ON, STATE_OFF, or STATE_MAYBE

    @property
    def time_str(self) -> str:
        """Return time as HH:MM string."""
        return f"{self.hour:02d}:{self.minute:02d}"

    @property
    def slot_index(self) -> int:
        """Return the slot index (0-47)."""
        return self.hour * 2 + (1 if self.minute == 30 else 0)


@dataclass
class GroupSchedule:
    """Schedule for a single group."""

    group: int
    date: date
    slots: list[TimeSlot]

    def get_current_slot(self, now: datetime | None = None) -> TimeSlot | None:
        """Get the current time slot."""
        if now is None:
            now = datetime.now()

        slot_index = now.hour * 2 + (1 if now.minute >= 30 else 0)
        if 0 <= slot_index < len(self.slots):
            return self.slots[slot_index]
        return None

    def get_current_state(self, now: datetime | None = None) -> str:
        """Get the current power state."""
        slot = self.get_current_slot(now)
        return slot.state if slot else STATE_MAYBE

    def get_next_change(self, now: datetime | None = None) -> tuple[TimeSlot, str] | None:
        """Get the next state change.

        Returns tuple of (slot, state) for the next different state, or None.
        """
        if now is None:
            now = datetime.now()

        current_slot_index = now.hour * 2 + (1 if now.minute >= 30 else 0)
        current_state = self.get_current_state(now)

        # Look for next different state
        for i in range(current_slot_index + 1, len(self.slots)):
            if self.slots[i].state != current_state:
                return (self.slots[i], self.slots[i].state)

        return None

    def get_next_off(self, now: datetime | None = None) -> TimeSlot | None:
        """Get the next OFF slot."""
        if now is None:
            now = datetime.now()

        current_slot_index = now.hour * 2 + (1 if now.minute >= 30 else 0)

        for i in range(current_slot_index + 1, len(self.slots)):
            if self.slots[i].state == STATE_OFF:
                return self.slots[i]

        return None

    def get_next_on(self, now: datetime | None = None) -> TimeSlot | None:
        """Get the next ON slot."""
        if now is None:
            now = datetime.now()

        current_slot_index = now.hour * 2 + (1 if now.minute >= 30 else 0)

        for i in range(current_slot_index + 1, len(self.slots)):
            if self.slots[i].state == STATE_ON:
                return self.slots[i]

        return None

    def count_off_hours_remaining(self, now: datetime | None = None) -> float:
        """Count remaining off hours for today."""
        if now is None:
            now = datetime.now()

        current_slot_index = now.hour * 2 + (1 if now.minute >= 30 else 0)
        off_slots = sum(1 for s in self.slots[current_slot_index:] if s.state == STATE_OFF)
        return off_slots * 0.5

    def count_on_hours_remaining(self, now: datetime | None = None) -> float:
        """Count remaining on hours for today."""
        if now is None:
            now = datetime.now()

        current_slot_index = now.hour * 2 + (1 if now.minute >= 30 else 0)
        on_slots = sum(1 for s in self.slots[current_slot_index:] if s.state == STATE_ON)
        return on_slots * 0.5

    def get_off_periods(self) -> list[tuple[str, str]]:
        """Get list of OFF periods as (start_time, end_time) tuples."""
        periods = []
        in_off_period = False
        start_time = None

        for slot in self.slots:
            if slot.state == STATE_OFF and not in_off_period:
                in_off_period = True
                start_time = slot.time_str
            elif slot.state != STATE_OFF and in_off_period:
                in_off_period = False
                periods.append((start_time, slot.time_str))

        # Handle period that extends to end of day
        if in_off_period:
            periods.append((start_time, "00:00"))

        return periods

    def get_on_periods(self) -> list[tuple[str, str]]:
        """Get list of ON periods as (start_time, end_time) tuples."""
        periods = []
        in_on_period = False
        start_time = None

        for slot in self.slots:
            if slot.state == STATE_ON and not in_on_period:
                in_on_period = True
                start_time = slot.time_str
            elif slot.state != STATE_ON and in_on_period:
                in_on_period = False
                periods.append((start_time, slot.time_str))

        # Handle period that extends to end of day
        if in_on_period:
            periods.append((start_time, "00:00"))

        return periods


@dataclass
class ScheduleData:
    """Complete schedule data."""

    date: date
    groups: dict[int, GroupSchedule]
    last_updated: datetime

    def get_group(self, group: int) -> GroupSchedule | None:
        """Get schedule for a specific group."""
        return self.groups.get(group)


class PowerScheduleApiClient:
    """API client for fetching schedule data."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the API client."""
        self._session = session

    async def async_get_schedule(self) -> ScheduleData:
        """Fetch the current schedule."""
        try:
            async with self._session.get(
                SCHEDULE_URL,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                html = await response.text()
                return self._parse_schedule(html)
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching schedule: %s", err)
            raise

    def _parse_schedule(self, html: str) -> ScheduleData:
        """Parse schedule from HTML."""
        groups = {}
        schedule_date = date.today()

        # Extract date from the page
        date_match = re.search(r'<p>(\d{2}\.\d{2}\.\d{4})\s*</p>', html)
        if date_match:
            try:
                schedule_date = datetime.strptime(date_match.group(1), "%d.%m.%Y").date()
            except ValueError:
                _LOGGER.warning("Could not parse date, using today")

        # Extract schedule for each group
        for group_num in range(1, NUM_GROUPS + 1):
            pattern = rf'<div id="inf{group_num}" data-id="{group_num}">(.*?)</div>'
            match = re.search(pattern, html)

            if match:
                slot_html = match.group(1)
                slots = self._parse_slots(slot_html)

                if len(slots) == NUM_SLOTS:
                    groups[group_num] = GroupSchedule(
                        group=group_num,
                        date=schedule_date,
                        slots=slots,
                    )
                else:
                    _LOGGER.warning(
                        "Group %d has %d slots instead of %d",
                        group_num, len(slots), NUM_SLOTS
                    )

        return ScheduleData(
            date=schedule_date,
            groups=groups,
            last_updated=datetime.now(),
        )

    def _parse_slots(self, slot_html: str) -> list[TimeSlot]:
        """Parse time slots from HTML fragment."""
        slots = []

        # Match all tags: <o>в</o>, <u>з</u>, <s>мз</s>
        pattern = r'<([ous])>[^<]*</\1>'
        matches = re.findall(pattern, slot_html)

        for i, tag in enumerate(matches):
            hour = i // 2
            minute = 30 if i % 2 else 0
            state = TAG_TO_STATE.get(tag, STATE_MAYBE)

            slots.append(TimeSlot(hour=hour, minute=minute, state=state))

        return slots
