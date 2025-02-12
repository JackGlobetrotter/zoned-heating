"""The zoned_heating component."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from collections.abc import Callable
from . import const

from dataclasses import dataclass
from .coordinator import ZonedHeatingDataCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE, Platform.SWITCH]


@dataclass
class RuntimeData:
    """Class to hold your data."""

    coordinator: DataUpdateCoordinator
    cancel_update_listener: Callable


async def async_setup(hass, config):
    """Track states and offer events for sensors."""
    return True


type ZonedHeatingConfigEntry = ConfigEntry[RuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: ZonedHeatingConfigEntry):
    """Set up Zoned Heating integration from a config entry."""

    # _async_import_options_from_data_if_missing(hass, entry)

    hass.data.setdefault(const.DOMAIN, {})
    hass.data[const.DOMAIN][entry.entry_id] = {}

    coordinator = ZonedHeatingDataCoordinator(hass, entry)
    hass.data[const.DOMAIN][entry.entry_id] = coordinator

    await coordinator.async_refresh()  # async_config_entry_first_refresh()

    cancel_update_listener = entry.async_on_unload(
        entry.add_update_listener(_async_update_listener)
    )
    entry.runtime_data = RuntimeData(coordinator, cancel_update_listener)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _async_update_listener(hass: HomeAssistant, config_entry):
    """Handle config options update."""
    # Reload the integration when the options change.
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when it changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    """Unload Zoned Heating config entry."""
    # unload_ok = await hass.config_entries.async_unload_platforms(
    #     entry,
    #     [Platform.CLIMATE],
    # )
    #
    # if unload_ok:
    #     hass.data[const.DOMAIN].pop(entry.entry_id)
    #
    # return unload_ok

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
