import logging
import datetime
import homeassistant.util.dt as dt_util
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.switch import SwitchEntity

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, ATTR_TEMPERATURE, Platform, ATTR_ENTITY_ID
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    ATTR_HVAC_ACTION,
    ATTR_MIN_TEMP,
    ATTR_MAX_TEMP,
    HVACMode,
    HVACAction,
    ATTR_CURRENT_TEMPERATURE,
    ATTR_TARGET_TEMP_STEP,
)
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_point_in_time,
)
from homeassistant.core import DOMAIN, HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import DOMAIN, HomeAssistant
from homeassistant.components.persistent_notification import async_create


class CustomAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return f"[DataCoordinator] {msg}", kwargs


_LOGGER = CustomAdapter(logging.getLogger(__name__))

from . import const
from .util import parse_state
from homeassistant.helpers.event import (
    async_track_state_change_event,
)


from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    ATTR_HVAC_ACTION,
    HVACAction,
    ATTR_CURRENT_TEMPERATURE,
)
from .util import (
    parse_state,
    async_set_hvac_mode,
    async_set_temperature,
    async_set_switch_state,
    compute_domain,
)


class ZonedHeatingData:
    """Class for zoned heating data."""

    controller_entity: ClimateEntity
    zone_entities: list[ClimateEntity]
    max_setpoint: int
    controller_delay_time: int
    absolute_mode: bool

    enabled: bool
    ignore_controller_state_change_timer: bool
    override_active: bool
    temperature_increase: int
    stored_controller_setpoint: int
    stored_controller_state: int
    current_zone: ClimateEntity


class ZonedHeatingDataCoordinator(DataUpdateCoordinator):
    data: ZonedHeatingData

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=self._async_update_data,
            update_interval=None,
            always_update=True,
        )

        controller = config_entry.options.get(const.CONF_CONTROLLER)
        zones = config_entry.options.get(const.CONF_ZONES, [])
        max_setpoint = config_entry.options.get(const.CONF_MAX_SETPOINT)
        controller_delay_time = config_entry.options.get(
            const.CONF_CONTROLLER_DELAY_TIME, const.DEFAULT_CONTROLLER_DELAY_TIME
        )
        absolute_mode = config_entry.options.get(
            const.CONF_ABSOLUTE_MODE, const.DEFAULT_ABSOLUTE_MODE
        )
        self.hass = hass
        self.data = ZonedHeatingData()
        self.data.controller_entity = controller
        self.data.zone_entities = zones
        self.data.max_setpoint = max_setpoint
        self.data.controller_delay_time = controller_delay_time
        self.data.absolute_mode = absolute_mode

        self.data.enabled = False
        self._state_listeners = []
        self.data.ignore_controller_state_change_timer = None
        self.data.override_active = False
        self.data.temperature_increase = 0
        self.data.stored_controller_setpoint = None
        self.data.stored_controller_state = None
        self.data.current_zone = None
        self._is_initialized = False

    async def _async_update_data(self):
        """Do the usual update"""
        _LOGGER.debug("_async_update_data called")  # with: {}".format(vars(self.data)))
        if self.data:
            return self.data

    async def _async_setup(self) -> None:
        """Do initialization logic."""
        self.data = ZonedHeatingData()
        _LOGGER.debug("_async_setup called")  # with: {}".format(vars(self.data)))

    async def async_get_initial_switch_state(self, state):
        _LOGGER.debug("async_get_initial_data called")

        if state:
            self.data.enabled = state.state == STATE_ON
            self.data.override_active = state.attributes.get(const.ATTR_OVERRIDE_ACTIVE)
            self.data.temperature_increase = state.attributes.get(
                const.ATTR_TEMPERATURE_INCREASE
            )
            self.data.stored_controller_setpoint = state.attributes.get(
                const.ATTR_STORED_CONTROLLER_SETPOINT
            )
            self.data.stored_controller_state = state.attributes.get(
                const.ATTR_STORED_CONTROLLER_STATE
            )
            self.data.current_zone = state.attributes.get(const.ATTR_CURRENT_ZONE)
        else:
            self.data.enabled = True

        if self.data.enabled:
            await self.async_start_state_listeners()
        await self.async_calculate_override()

    async def async_on_remove(self):
        await self.async_stop_state_listeners()

    async def async_shutdown(self) -> None:
        """Run shutdown clean up."""
        await self.async_stop_state_listeners()
        return await super().async_shutdown()

    async def async_start_state_listeners(self):
        """start watching for state changes of controller / zone entities"""
        await self.async_stop_state_listeners()
        if not len(self.data.zone_entities) or not self.data.controller_entity:
            return
        self._state_listeners = [
            async_track_state_change_event(
                self.hass,
                self.data.controller_entity,
                self.async_controller_state_changed,
            ),
            async_track_state_change_event(
                self.hass,
                self.data.zone_entities,
                self.async_zone_state_changed,
            ),
        ]

    @callback
    async def async_controller_state_changed(self, event):
        """fired when controller entity changes"""
        if (
            self.data.ignore_controller_state_change_timer
            or not self.data.override_active
        ):
            return
        old_state = parse_state(event.data["old_state"])
        new_state = parse_state(event.data["new_state"])

        if new_state[ATTR_TEMPERATURE] != old_state[ATTR_TEMPERATURE]:
            # if controller setpoint has changed, make sure to store it
            _LOGGER.debug(
                "Storing controller setpoint={}".format(new_state[ATTR_TEMPERATURE])
            )
            self.data.stored_controller_setpoint = new_state[ATTR_TEMPERATURE]
            self.async_set_updated_data(self.data)

        if (
            new_state[ATTR_HVAC_MODE] != old_state[ATTR_HVAC_MODE]
            and new_state[ATTR_HVAC_MODE] == HVACAction.OFF
        ):
            _LOGGER.debug("Controller was turned off, disable zones")
            await self.async_turn_off_zones()

    @callback
    async def async_zone_state_changed(self, event):
        """fired when zone entity changes"""
        entity = event.data["entity_id"]
        old_state = parse_state(event.data["old_state"])
        new_state = parse_state(event.data["new_state"])

        if (
            old_state[ATTR_TEMPERATURE] != new_state[ATTR_TEMPERATURE]
            and isinstance(new_state[ATTR_TEMPERATURE], float)
            and isinstance(new_state[ATTR_CURRENT_TEMPERATURE], float)
        ):
            # setpoint of a zone was updated, check whether controller needs to be updated
            _LOGGER.debug(
                "Zone {} updated: setpoint={}".format(
                    entity, new_state[ATTR_TEMPERATURE]
                )
            )
            await self.async_calculate_override()

        if (
            old_state[ATTR_HVAC_ACTION] != new_state[ATTR_HVAC_ACTION]
            or old_state[ATTR_HVAC_MODE] != new_state[ATTR_HVAC_MODE]
        ):
            # action of a zone was updated, check whether controller needs to be updated
            _LOGGER.debug(
                "Zone {} updated: action={}".format(entity, new_state[ATTR_HVAC_ACTION])
            )
            await self.async_calculate_override()

    async def async_calculate_override(self):
        """calculate whether override should be active and determine setpoint"""

        zone_id = None
        temperature_increase = 0.0
        set_temp = 0.0
        override_active = False
        zone_id = None

        states = [
            parse_state(self.hass.states.get(entity), entity)
            for entity in self.data.zone_entities
        ]

        for index, state in enumerate(states):
            if (
                self.data.enabled
                and state[ATTR_HVAC_ACTION] == HVACAction.HEATING
                and state[ATTR_HVAC_MODE] != HVACAction.OFF
                and state[ATTR_TEMPERATURE]
                - state[ATTR_CURRENT_TEMPERATURE]  # is positif
                > temperature_increase
            ):
                temperature_increase = (
                    state[ATTR_TEMPERATURE] - state[ATTR_CURRENT_TEMPERATURE]
                )
                zone_id = index
                override_active = True
                if self.data.absolute_mode:
                    set_temp = state[ATTR_TEMPERATURE]
                else:
                    set_temp = temperature_increase

        _LOGGER.debug(
            "Absolute temp debug ={}, override_active={}, new set_temp={}".format(
                temperature_increase, override_active, set_temp
            )
        )

        if (not self.data.override_active and not override_active) or (
            self.data.temperature_increase == temperature_increase
            and override_active == self.data.override_active
        ):
            if zone_id is not None:
                self.data.current_zone = states[zone_id][ATTR_ENTITY_ID]
            self.async_set_updated_data(self.data)
            return

        _LOGGER.debug(
            "Updated override temperature_increase={}, override_active={}, new set_temp={}".format(
                temperature_increase, override_active, set_temp
            )
        )
        if zone_id is not None:
            self.data.current_zone = states[zone_id][ATTR_ENTITY_ID]

        if override_active and not self.data.override_active:
            await self.async_start_override_mode(set_temp)
        elif not override_active and self.data.override_active:
            await self.async_stop_override_mode()
        else:
            await self.async_update_override_setpoint(set_temp)

        if self._is_initialized:
            self.async_set_updated_data(self.data)
        else:
            self._is_initialized = True
        await self._async_update_data()

    async def async_start_override_mode(self, temperature_increase: float):
        """Start the override of the controller"""

        self.data.override_active = True
        current_state = parse_state(self.hass.states.get(self.data.controller_entity))
        # store current controller entity settings for later
        _LOGGER.debug("Storing controller state={}".format(current_state))
        self.data.stored_controller_state = current_state[ATTR_HVAC_MODE]
        self.data.stored_controller_setpoint = current_state[ATTR_TEMPERATURE]

        if current_state[ATTR_HVAC_MODE] != HVACMode.HEAT:
            # uupdate to heat mode if needed
            await self._ignore_controller_state_changes()
            if compute_domain(self.data.controller_entity) == Platform.CLIMATE:
                await async_set_hvac_mode(
                    self.hass, self.data.controller_entity, HVACMode.HEAT
                )
            elif compute_domain(self.data.controller_entity) == Platform.SWITCH:
                await async_set_switch_state(
                    self.hass, self.data.controller_entity, STATE_ON
                )

        await self.async_update_override_setpoint(temperature_increase)

    async def async_stop_override_mode(self):
        """Stop the override of the controller and revert its prior settings"""
        if not self.data.override_active:
            return

        _LOGGER.debug("Stopping override mode")
        self.data.override_active = False
        self.data.temperature_increase = 0

        current_controller_state = parse_state(
            self.hass.states.get(self.data.controller_entity)
        )

        if (
            current_controller_state[ATTR_HVAC_MODE]
            != self.data.stored_controller_state
            and self.data.stored_controller_state is not None
        ):
            if compute_domain(self.data.controller_entity) == Platform.CLIMATE:
                await async_set_hvac_mode(
                    self.hass,
                    self.data.controller_entity,
                    self.data.stored_controller_state,
                )
            elif compute_domain(self.data.controller_entity) == Platform.SWITCH:
                await async_set_switch_state(
                    self.hass,
                    self.data.controller_entity,
                    self.data.stored_controller_state,
                )

        if (
            current_controller_state[ATTR_TEMPERATURE]
            != self.data.stored_controller_setpoint
            and isinstance(self.data.stored_controller_setpoint, float)
            and compute_domain(self.data.controller_entity) == Platform.CLIMATE
        ):
            await async_set_temperature(
                self.hass,
                self.data.controller_entity,
                self.data.stored_controller_setpoint,
            )

        self.data.stored_controller_setpoint = None
        self.data.stored_controller_state = None
        self.data.current_zone = None

    async def async_update_override_setpoint(self, temperature: float):
        """Update the override setpoint of the controller"""

        self.data.temperature_increase = temperature

        controller_setpoint = 0
        if self.data.stored_controller_state == HVACMode.HEAT and isinstance(
            self.data.stored_controller_setpoint, float
        ):
            controller_setpoint = self.data.stored_controller_setpoint

        controller_state = self.hass.states.get(self.data.controller_entity)
        current_state = parse_state(controller_state)

        override_setpoint = 0
        new_setpoint = 0

        if not self.data.absolute_mode and isinstance(
            current_state[ATTR_CURRENT_TEMPERATURE], float
        ):
            override_setpoint = min(
                [
                    current_state[ATTR_CURRENT_TEMPERATURE]
                    + self.data.temperature_increase,
                    self.data.max_setpoint,
                ]
            )

        if self.data.absolute_mode:
            override_setpoint = min(temperature, self.data.max_setpoint)

        new_setpoint = max([override_setpoint, controller_setpoint])

        _LOGGER.debug(
            "Updating override setpoint for set_temp={}, current_temp={}, mode={}".format(
                new_setpoint, current_state[ATTR_TEMPERATURE], self.data.absolute_mode
            )
        )

        if (
            new_setpoint != current_state[ATTR_TEMPERATURE]
            and compute_domain(self.data.controller_entity) == Platform.CLIMATE
        ):
            setpoint_resolution = controller_state.attributes.get(
                ATTR_TARGET_TEMP_STEP, 0.5
            )

            min_set_temp = controller_state.attributes.get(ATTR_MIN_TEMP, 0)
            if new_setpoint < min_set_temp:
                _LOGGER.warning(
                    "Setpoint({}) is lower than than authorized by controller min_setpoint ({}). Adjusting setpoint to {}".format(
                        new_setpoint,
                        min_set_temp,
                        min_set_temp,
                    )
                )
                new_setpoint = min_set_temp

            max_set_temp = controller_state.attributes.get(
                ATTR_MAX_TEMP, self.data.max_setpoint
            )
            if new_setpoint > max_set_temp:
                _LOGGER.warning(
                    "Setpoint ({}) exceeds controllers max setpoint ({}), Adjusting to {}".format(
                        new_setpoint,
                        max_set_temp,
                        max_set_temp,
                    )
                )
            else:
                new_setpoint = max_set_temp

            new_setpoint = (
                round(new_setpoint / setpoint_resolution) * setpoint_resolution
            )

            _LOGGER.debug("Updating override setpoint={}".format(new_setpoint))
            await self._ignore_controller_state_changes()
            await async_set_temperature(
                self.hass, self.data.controller_entity, new_setpoint
            )

    @callback
    async def async_turn_off_zones(self):
        """turn off all zones"""
        entity_list = [
            entity
            for entity in self.data.zone_entities
            if parse_state(self.hass.states.get(entity))[ATTR_HVAC_MODE]
            == HVACMode.HEAT
        ]
        if not len(entity_list):
            return

        _LOGGER.debug("Turning off zones {}".format(", ".join(entity_list)))
        await async_set_hvac_mode(self.hass, entity_list, HVACMode.OFF)
        self.data.current_zone = None

    async def _ignore_controller_state_changes(self):
        """temporarily stop watching for state changes of the controller"""
        if self.data.ignore_controller_state_change_timer:
            self.data.ignore_controller_state_change_timer()

        _LOGGER.debug("start ignoring controller state changes")

        now = dt_util.utcnow()
        delay = datetime.timedelta(seconds=self.data.controller_delay_time)

        @callback
        async def timer_finished(now):
            _LOGGER.debug("stop ignoring controller state changes")
            self.data.ignore_controller_state_change_timer = None

        self.data.ignore_controller_state_change_timer = async_track_point_in_time(
            self.hass, timer_finished, now + delay
        )

    async def async_stop_state_listeners(self):
        """stop watching for state changes of controller / zone entities"""
        while len(self._state_listeners):
            self._state_listeners.pop()()

    async def async_enable_zoned_heating(self):
        if self.data.enabled:
            return
        self.data.enabled = True
        await self.async_start_state_listeners()
        await self.async_calculate_override()
        # self.async_set_updated_data(self.data)
        _LOGGER.debug("Zoned heating turned on")

    async def async_disable_zoned_heating(self):
        if not self.data.enabled:
            return
            # async_create(self.hass, "Zoned Heating", "Zoned Heating has been turned off")
        self.data.enabled = False
        await self.async_stop_state_listeners()
        await self.async_calculate_override()
        # self.async_set_updated_data(self.data)
        _LOGGER.debug("Zoned heating turned off")
