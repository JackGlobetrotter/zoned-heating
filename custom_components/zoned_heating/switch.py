import logging
import datetime
from custom_components.zoned_heating.base_entity import BaseEntity

from homeassistant.const import (
    STATE_ON,
)
from homeassistant.core import HomeAssistant

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import ToggleEntity

from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)
from .const import DOMAIN, DEFAULT_SWITCH_ID
from .coordinator import ZonedHeatingDataCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch(es) for zoned heating platform."""

    coordinator: ZonedHeatingDataCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ].coordinator

    # Create the binary sensors.
    async_add_entities([ZonedHeaterSwitch(coordinator)])


class ZonedHeaterSwitch(BaseEntity, ToggleEntity):
    _attr_name = "Zoned Heating"
    _attr_unique_id = DEFAULT_SWITCH_ID

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._enabled = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        state = await self.async_get_last_state()

        if state:
            self._enabled = state.state == STATE_ON
        else:
            self._enabled = True
        await self.coordinator.async_get_initial_switch_state(state)

    @property
    def is_on(self) -> bool | None:
        """Return if the binary sensor is on."""
        # This needs to enumerate to true or false
        return self.coordinator.data.enabled

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self.coordinator.async_enable_zoned_heating()

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self.coordinator.async_disable_zoned_heating()
