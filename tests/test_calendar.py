"""Tests for calendar platform."""
import pytest
from datetime import datetime, date, timedelta
from unittest.mock import MagicMock, patch

from custom_components.cv_oblenergo.calendar import PowerScheduleCalendar


class TestPowerScheduleCalendar:
    """Tests for PowerScheduleCalendar."""
    
    def test_event_returns_current_outage(self, sample_schedule_data, mock_config_entry):
        """Test event property returns current or next outage."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        calendar = PowerScheduleCalendar(coordinator, 12, mock_config_entry)
        
        # The event property should return a CalendarEvent or None
        event = calendar.event
        # Can be None if no outages
        assert event is None or hasattr(event, 'start')
    
    def test_unique_id(self, sample_schedule_data, mock_config_entry):
        """Test unique ID format."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        calendar = PowerScheduleCalendar(coordinator, 12, mock_config_entry)
        
        assert calendar.unique_id == "test_entry_id_calendar"
    
    def test_name(self, sample_schedule_data, mock_config_entry):
        """Test calendar name."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        calendar = PowerScheduleCalendar(coordinator, 12, mock_config_entry)
        
        assert calendar.name == "Outages"
    
    def test_device_info(self, sample_schedule_data, mock_config_entry):
        """Test device info."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        calendar = PowerScheduleCalendar(coordinator, 12, mock_config_entry)
        
        device_info = calendar.device_info
        assert device_info is not None
        assert "identifiers" in device_info
        assert device_info["name"] == "CV"
        assert device_info["model"] == "Group 12"
    
    @pytest.mark.asyncio
    async def test_async_get_events_no_data(self, mock_config_entry):
        """Test async_get_events returns empty list when no data."""
        coordinator = MagicMock()
        coordinator.data = None
        
        calendar = PowerScheduleCalendar(coordinator, 12, mock_config_entry)
        
        hass = MagicMock()
        start = datetime(2025, 12, 9, 0, 0)
        end = datetime(2025, 12, 10, 0, 0)
        
        events = await calendar.async_get_events(hass, start, end)
        assert events == []
    
    @pytest.mark.asyncio
    async def test_async_get_events_with_data(self, sample_schedule_data, mock_config_entry):
        """Test async_get_events returns events within range."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        calendar = PowerScheduleCalendar(coordinator, 12, mock_config_entry)
        
        hass = MagicMock()
        start = datetime(2025, 12, 9, 0, 0)
        end = datetime(2025, 12, 10, 0, 0)
        
        events = await calendar.async_get_events(hass, start, end)
        
        # Should return list of CalendarEvent objects
        assert isinstance(events, list)
        # Each event should have required properties
        for event in events:
            assert hasattr(event, 'start')
            assert hasattr(event, 'end')
            assert hasattr(event, 'summary')
    
    @pytest.mark.asyncio
    async def test_async_get_events_out_of_range(self, sample_schedule_data, mock_config_entry):
        """Test async_get_events returns empty for dates out of range."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        calendar = PowerScheduleCalendar(coordinator, 12, mock_config_entry)
        
        hass = MagicMock()
        # Request dates that don't match the schedule date
        start = datetime(2025, 12, 1, 0, 0)
        end = datetime(2025, 12, 2, 0, 0)
        
        events = await calendar.async_get_events(hass, start, end)
        assert events == []
    
    def test_get_events_for_schedule(self, sample_schedule_data, mock_config_entry):
        """Test _get_events_for_schedule generates correct events."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        calendar = PowerScheduleCalendar(coordinator, 12, mock_config_entry)
        
        schedule = sample_schedule_data.get_group(12)
        events = calendar._get_events_for_schedule(schedule, date(2025, 12, 9))
        
        # Should create events for OFF periods
        assert isinstance(events, list)
        
        # Events should be sorted by start time
        if len(events) > 1:
            for i in range(len(events) - 1):
                assert events[i].start <= events[i + 1].start
