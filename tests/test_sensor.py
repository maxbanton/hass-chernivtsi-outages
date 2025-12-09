"""Tests for sensor platform."""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from custom_components.cv_oblenergo.sensor import (
    PowerStateSensor,
    NextOnSensor,
    NextOffSensor,
)
from custom_components.cv_oblenergo.api import GroupSchedule, TimeSlot
from custom_components.cv_oblenergo.const import STATE_ON, STATE_OFF, STATE_MAYBE


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = None
    return coordinator


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {"group": 12}
    return entry


@pytest.fixture
def sample_schedule():
    """Create a sample schedule for testing."""
    slots = []
    for i in range(48):
        hour = i // 2
        minute = 30 if i % 2 else 0
        # Pattern: OFF 0-6, ON 6-12, OFF 12-18, ON 18-24
        if hour < 6:
            state = STATE_OFF
        elif hour < 12:
            state = STATE_ON
        elif hour < 18:
            state = STATE_OFF
        else:
            state = STATE_ON
        slots.append(TimeSlot(hour=hour, minute=minute, state=state))
    return GroupSchedule(group=12, date=datetime.now().date(), slots=slots)


@pytest.fixture
def schedule_with_maybe():
    """Create a schedule with maybe state."""
    slots = []
    for i in range(48):
        hour = i // 2
        minute = 30 if i % 2 else 0
        if hour < 6:
            state = STATE_OFF
        elif hour < 8:
            state = STATE_MAYBE  # Maybe from 6-8
        elif hour < 12:
            state = STATE_ON
        elif hour < 18:
            state = STATE_OFF
        else:
            state = STATE_ON
        slots.append(TimeSlot(hour=hour, minute=minute, state=state))
    return GroupSchedule(group=12, date=datetime.now().date(), slots=slots)


class TestPowerStateSensor:
    """Tests for PowerStateSensor."""

    def test_native_value_on(self, mock_coordinator, mock_entry, sample_schedule):
        """Test native value when power is on."""
        mock_coordinator.data = MagicMock()
        mock_coordinator.data.get_group.return_value = sample_schedule

        sensor = PowerStateSensor(mock_coordinator, 12, mock_entry)

        with patch.object(sample_schedule, 'get_current_state', return_value=STATE_ON):
            assert sensor.native_value == "on"

    def test_native_value_off(self, mock_coordinator, mock_entry, sample_schedule):
        """Test native value when power is off."""
        mock_coordinator.data = MagicMock()
        mock_coordinator.data.get_group.return_value = sample_schedule

        sensor = PowerStateSensor(mock_coordinator, 12, mock_entry)

        with patch.object(sample_schedule, 'get_current_state', return_value=STATE_OFF):
            assert sensor.native_value == "off"

    def test_native_value_maybe_treated_as_on(self, mock_coordinator, mock_entry, sample_schedule):
        """Test that maybe state is treated as on."""
        mock_coordinator.data = MagicMock()
        mock_coordinator.data.get_group.return_value = sample_schedule

        sensor = PowerStateSensor(mock_coordinator, 12, mock_entry)

        with patch.object(sample_schedule, 'get_current_state', return_value=STATE_MAYBE):
            assert sensor.native_value == "on"

    def test_native_value_no_data(self, mock_coordinator, mock_entry):
        """Test native value when no data available."""
        mock_coordinator.data = None

        sensor = PowerStateSensor(mock_coordinator, 12, mock_entry)
        assert sensor.native_value is None

    def test_icon_on(self, mock_coordinator, mock_entry, sample_schedule):
        """Test icon when power is on."""
        mock_coordinator.data = MagicMock()
        mock_coordinator.data.get_group.return_value = sample_schedule

        sensor = PowerStateSensor(mock_coordinator, 12, mock_entry)

        with patch.object(sample_schedule, 'get_current_state', return_value=STATE_ON):
            assert sensor.icon == "mdi:flash"

    def test_icon_off(self, mock_coordinator, mock_entry, sample_schedule):
        """Test icon when power is off."""
        mock_coordinator.data = MagicMock()
        mock_coordinator.data.get_group.return_value = sample_schedule

        sensor = PowerStateSensor(mock_coordinator, 12, mock_entry)

        with patch.object(sample_schedule, 'get_current_state', return_value=STATE_OFF):
            assert sensor.icon == "mdi:flash-off"

    def test_unique_id(self, mock_coordinator, mock_entry):
        """Test unique_id format."""
        sensor = PowerStateSensor(mock_coordinator, 12, mock_entry)
        assert sensor.unique_id == "test_entry_id_state"

    def test_device_info(self, mock_coordinator, mock_entry):
        """Test device_info."""
        sensor = PowerStateSensor(mock_coordinator, 12, mock_entry)
        assert "CV Power" in sensor.device_info["name"]


class TestNextOnSensor:
    """Tests for NextOnSensor."""

    def test_native_value(self, mock_coordinator, mock_entry, sample_schedule):
        """Test native value returns next ON time."""
        mock_coordinator.data = MagicMock()
        mock_coordinator.data.get_group.return_value = sample_schedule

        sensor = NextOnSensor(mock_coordinator, 12, mock_entry)

        next_on_slot = TimeSlot(hour=6, minute=0, state=STATE_ON)
        with patch.object(sample_schedule, 'get_next_on_or_maybe', return_value=next_on_slot):
            value = sensor.native_value
            assert value is not None
            assert value.hour == 6
            assert value.minute == 0

    def test_native_value_no_next_on(self, mock_coordinator, mock_entry, sample_schedule):
        """Test native value when no next ON."""
        mock_coordinator.data = MagicMock()
        mock_coordinator.data.get_group.return_value = sample_schedule

        sensor = NextOnSensor(mock_coordinator, 12, mock_entry)

        with patch.object(sample_schedule, 'get_next_on_or_maybe', return_value=None):
            assert sensor.native_value is None

    def test_unique_id(self, mock_coordinator, mock_entry):
        """Test unique_id format."""
        sensor = NextOnSensor(mock_coordinator, 12, mock_entry)
        assert sensor.unique_id == "test_entry_id_next_on"


class TestNextOffSensor:
    """Tests for NextOffSensor."""

    def test_native_value(self, mock_coordinator, mock_entry, sample_schedule):
        """Test native value returns next OFF time."""
        mock_coordinator.data = MagicMock()
        mock_coordinator.data.get_group.return_value = sample_schedule

        sensor = NextOffSensor(mock_coordinator, 12, mock_entry)

        next_off_slot = TimeSlot(hour=12, minute=0, state=STATE_OFF)
        with patch.object(sample_schedule, 'get_next_off', return_value=next_off_slot):
            value = sensor.native_value
            assert value is not None
            assert value.hour == 12
            assert value.minute == 0

    def test_native_value_no_next_off(self, mock_coordinator, mock_entry, sample_schedule):
        """Test native value when no next OFF."""
        mock_coordinator.data = MagicMock()
        mock_coordinator.data.get_group.return_value = sample_schedule

        sensor = NextOffSensor(mock_coordinator, 12, mock_entry)

        with patch.object(sample_schedule, 'get_next_off', return_value=None):
            assert sensor.native_value is None

    def test_unique_id(self, mock_coordinator, mock_entry):
        """Test unique_id format."""
        sensor = NextOffSensor(mock_coordinator, 12, mock_entry)
        assert sensor.unique_id == "test_entry_id_next_off"
