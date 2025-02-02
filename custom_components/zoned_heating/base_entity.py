import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.const import (
    STATE_ON,
)
from homeassistant import config_entries
from .const import DOMAIN
from .coordinator import ZonedHeatingDataCoordinator
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from . import const

_LOGGER = logging.getLogger(__name__)


class BaseEntity(CoordinatorEntity, RestoreEntity):
    coordinator: ZonedHeatingDataCoordinator

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ZonedHeatingDataCoordinator,
    ) -> None:
        """Initialise entity."""
        super().__init__(coordinator)
        _LOGGER.debug("Called init for device")

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.

        _LOGGER.debug("Updating device")  #: {}".format(vars(self)))
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        await self.coordinator.async_on_remove()
