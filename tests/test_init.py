"""Tests for integration setup."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState

from custom_components.cv_oblenergo.const import DOMAIN, CONF_GROUP
from custom_components.cv_oblenergo import async_setup_entry, async_unload_entry


class TestIntegrationSetup:
    """Tests for integration setup and teardown."""
    
    @pytest.mark.asyncio
    async def test_async_setup_entry_success(self, mock_config_entry, sample_schedule_data):
        """Test successful setup of config entry."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        
        # Mock the coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.data = sample_schedule_data
        
        # Mock forward entry setups
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        
        with patch(
            "custom_components.cv_oblenergo.async_get_clientsession"
        ) as mock_session:
            with patch(
                "custom_components.cv_oblenergo.PowerScheduleCoordinator",
                return_value=mock_coordinator
            ):
                result = await async_setup_entry(hass, mock_config_entry)
        
        assert result is True
        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id in hass.data[DOMAIN]
    
    @pytest.mark.asyncio
    async def test_async_setup_entry_coordinator_error(self, mock_config_entry):
        """Test setup fails when coordinator fails."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        with patch(
            "custom_components.cv_oblenergo.async_get_clientsession"
        ):
            with patch(
                "custom_components.cv_oblenergo.PowerScheduleCoordinator",
                return_value=mock_coordinator
            ):
                with pytest.raises(Exception):
                    await async_setup_entry(hass, mock_config_entry)
    
    @pytest.mark.asyncio
    async def test_async_unload_entry_success(self, mock_config_entry):
        """Test successful unload of config entry."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {DOMAIN: {mock_config_entry.entry_id: MagicMock()}}
        
        hass.config_entries = MagicMock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        result = await async_unload_entry(hass, mock_config_entry)
        
        assert result is True
        assert mock_config_entry.entry_id not in hass.data[DOMAIN]
    
    @pytest.mark.asyncio
    async def test_async_unload_entry_failure(self, mock_config_entry):
        """Test failed unload of config entry."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {DOMAIN: {mock_config_entry.entry_id: MagicMock()}}
        
        hass.config_entries = MagicMock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)
        
        result = await async_unload_entry(hass, mock_config_entry)
        
        assert result is False
        # Entry should still be in data since unload failed
        assert mock_config_entry.entry_id in hass.data[DOMAIN]

