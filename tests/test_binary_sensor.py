"""Tests for binary sensor platform."""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

from custom_components.cv_oblenergo.const import (
    DOMAIN,
    STATE_ON,
    STATE_OFF,
    STATE_MAYBE,
)
from custom_components.cv_oblenergo.binary_sensor import PowerConnectivitySensor


class TestPowerConnectivitySensor:
    """Tests for PowerConnectivitySensor."""
    
    def test_is_on_when_power_on(self, sample_schedule_data, mock_config_entry):
        """Test is_on returns True when power is ON."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = PowerConnectivitySensor(coordinator, 12, mock_config_entry)
        
        # Group 12 at 00:00 is ON based on fixture
        with patch('custom_components.cv_oblenergo.api.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 9, 0, 15)
            assert sensor.is_on is True
    
    def test_is_on_when_power_off(self, sample_schedule_data, mock_config_entry):
        """Test is_on returns False when power is OFF."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = PowerConnectivitySensor(coordinator, 12, mock_config_entry)
        
        # Group 12 at 01:00 (slot 2) is OFF
        with patch('custom_components.cv_oblenergo.api.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 9, 1, 15)
            assert sensor.is_on is False
    
    def test_is_on_when_power_maybe(self, sample_schedule_data, mock_config_entry):
        """Test is_on returns True when power is MAYBE (not definitively off)."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = PowerConnectivitySensor(coordinator, 12, mock_config_entry)
        
        # Group 12 at 05:00 (slot 10) is MAYBE
        with patch('custom_components.cv_oblenergo.api.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 9, 5, 15)
            assert sensor.is_on is True  # MAYBE is treated as possibly ON
    
    def test_is_on_no_data(self, mock_config_entry):
        """Test is_on returns None when no data available."""
        coordinator = MagicMock()
        coordinator.data = None
        
        sensor = PowerConnectivitySensor(coordinator, 12, mock_config_entry)
        assert sensor.is_on is None
    
    def test_is_on_no_group(self, sample_schedule_data, mock_config_entry):
        """Test is_on returns None when group not found."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = PowerConnectivitySensor(coordinator, 99, mock_config_entry)  # Non-existent group
        assert sensor.is_on is None
    
    def test_icon_on(self, sample_schedule_data, mock_config_entry):
        """Test icon when power is ON."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = PowerConnectivitySensor(coordinator, 12, mock_config_entry)
        
        # Test when is_on returns True
        with patch('custom_components.cv_oblenergo.api.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 9, 0, 15)
            assert sensor.icon == "mdi:power-plug"
    
    def test_icon_off(self, sample_schedule_data, mock_config_entry):
        """Test icon when power is OFF."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = PowerConnectivitySensor(coordinator, 12, mock_config_entry)
        
        # Test when is_on returns False
        with patch('custom_components.cv_oblenergo.api.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 9, 1, 15)
            assert sensor.icon == "mdi:power-plug-off"
    
    def test_extra_state_attributes(self, sample_schedule_data, mock_config_entry):
        """Test extra state attributes."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = PowerConnectivitySensor(coordinator, 12, mock_config_entry)
        
        attrs = sensor.extra_state_attributes
        assert "group" in attrs
        assert attrs["group"] == 12
        assert "schedule_date" in attrs
    
    def test_unique_id(self, sample_schedule_data, mock_config_entry):
        """Test unique ID format."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = PowerConnectivitySensor(coordinator, 12, mock_config_entry)
        
        assert sensor.unique_id == "test_entry_id_power"
    
    def test_device_info(self, sample_schedule_data, mock_config_entry):
        """Test device info."""
        coordinator = MagicMock()
        coordinator.data = sample_schedule_data
        
        sensor = PowerConnectivitySensor(coordinator, 12, mock_config_entry)
        
        device_info = sensor.device_info
        assert device_info is not None
        assert "identifiers" in device_info
        assert "name" in device_info
        assert device_info["name"] == "CV"
        assert device_info["model"] == "Group 12"
