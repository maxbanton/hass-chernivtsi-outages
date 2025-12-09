"""Tests for data update coordinator."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import timedelta

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.cv_oblenergo.coordinator import PowerScheduleCoordinator
from custom_components.cv_oblenergo.const import DEFAULT_UPDATE_INTERVAL


class TestPowerScheduleCoordinator:
    """Tests for PowerScheduleCoordinator."""
    
    def test_init(self):
        """Test coordinator initialization."""
        hass = MagicMock(spec=HomeAssistant)
        session = MagicMock()
        
        coordinator = PowerScheduleCoordinator(hass, session, group=12)
        
        assert coordinator.group == 12
        assert coordinator.update_interval == timedelta(minutes=DEFAULT_UPDATE_INTERVAL)
    
    def test_init_default_group(self):
        """Test coordinator initialization without group."""
        hass = MagicMock(spec=HomeAssistant)
        session = MagicMock()
        
        coordinator = PowerScheduleCoordinator(hass, session)
        
        assert coordinator.group is None
    
    @pytest.mark.asyncio
    async def test_async_update_data_success(self, sample_schedule_data):
        """Test successful data update."""
        hass = MagicMock(spec=HomeAssistant)
        session = MagicMock()
        
        coordinator = PowerScheduleCoordinator(hass, session, group=12)
        coordinator.api = MagicMock()
        coordinator.api.async_get_schedule = AsyncMock(return_value=sample_schedule_data)
        
        result = await coordinator._async_update_data()
        
        assert result == sample_schedule_data
        coordinator.api.async_get_schedule.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_update_data_client_error(self):
        """Test data update with client error."""
        hass = MagicMock(spec=HomeAssistant)
        session = MagicMock()
        
        coordinator = PowerScheduleCoordinator(hass, session, group=12)
        coordinator.api = MagicMock()
        coordinator.api.async_get_schedule = AsyncMock(
            side_effect=aiohttp.ClientError("Connection failed")
        )
        
        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()
        
        assert "Error communicating with API" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_async_update_data_generic_error(self):
        """Test data update with generic error."""
        hass = MagicMock(spec=HomeAssistant)
        session = MagicMock()
        
        coordinator = PowerScheduleCoordinator(hass, session, group=12)
        coordinator.api = MagicMock()
        coordinator.api.async_get_schedule = AsyncMock(
            side_effect=Exception("Unknown error")
        )
        
        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()
        
        assert "Error fetching data" in str(exc_info.value)
    
    def test_update_interval(self):
        """Test update interval is set correctly."""
        hass = MagicMock(spec=HomeAssistant)
        session = MagicMock()
        
        coordinator = PowerScheduleCoordinator(hass, session, group=12)
        
        # Should be 30 minutes as per const.py
        assert coordinator.update_interval == timedelta(minutes=30)

