import logging
from datetime import datetime, timedelta
import voluptuous as vol


from custom_components.zoned_heating.switch import DEFAULT_SWITCH_ID
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_FAN_MODE,
    ATTR_HUMIDITY,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    ATTR_AUX_HEAT,
    ATTR_MAX_HUMIDITY,
    ATTR_SWING_HORIZONTAL_MODE,
    ATTR_SWING_MODE,
    SERVICE_SET_AUX_HEAT,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_SWING_HORIZONTAL_MODE,
    SERVICE_SET_SWING_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACAction,
    HVACMode,
    PRESET_NONE,
)

from homeassistant.const import (
    ATTR_FRIENDLY_NAME,
    ATTR_TEMPERATURE,
    UnitOfTemperature,
    ATTR_TEMPERATURE,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    UnitOfTemperature,
)


from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv


from homeassistant import config_entries
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.hass_dict import HassKey
from .const import DOMAIN
from .base_entity import BaseEntity
from .coordinator import (
    ZonedHeatingDataCoordinator,
    async_set_temperature as utility_cliamte_async_set_temperature,
)

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ["switch", "sensor"]
REQUIREMENTS = ["requests"]

DEFAULT_NAME = "Zoned Heating Thermostat (Mirror)"

DATA_COMPONENT: HassKey[EntityComponent[ClimateEntity]] = HassKey(DOMAIN)
SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate device for zoned heating platform."""
    coordinator: ZonedHeatingDataCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ].coordinator

    async_add_entities([VirtualThermostat(coordinator)])


class VirtualThermostat(BaseEntity, ClimateEntity):
    """Representation of a Climate device."""

    _attr_unique_id = DEFAULT_SWITCH_ID
    _attr_has_entity_name = True
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_name = None
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _attr_preset_mode = PRESET_NONE
    _attr_preset_modes = [PRESET_NONE]
    _attr_current_temperature = 0
    _attr_target_temperature = 0
    _attr_hvac_mode = HVACMode.OFF
    _enable_turn_on_off_backwards_compatibility = False
    _current_temperature = None
    _target_temperature = None
    _current_state = HVACAction.OFF
    _current_operation = ""
    _current_unit = 0
    _heating_state = True
    _hvac_mode = HVACMode.HEAT

    def __init__(self, coordinator) -> None:
        """Initialize the thermostat."""

        self._name = DEFAULT_NAME
        super().__init__(coordinator)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self):
        await self.coordinator.async_on_remove()
        return await super().async_will_remove_from_hass()

    def update(self):
        """Update the data from the thermostat."""
        if self.coordinator.data.current_zone is not None:
            trv = self.hass.states.get(self.coordinator.data.current_zone)
            self._attr_current_temperature = float(
                trv.attributes.get(ATTR_CURRENT_TEMPERATURE)
            )
            self._attr_target_temperature = float(trv.attributes.get(ATTR_TEMPERATURE))
            self._name = trv.attributes.get(ATTR_FRIENDLY_NAME)
            self._attr_hvac_action = trv.attributes.get(ATTR_HVAC_ACTION)
            if (
                trv.attributes.get(ATTR_HVAC_MODE) is None
                and trv.attributes.get(ATTR_HVAC_ACTION) == HVACAction.HEATING
            ):
                self._attr_hvac_mode = HVACMode.HEAT
            else:
                self._attr_hvac_mode = trv.attributes.get(ATTR_HVAC_MODE)

            self._attr_target_temperature_low = float(
                trv.attributes.get(ATTR_TEMPERATURE)
            )
            self._attr_target_temperature_high = float(
                trv.attributes.get(ATTR_TEMPERATURE)
            )
        else:
            self._attr_target_temperature = None
            self._attr_current_temperature = None
            self._name = DEFAULT_NAME
            self._attr_hvac_action = HVACAction.OFF
            self._attr_hvac_mode = HVACMode.OFF
            self._attr_target_temperature = None
            self._attr_target_temperature_low = None
            self._attr_target_temperature_high = None
        _LOGGER.debug("Update called")
        # self.async_write_ha_state()

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    def _handle_coordinator_update(self):
        self.update()
        return super()._handle_coordinator_update()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.HEAT and not self.coordinator.data.enabled:
            await self.coordinator.async_enable_zoned_heating()
        elif hvac_mode == HVACMode.OFF and self.coordinator.data.enabled:
            await self.coordinator.async_disable_zoned_heating()
        else:
            _LOGGER.debug(
                "HVAC Mode Handling not implemented for {}. Zoned Heating is {}".format(
                    hvac_mode, self.coordinator.data.enabled
                )
            )

    async def async_set_temperature(self, **kwargs):
        await utility_cliamte_async_set_temperature(
            self.hass, self.coordinator.data.current_zone, kwargs["temperature"]
        )
