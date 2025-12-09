"""Unit tests for the API client."""
import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from custom_components.cv_oblenergo.api import (
    PowerScheduleApiClient,
    ScheduleData,
    GroupSchedule,
    TimeSlot,
)
from custom_components.cv_oblenergo.const import STATE_ON, STATE_OFF, STATE_MAYBE


class TestTimeSlot:
    """Tests for TimeSlot dataclass."""
    
    def test_time_str(self):
        """Test time_str property."""
        slot = TimeSlot(hour=9, minute=0, state=STATE_ON)
        assert slot.time_str == "09:00"
        
        slot = TimeSlot(hour=14, minute=30, state=STATE_OFF)
        assert slot.time_str == "14:30"
        
        slot = TimeSlot(hour=0, minute=0, state=STATE_ON)
        assert slot.time_str == "00:00"
    
    def test_slot_index(self):
        """Test slot_index property."""
        # 00:00 should be index 0
        slot = TimeSlot(hour=0, minute=0, state=STATE_ON)
        assert slot.slot_index == 0
        
        # 00:30 should be index 1
        slot = TimeSlot(hour=0, minute=30, state=STATE_ON)
        assert slot.slot_index == 1
        
        # 12:00 should be index 24
        slot = TimeSlot(hour=12, minute=0, state=STATE_ON)
        assert slot.slot_index == 24
        
        # 23:30 should be index 47
        slot = TimeSlot(hour=23, minute=30, state=STATE_ON)
        assert slot.slot_index == 47


class TestGroupSchedule:
    """Tests for GroupSchedule dataclass."""
    
    @pytest.fixture
    def schedule(self):
        """Create a test schedule."""
        # Create a simple pattern: ON for first 4 hours, OFF for next 4, ON for rest
        slots = []
        for i in range(48):
            hour = i // 2
            minute = 30 if i % 2 else 0
            if i < 8:  # 00:00 - 03:30 = ON
                state = STATE_ON
            elif i < 16:  # 04:00 - 07:30 = OFF
                state = STATE_OFF
            elif i == 16:  # 08:00 = MAYBE
                state = STATE_MAYBE
            else:  # Rest = ON
                state = STATE_ON
            slots.append(TimeSlot(hour=hour, minute=minute, state=state))
        
        return GroupSchedule(
            group=1,
            date=date(2025, 12, 9),
            slots=slots,
        )
    
    def test_get_current_slot(self, schedule):
        """Test getting current slot."""
        # Test at 02:15 -> should return slot for 02:00
        now = datetime(2025, 12, 9, 2, 15)
        slot = schedule.get_current_slot(now)
        assert slot is not None
        assert slot.hour == 2
        assert slot.minute == 0
        assert slot.state == STATE_ON
        
        # Test at 02:45 -> should return slot for 02:30
        now = datetime(2025, 12, 9, 2, 45)
        slot = schedule.get_current_slot(now)
        assert slot is not None
        assert slot.hour == 2
        assert slot.minute == 30
        assert slot.state == STATE_ON
    
    def test_get_current_state(self, schedule):
        """Test getting current state."""
        # During ON period
        now = datetime(2025, 12, 9, 2, 0)
        assert schedule.get_current_state(now) == STATE_ON
        
        # During OFF period
        now = datetime(2025, 12, 9, 5, 0)
        assert schedule.get_current_state(now) == STATE_OFF
        
        # During MAYBE period
        now = datetime(2025, 12, 9, 8, 0)
        assert schedule.get_current_state(now) == STATE_MAYBE
    
    def test_get_next_change(self, schedule):
        """Test getting next state change."""
        # At 02:00 (ON), next change should be at 04:00 (OFF)
        now = datetime(2025, 12, 9, 2, 0)
        result = schedule.get_next_change(now)
        assert result is not None
        slot, state = result
        assert slot.hour == 4
        assert slot.minute == 0
        assert state == STATE_OFF
        
        # At 05:00 (OFF), next change should be at 08:00 (MAYBE)
        now = datetime(2025, 12, 9, 5, 0)
        result = schedule.get_next_change(now)
        assert result is not None
        slot, state = result
        assert slot.hour == 8
        assert slot.minute == 0
        assert state == STATE_MAYBE
    
    def test_get_next_off(self, schedule):
        """Test getting next OFF slot."""
        # At 02:00 (ON), next OFF should be at 04:00
        now = datetime(2025, 12, 9, 2, 0)
        slot = schedule.get_next_off(now)
        assert slot is not None
        assert slot.hour == 4
        assert slot.minute == 0
    
    def test_get_next_on(self, schedule):
        """Test getting next ON slot."""
        # At 05:00 (OFF), next ON should be at 08:30 (after MAYBE at 08:00)
        now = datetime(2025, 12, 9, 5, 0)
        slot = schedule.get_next_on(now)
        assert slot is not None
        assert slot.hour == 8
        assert slot.minute == 30

    def test_get_next_on_or_maybe(self, schedule):
        """Test getting next ON or MAYBE slot (both treated as power available)."""
        # At 05:00 (OFF), next non-OFF should be at 08:00 (MAYBE)
        now = datetime(2025, 12, 9, 5, 0)
        slot = schedule.get_next_on_or_maybe(now)
        assert slot is not None
        assert slot.hour == 8
        assert slot.minute == 0
        assert slot.state == STATE_MAYBE
    
    def test_count_off_hours_remaining(self, schedule):
        """Test counting remaining off hours."""
        # At 04:00, there are 8 OFF slots (04:00-07:30) = 4 hours
        now = datetime(2025, 12, 9, 4, 0)
        hours = schedule.count_off_hours_remaining(now)
        assert hours == 4.0  # 8 slots * 0.5 = 4 hours
    
    def test_count_on_hours_remaining(self, schedule):
        """Test counting remaining on hours."""
        # At 00:00, count ON slots
        now = datetime(2025, 12, 9, 0, 0)
        hours = schedule.count_on_hours_remaining(now)
        # 8 ON slots at start (0-7) + 31 ON slots after slot 16 = 39 * 0.5 = 19.5 hours
        assert hours == 19.5
    
    def test_get_off_periods(self, schedule):
        """Test getting off periods."""
        periods = schedule.get_off_periods()
        assert len(periods) == 1
        assert periods[0] == ("04:00", "08:00")
    
    def test_get_on_periods(self, schedule):
        """Test getting on periods."""
        periods = schedule.get_on_periods()
        assert len(periods) == 2
        assert periods[0] == ("00:00", "04:00")
        assert periods[1] == ("08:30", "00:00")  # Extends to end of day


class TestScheduleData:
    """Tests for ScheduleData dataclass."""
    
    def test_get_group(self, sample_schedule_data):
        """Test getting schedule for a specific group."""
        group1 = sample_schedule_data.get_group(1)
        assert group1 is not None
        assert group1.group == 1
        
        group12 = sample_schedule_data.get_group(12)
        assert group12 is not None
        assert group12.group == 12
        
        # Non-existent group
        group99 = sample_schedule_data.get_group(99)
        assert group99 is None


class TestPowerScheduleApiClient:
    """Tests for PowerScheduleApiClient."""
    
    @pytest.mark.asyncio
    async def test_parse_schedule(self, sample_html):
        """Test parsing schedule from HTML."""
        session = MagicMock()
        client = PowerScheduleApiClient(session)
        
        # Call the internal parse method
        schedule = client._parse_schedule(sample_html)
        
        assert schedule is not None
        assert schedule.date == date(2025, 12, 9)
        # Should have groups (may vary based on HTML parsing)
        assert len(schedule.groups) >= 1
        
        # Check group 1
        group1 = schedule.get_group(1)
        assert group1 is not None
        assert len(group1.slots) == 48
        assert group1.slots[0].state == STATE_OFF  # First slot is OFF
        assert group1.slots[2].state == STATE_MAYBE  # Third slot is MAYBE
        assert group1.slots[3].state == STATE_ON  # Fourth slot is ON
    
    @pytest.mark.asyncio
    async def test_parse_slots(self):
        """Test parsing slots from HTML fragment."""
        session = MagicMock()
        client = PowerScheduleApiClient(session)
        
        slot_html = "<o>в</o><u>з</u><s>мз</s><u>з</u>"
        slots = client._parse_slots(slot_html)
        
        assert len(slots) == 4
        assert slots[0].state == STATE_OFF
        assert slots[0].hour == 0
        assert slots[0].minute == 0
        
        assert slots[1].state == STATE_ON
        assert slots[1].hour == 0
        assert slots[1].minute == 30
        
        assert slots[2].state == STATE_MAYBE
        assert slots[2].hour == 1
        assert slots[2].minute == 0
        
        assert slots[3].state == STATE_ON
        assert slots[3].hour == 1
        assert slots[3].minute == 30
    
    @pytest.mark.asyncio
    async def test_async_get_schedule_success(self, sample_html):
        """Test successful schedule fetch."""
        # Create mock response
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=sample_html)
        mock_response.raise_for_status = MagicMock()
        
        # Create mock context manager
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_cm)
        
        client = PowerScheduleApiClient(mock_session)
        schedule = await client.async_get_schedule()
        
        assert schedule is not None
        assert len(schedule.groups) >= 1
    
    @pytest.mark.asyncio
    async def test_async_get_schedule_error(self):
        """Test schedule fetch with network error."""
        # Create mock that raises on get
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection failed"))
        
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_cm)
        
        client = PowerScheduleApiClient(mock_session)
        
        with pytest.raises(aiohttp.ClientError):
            await client.async_get_schedule()
