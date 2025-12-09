"""Tests for sensor platform."""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

from homeassistant.core import HomeAssistant

from custom_components.cv_oblenergo.const import (
    DOMAIN,
    STATE_ON,
    STATE_OFF,
    STATE_MAYBE,
)
from custom_components.cv_oblenergo.sensor import (
    PowerStateSensor,
    NextChangeSensor,
    OffHoursRemainingSensor,
    OnHoursRemainingSensor,
    ScheduleSensor,
)


class TestPowerStateSensor:
    """Tests for PowerStateSensor."""
    
    def test_native_value_on(self, sample_schedule_data, mock_config_entry):
        """Test native value when power is ON."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = PowerStateSensor(coordinator, 12, mock_config_entry)
        
        # Mock current time to be during ON period (00:00)
        with patch('custom_components.cv_oblenergo.api.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 9, 0, 15)
            # Group 12 at 00:00 is ON
            assert sensor.native_value == STATE_ON
    
    def test_native_value_off(self, sample_schedule_data, mock_config_entry):
        """Test native value when power is OFF."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = PowerStateSensor(coordinator, 12, mock_config_entry)
        
        # Group 12 at 01:00 (slot 2) is OFF
        with patch('custom_components.cv_oblenergo.api.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 9, 1, 15)
            assert sensor.native_value == STATE_OFF
    
    def test_native_value_no_data(self, mock_config_entry):
        """Test native value when no data available."""
        coordinator = MagicMock()
        coordinator.data = None
        
        sensor = PowerStateSensor(coordinator, 12, mock_config_entry)
        assert sensor.native_value is None
    
    def test_icon_on(self, sample_schedule_data, mock_config_entry):
        """Test icon when power is ON."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = PowerStateSensor(coordinator, 12, mock_config_entry)
        
        with patch.object(sensor, 'native_value', STATE_ON):
            assert sensor.icon == "mdi:transmission-tower"
    
    def test_icon_off(self, sample_schedule_data, mock_config_entry):
        """Test icon when power is OFF."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = PowerStateSensor(coordinator, 12, mock_config_entry)
        
        with patch.object(sensor, 'native_value', STATE_OFF):
            assert sensor.icon == "mdi:transmission-tower-off"
    
    def test_icon_maybe(self, sample_schedule_data, mock_config_entry):
        """Test icon when power is MAYBE."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = PowerStateSensor(coordinator, 12, mock_config_entry)
        
        with patch.object(sensor, 'native_value', STATE_MAYBE):
            assert sensor.icon == "mdi:transmission-tower-import"
    
    def test_extra_state_attributes(self, sample_schedule_data, mock_config_entry):
        """Test extra state attributes."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = PowerStateSensor(coordinator, 12, mock_config_entry)
        
        attrs = sensor.extra_state_attributes
        assert "group" in attrs
        assert attrs["group"] == 12
        assert "schedule_date" in attrs


class TestNextChangeSensor:
    """Tests for NextChangeSensor."""
    
    def test_native_value(self, sample_schedule_data, mock_config_entry):
        """Test native value returns datetime."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = NextChangeSensor(coordinator, 12, mock_config_entry)
        
        value = sensor.native_value
        # Should return a datetime or None
        assert value is None or isinstance(value, datetime)
    
    def test_extra_state_attributes(self, sample_schedule_data, mock_config_entry):
        """Test extra state attributes include next state info."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = NextChangeSensor(coordinator, 12, mock_config_entry)
        
        attrs = sensor.extra_state_attributes
        assert "group" in attrs
        assert attrs["group"] == 12


class TestOffHoursRemainingSensor:
    """Tests for OffHoursRemainingSensor."""
    
    def test_native_value(self, sample_schedule_data, mock_config_entry):
        """Test native value returns hours."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = OffHoursRemainingSensor(coordinator, 12, mock_config_entry)
        
        value = sensor.native_value
        assert value is None or isinstance(value, (int, float))
    
    def test_unit_of_measurement(self, sample_schedule_data, mock_config_entry):
        """Test unit of measurement is hours."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = OffHoursRemainingSensor(coordinator, 12, mock_config_entry)
        
        assert sensor.native_unit_of_measurement == "h"


class TestOnHoursRemainingSensor:
    """Tests for OnHoursRemainingSensor."""
    
    def test_native_value(self, sample_schedule_data, mock_config_entry):
        """Test native value returns hours."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = OnHoursRemainingSensor(coordinator, 12, mock_config_entry)
        
        value = sensor.native_value
        assert value is None or isinstance(value, (int, float))
    
    def test_unit_of_measurement(self, sample_schedule_data, mock_config_entry):
        """Test unit of measurement is hours."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = OnHoursRemainingSensor(coordinator, 12, mock_config_entry)
        
        assert sensor.native_unit_of_measurement == "h"


class TestScheduleSensor:
    """Tests for ScheduleSensor."""
    
    def test_native_value(self, sample_schedule_data, mock_config_entry):
        """Test native value returns date string."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = ScheduleSensor(coordinator, 12, mock_config_entry)
        
        value = sensor.native_value
        assert value == "2025-12-09"
    
    def test_extra_state_attributes(self, sample_schedule_data, mock_config_entry):
        """Test extra state attributes include full schedule."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = ScheduleSensor(coordinator, 12, mock_config_entry)
        
        attrs = sensor.extra_state_attributes
        assert "group" in attrs
        assert "schedule" in attrs
        assert "off_periods" in attrs
        assert "on_periods" in attrs
        assert "total_off_hours" in attrs
        assert "total_on_hours" in attrs
        
        # Schedule should have 48 entries
        assert len(attrs["schedule"]) == 48

