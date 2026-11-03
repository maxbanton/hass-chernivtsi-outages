"""Config flow: pick the outage groups to follow."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import Client, FetchError
from .const import CONF_GROUPS, DOMAIN, GROUPS, SEARCH_URL, SITE_URL, TELEGRAM_URL

TITLE = "Chernivtsi Power Outages"


def _schema(groups: list[int]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_GROUPS, default=[str(g) for g in groups]): SelectSelector(
                SelectSelectorConfig(
                    options=[str(g) for g in GROUPS],
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                    translation_key="group",
                )
            )
        }
    )


async def _reachable(hass: HomeAssistant) -> bool:
    from . import user_agent

    client = Client(async_get_clientsession(hass), user_agent(hass))
    for url in (SITE_URL, TELEGRAM_URL):
        try:
            await client.fetch(url)
        except FetchError:
            continue
        return True
    return False


def _validate(user_input: dict[str, Any]) -> tuple[list[int], dict[str, str]]:
    groups = sorted(int(g) for g in user_input.get(CONF_GROUPS, []))
    return groups, ({} if groups else {CONF_GROUPS: "no_groups"})


class OutagesConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        groups: list[int] = []
        if user_input is not None:
            groups, errors = _validate(user_input)
            if not errors and not await _reachable(self.hass):
                errors["base"] = "cannot_connect"
            if not errors:
                return self.async_create_entry(title=TITLE, data={CONF_GROUPS: groups})
        return self.async_show_form(
            step_id="user",
            data_schema=_schema(groups),
            errors=errors,
            description_placeholders={"search_url": SEARCH_URL},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return OutagesOptionsFlow()


class OutagesOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        from . import entry_groups

        errors: dict[str, str] = {}
        groups = entry_groups(self.config_entry)
        if user_input is not None:
            groups, errors = _validate(user_input)
            if not errors:
                return self.async_create_entry(data={CONF_GROUPS: groups})
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(groups),
            errors=errors,
            description_placeholders={"search_url": SEARCH_URL},
        )
