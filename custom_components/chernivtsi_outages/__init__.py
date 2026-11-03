"""Chernivtsi Power Outages: scheduled outages of the Chernivtsi region in Home Assistant."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_loaded_integration

from .api import Client
from .card import async_add_card_resource, async_remove_card_resource, async_serve_card
from .const import CONF_GROUPS, DOMAIN, REPO_URL, STORAGE_VERSION
from .coordinator import OutageCoordinator
from .entity import device_identifier

PLATFORMS = [Platform.BINARY_SENSOR, Platform.CALENDAR, Platform.EVENT, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type OutageConfigEntry = ConfigEntry[OutageCoordinator]


def user_agent(hass: HomeAssistant) -> str:
    """Says who is asking, so the site's admins can tell and reach the project."""
    version = async_get_loaded_integration(hass, DOMAIN).version
    return f"HomeAssistant/{HA_VERSION} hass-chernivtsi-outages/{version} (+{REPO_URL})"


def entry_groups(entry: ConfigEntry) -> list[int]:
    return sorted(int(g) for g in entry.options.get(CONF_GROUPS, entry.data[CONF_GROUPS]))


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    await async_serve_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: OutageConfigEntry) -> bool:
    await async_add_card_resource(hass)
    coordinator = OutageCoordinator(
        hass,
        entry,
        Client(async_get_clientsession(hass), user_agent(hass)),
        entry_groups(entry),
    )
    await coordinator.async_load()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    registry = dr.async_get(hass)
    wanted = {device_identifier(group) for group in coordinator.groups}
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        if not device.identifiers & wanted:
            registry.async_update_device(device.id, remove_config_entry_id=entry.entry_id)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(
        async_track_time_change(hass, coordinator.async_tick, minute=(0, 30), second=0)
    )
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: OutageConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: OutageConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: OutageConfigEntry) -> None:
    await Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}").async_remove()
    await async_remove_card_resource(hass)
