"""Config flow for Chernivtsi Power Schedule integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PowerScheduleApiClient
from .const import DOMAIN, CONF_GROUP, NUM_GROUPS

_LOGGER = logging.getLogger(__name__)


async def validate_connection(hass: HomeAssistant) -> bool:
    """Validate we can connect to the API."""
    session = async_get_clientsession(hass)
    client = PowerScheduleApiClient(session)

    try:
        await client.async_get_schedule()
        return True
    except Exception:
        return False


class PowerScheduleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Chernivtsi Power Schedule."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate connection
            if not await validate_connection(self.hass):
                errors["base"] = "cannot_connect"
            else:
                group = user_input.get(CONF_GROUP)

                # Create unique ID and title based on selected group
                await self.async_set_unique_id(f"cv_oblenergo_group_{group}")
                self._abort_if_unique_id_configured()
                title = f"Electricity Group {group}"

                return self.async_create_entry(
                    title=title,
                    data={CONF_GROUP: group},
                )

        # Build group selection list (1-12 only, no "all groups" option)
        group_options = {}
        for i in range(1, NUM_GROUPS + 1):
            group_options[i] = f"Group {i} (Група {i})"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_GROUP): vol.In(group_options),
            }),
            errors=errors,
            description_placeholders={
                "url": "https://oblenergo.cv.ua/shutdowns/",
            },
        )


class PowerScheduleOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Power Schedule."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
        )
