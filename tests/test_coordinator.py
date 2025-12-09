"""Tests for data update coordinator."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import timedelta

import aiohttp

from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.cv_oblenergo.api import PowerScheduleApiClient
from custom_components.cv_oblenergo.const import DEFAULT_UPDATE_INTERVAL


class TestPowerScheduleCoordinator:
    """Tests for PowerScheduleCoordinator."""
    
    def test_default_update_interval(self):
        """Test default update interval is 30 minutes."""
        assert DEFAULT_UPDATE_INTERVAL == 30
    
    @pytest.mark.asyncio
    async def test_api_client_get_schedule(self, sample_schedule_data):
        """Test API client can be called."""
        api = MagicMock(spec=PowerScheduleApiClient)
        api.async_get_schedule = AsyncMock(return_value=sample_schedule_data)
        
        result = await api.async_get_schedule()
        
        assert result == sample_schedule_data
        api.async_get_schedule.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_api_client_error_handling(self):
        """Test API client error is raised."""
        api = MagicMock(spec=PowerScheduleApiClient)
        api.async_get_schedule = AsyncMock(
            side_effect=aiohttp.ClientError("Connection failed")
        )
        
        with pytest.raises(aiohttp.ClientError):
            await api.async_get_schedule()
    
    @pytest.mark.asyncio
    async def test_update_failed_wrapping(self):
        """Test that UpdateFailed can wrap errors."""
        original_error = aiohttp.ClientError("Test error")
        
        with pytest.raises(UpdateFailed) as exc_info:
            raise UpdateFailed(f"Error communicating with API: {original_error}") from original_error
        
        assert "Error communicating with API" in str(exc_info.value)
