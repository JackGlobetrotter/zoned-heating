import logging
import datetime
from custom_components.zoned_heating.base_entity import BaseEntity

from homeassistant.const import (
    STATE_ON,
)
from homeassistant.core import HomeAssistant

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import ToggleEntity


from . import const

from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)
from .const import DOMAIN
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

    switch = ZonedHeaterSwitch(coordinator)

    async_add_entities([switch])

    switches = [ZonedHeaterSwitch(coordinator, coordinator.data.switch, "state")]

    # Create the binary sensors.
    async_add_entities(switches)


class ZonedHeaterSwitch(ToggleEntity, BaseEntity):
    _attr_name = "Zoned Heating"

    def __init__(
        self,
    ):
        super().__init__()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        state = await self.async_get_last_state()
        if state:
            self._enabled = state.state == STATE_ON
            self._override_active = state.attributes.get(const.ATTR_OVERRIDE_ACTIVE)
            self._temperature_increase = state.attributes.get(
                const.ATTR_TEMPERATURE_INCREASE
            )
            self._stored_controller_setpoint = state.attributes.get(
                const.ATTR_STORED_CONTROLLER_SETPOINT
            )
            self._stored_controller_state = state.attributes.get(
                const.ATTR_STORED_CONTROLLER_STATE
            )
            self._current_zone = state.attributes.get(const.ATTR_CURRENT_ZONE)
        else:
            self._enabled = True

        if self._enabled:
            await self.async_start_state_listeners()
        await self.async_calculate_override()

    async def async_will_remove_from_hass(self):
        """remove entity from hass."""
        await self.async_stop_state_listeners()

    @property
    def is_on(self) -> bool | None:
        """Return if the binary sensor is on."""
        # This needs to enumerate to true or false
        return self.coordinator.data.enabled

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self.coordinator.async_switch(True)
        await self.coordinator.async_refresh()

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self.coordinator.async_switch(False)
        await self.coordinator.async_refresh()

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        # Add any additional attributes you want on your sensor.
        attrs = {}
        attrs["last_rebooted"] = self.coordinator.get_device_parameter(
            self.device_id, "last_reboot"
        )
        return attrs
