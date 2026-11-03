"""Config and options flows."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.chernivtsi_outages.api import FetchError
from custom_components.chernivtsi_outages.const import (
    CONF_GROUPS,
    DOMAIN,
    SEARCH_URL,
    SITE_URL,
    TELEGRAM_URL,
)

from .common import kyiv, setup
from .helpers import FakeWeb, fixture


async def _start(hass: HomeAssistant):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_user_flow(hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, fixture("site_schedule.html"))
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["description_placeholders"] == {"search_url": SEARCH_URL}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_GROUPS: ["12", "3"]}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Chernivtsi Power Outages"
    assert result["data"] == {CONF_GROUPS: [3, 12]}


async def test_user_flow_needs_a_group(hass: HomeAssistant, web: FakeWeb) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_GROUPS: []})
    assert result["errors"] == {CONF_GROUPS: "no_groups"}


async def test_user_flow_works_with_only_the_channel(hass: HomeAssistant, web: FakeWeb) -> None:
    web.set(SITE_URL, FetchError("down"))
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_GROUPS: ["1"]})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_cannot_connect(hass: HomeAssistant, web: FakeWeb) -> None:
    web.set(SITE_URL, FetchError("down"))
    web.set(TELEGRAM_URL, FetchError("down"))
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_GROUPS: ["1"]})
    assert result["errors"] == {"base": "cannot_connect"}

    web.set(SITE_URL, fixture("site_schedule.html"))
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_GROUPS: ["1"]})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_single_entry(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, fixture("site_schedule.html"))
    await setup(hass)
    result = await _start(hass)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options_flow(
    hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, fixture("site_schedule.html"))
    entry = await setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_GROUPS: []})
    assert result["errors"] == {CONF_GROUPS: "no_groups"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_GROUPS: ["5", "12"]}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_GROUPS: [5, 12]}
    assert entry.runtime_data.groups == [5, 12]
