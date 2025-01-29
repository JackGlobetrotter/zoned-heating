import logging
from datetime import datetime, timedelta
import voluptuous as vol

from homeassistant.components.climate import (ClimateDevice, PLATFORM_SCHEMA, ATTR_TARGET_TEMP_LOW)
from homeassistant.components.climate.const import (ATTR_TARGET_TEMP_HIGH,
                                                    CURRENT_HVAC_OFF, CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL,
                                                    HVAC_MODE_AUTO, HVAC_MODE_OFF, HVAC_MODE_COOL,
                                                    HVAC_MODE_HEAT, SUPPORT_TARGET_TEMPERATURE,
                                                    SUPPORT_PRESET_MODE, SUPPORT_TARGET_TEMPERATURE_RANGE)

from homeassistant.const import (CONF_NAME, CONF_USERNAME, CONF_PASSWORD, CONF_ROOM, ATTR_STATE,
                                 TEMP_CELSIUS, ATTR_TEMPERATURE, TEMP_FAHRENHEIT)

from homeassistant.const import STATE_ON, STATE_OFF

import homeassistant.helpers.config_validation as cv

import requests

_LOGGER = logging.getLogger(__name__)
DEPENDENCIES = ['switch', 'sensor']
REQUIREMENTS = ['requests']

DEFAULT_NAME = 'Zoned Heating Thermostat (Mirror)'
DEFAULT_TIMEOUT = 3

ATTR_MODE = 'mode'
STATE_UNKNOWN = 'unknown'

SUPPORT_FLAGS = (SUPPORT_PRESET_MODE | SUPPORT_TARGET_TEMPERATURE_RANGE)

def setup_platform(hass, config, add_devices, discovery_info=None):

    add_devices([Thermostat(DEFAULT_NAME, client)])

class Thermostat(ClimateDevice):
    """Representation of a Climate device."""

    HVAC_MODE_LIST = (
        HVAC_MODE_OFF,
        HVAC_MODE_HEAT
    )

    def __init__(self, name, client):
        """Initialize the thermostat."""
        self._name = name
        self._cl = client
        self._current_temp = 0
        self._current_state = self.IDLE
        self._current_operation = ''
        self._current_unit = 0
        self._tempSetMark = 0
        self._heating_state = False
        self._hvac_mode = HVAC_MODE_OFF
        self.update()

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def should_poll(self):
        """Polling needed for thermostat."""
        _LOGGER.debug("Should_Poll called")
        return True

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    def get_target_temperature(self):
        """
        To get the tartget temperature using the Preset info
        :return:
        """
        return self._target_temperature

    def update(self):
        """Update the data from the thermostat."""
        _LOGGER.debug("Update called")


    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the device specific state attributes."""
        return {
            ATTR_MODE: self._current_state,
            'season_mode': self.hvac_mode,
            'heating_state': self._heating_state
        }

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        if self._current_unit == '0':
            return TEMP_CELSIUS
        else:
            return TEMP_FAHRENHEIT

    @property
    def hvac_mode(self):
        """Current mode."""
        return self._hvac_mode

    @property
    def hvac_action(self):
        """Current mode."""
        if self._heating_state:
            mode = self.hvac_mode
            if mode == HVAC_MODE_HEAT:
                return CURRENT_HVAC_HEAT
        else:
            return CURRENT_HVAC_OFF

    @property
    def hvac_modes(self):
        """List of available operation modes."""
        return self.HVAC_MODE_LIST

    def set_hvac_mode(self, hvac_mode):
        """Set HVAC mode (COOL, HEAT)."""
        _LOGGER.debug("set_hvac_mode called, should be disabled")

    def set_preset_mode(self, preset_mode):
        """Set HVAC mode (comfort, home, sleep, Party, Off)."""

        _LOGGER.debug("set_preset_mode called, should be disabled")

    def set_temperature(self, **kwargs):
        """Set new target temperature."""

        _LOGGER.debug("set_temperature called, should be disabled")
