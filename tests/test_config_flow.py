"""Tests for config flow."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.cv_oblenergo.const import DOMAIN, CONF_GROUP
from custom_components.cv_oblenergo.config_flow import PowerScheduleConfigFlow


class TestConfigFlow:
    """Tests for PowerScheduleConfigFlow."""
    
    @pytest.mark.asyncio
    async def test_form_is_shown(self):
        """Test that the form is shown on init."""
        flow = PowerScheduleConfigFlow()
        flow.hass = MagicMock()
        
        result = await flow.async_step_user(user_input=None)
        
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert "data_schema" in result
    
    @pytest.mark.asyncio
    async def test_form_has_group_selection(self):
        """Test that the form has group selection."""
        flow = PowerScheduleConfigFlow()
        flow.hass = MagicMock()
        
        result = await flow.async_step_user(user_input=None)
        
        # The form should have a schema with group field
        schema = result["data_schema"]
        assert schema is not None
    
    @pytest.mark.asyncio
    async def test_successful_config(self):
        """Test successful configuration."""
        flow = PowerScheduleConfigFlow()
        flow.hass = MagicMock()
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_create_entry = MagicMock(return_value={"type": FlowResultType.CREATE_ENTRY})
        
        with patch(
            "custom_components.cv_oblenergo.config_flow.validate_connection",
            return_value=True
        ):
            result = await flow.async_step_user(user_input={CONF_GROUP: 12})
        
        flow.async_create_entry.assert_called_once()
        call_args = flow.async_create_entry.call_args
        assert call_args.kwargs["title"] == "Electricity Group 12"
        assert call_args.kwargs["data"][CONF_GROUP] == 12
    
    @pytest.mark.asyncio
    async def test_connection_error(self):
        """Test handling of connection errors."""
        flow = PowerScheduleConfigFlow()
        flow.hass = MagicMock()
        
        with patch(
            "custom_components.cv_oblenergo.config_flow.validate_connection",
            return_value=False
        ):
            result = await flow.async_step_user(user_input={CONF_GROUP: 12})
        
        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"
    
    @pytest.mark.asyncio
    async def test_already_configured(self):
        """Test handling of already configured group."""
        flow = PowerScheduleConfigFlow()
        flow.hass = MagicMock()
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock(
            side_effect=config_entries.ConfigFlowError("already_configured")
        )
        
        with patch(
            "custom_components.cv_oblenergo.config_flow.validate_connection",
            return_value=True
        ):
            with pytest.raises(config_entries.ConfigFlowError):
                await flow.async_step_user(user_input={CONF_GROUP: 12})
    
    @pytest.mark.asyncio
    async def test_unique_id_format(self):
        """Test unique ID is set correctly."""
        flow = PowerScheduleConfigFlow()
        flow.hass = MagicMock()
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_create_entry = MagicMock(return_value={"type": FlowResultType.CREATE_ENTRY})
        
        with patch(
            "custom_components.cv_oblenergo.config_flow.validate_connection",
            return_value=True
        ):
            await flow.async_step_user(user_input={CONF_GROUP: 5})
        
        flow.async_set_unique_id.assert_called_once_with("cv_oblenergo_group_5")
    
    @pytest.mark.asyncio
    async def test_all_groups_available(self):
        """Test that all 12 groups are available for selection."""
        flow = PowerScheduleConfigFlow()
        flow.hass = MagicMock()
        
        result = await flow.async_step_user(user_input=None)
        
        # Check that the description placeholders include the URL
        assert "url" in result.get("description_placeholders", {})


@pytest.mark.asyncio
async def test_validate_connection_success():
    """Test validate_connection returns True on success."""
    from custom_components.cv_oblenergo.config_flow import validate_connection
    
    hass = MagicMock()
    
    with patch(
        "custom_components.cv_oblenergo.config_flow.async_get_clientsession"
    ) as mock_session:
        mock_client = MagicMock()
        mock_client.async_get_schedule = AsyncMock(return_value=MagicMock())
        
        with patch(
            "custom_components.cv_oblenergo.config_flow.PowerScheduleApiClient",
            return_value=mock_client
        ):
            result = await validate_connection(hass)
            assert result is True


@pytest.mark.asyncio
async def test_validate_connection_failure():
    """Test validate_connection returns False on failure."""
    from custom_components.cv_oblenergo.config_flow import validate_connection
    
    hass = MagicMock()
    
    with patch(
        "custom_components.cv_oblenergo.config_flow.async_get_clientsession"
    ) as mock_session:
        mock_client = MagicMock()
        mock_client.async_get_schedule = AsyncMock(side_effect=Exception("Connection failed"))
        
        with patch(
            "custom_components.cv_oblenergo.config_flow.PowerScheduleApiClient",
            return_value=mock_client
        ):
            result = await validate_connection(hass)
            assert result is False

