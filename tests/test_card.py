"""The schedule card: served by the integration and loaded on the dashboards."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.lovelace.resources import (
    ResourceStorageCollection,
    ResourceYAMLCollection,
)
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from custom_components.chernivtsi_outages.card import CARD_URL, FRONTEND_PATH
from custom_components.chernivtsi_outages.const import DOMAIN, SITE_URL

from .common import kyiv, setup
from .helpers import FakeWeb, fixture


@pytest.fixture(autouse=True)
def frontend(hass: HomeAssistant, web: FakeWeb, freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to(kyiv(18, 49))
    web.set(SITE_URL, fixture("site_schedule.html"))
    hass.config.components.add("frontend")
    hass.http = MagicMock(async_register_static_paths=AsyncMock())


@pytest.fixture(params=["dataclass", "dict"])
def resources(hass: HomeAssistant, request) -> ResourceStorageCollection:
    """The UI managed resources, in both shapes Home Assistant has kept them in."""
    collection = ResourceStorageCollection(hass, MagicMock(async_load=AsyncMock(return_value={})))
    if request.param == "dict":
        hass.data["lovelace"] = {"resources": collection}
    else:
        hass.data["lovelace"] = SimpleNamespace(resources=collection)
    return collection


async def _card_url(hass: HomeAssistant) -> str:
    return f"{CARD_URL}?v={(await async_get_integration(hass, DOMAIN)).version}"


def _urls(resources: ResourceStorageCollection) -> list[str]:
    return [item["url"] for item in resources.async_items()]


async def test_card_files_are_served(hass: HomeAssistant, resources) -> None:
    register = hass.http.async_register_static_paths
    await setup(hass)
    (paths,), _ = register.call_args
    assert paths[0].url_path == f"/{DOMAIN}/frontend"
    assert (FRONTEND_PATH / "chernivtsi-outages-card.js").is_file()


async def test_card_is_added_to_the_dashboard_resources(hass: HomeAssistant, resources) -> None:
    with patch("custom_components.chernivtsi_outages.card.add_extra_js_url") as add_url:
        await setup(hass)
    add_url.assert_not_called()
    assert _urls(resources) == [await _card_url(hass)]


async def test_update_moves_the_resource_to_the_new_version(hass: HomeAssistant, resources) -> None:
    await resources.async_create_item({"res_type": "module", "url": "/local/other-card.js"})
    await resources.async_create_item({"res_type": "module", "url": f"{CARD_URL}?v=0.9.0"})
    await resources.async_create_item({"res_type": "js", "url": CARD_URL})
    await setup(hass)
    assert _urls(resources) == ["/local/other-card.js", await _card_url(hass)]


async def test_yaml_dashboards_load_the_card_with_the_page(hass: HomeAssistant) -> None:
    hass.data["lovelace"] = SimpleNamespace(resources=ResourceYAMLCollection([]))
    with patch("custom_components.chernivtsi_outages.card.add_extra_js_url") as add_url:
        await setup(hass)
    add_url.assert_called_once_with(hass, await _card_url(hass))


async def test_removing_the_entry_removes_the_resource(hass: HomeAssistant, resources) -> None:
    entry = await setup(hass)
    await hass.config_entries.async_remove(entry.entry_id)
    assert _urls(resources) == []
