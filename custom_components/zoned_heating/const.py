"""Store constants."""

VERSION = "1.1.2"
DOMAIN = "zoned_heating"
NAME = "Zoned Heating"
DATA = "data"
UPDATE_LISTENER = "update_listener"

CONF_CONTROLLER = "controller"
CONF_ZONES = "zones"
CONF_MAX_SETPOINT = "max_setpoint"
CONF_CONTROLLER_DELAY_TIME = "controller_delay_time"
CONF_ABSOLUTE_MODE = "absolute_mode"
CONF_CONTROLLER_MANUAL = "controller_manual"
CONF_CONTROLLER_MANUAL_CONFIG = "controller_manual_config"
CONF_CONTROLLER_MANUAL_MODE = "controller_manual_mode"
CONF_CONTROLLER_MANUAL_SETPOINT = "controller_manual_setpoint"


DEFAULT_MAX_SETPOINT = 21
DEFAULT_CONTROLLER_DELAY_TIME = 10
DEFAULT_ABSOLUTE_MODE = False

DEFAULT_SWITCH_ID = "zoned_heating_internal_switch"
DEFAULT_CLIMATE_ID = "zoned_heating_internal_climate"
DEFAULT_ENTITY_IDS = "zoned_heating"
DEFAULT_CONTROLLER_MANUAL = False
DEFAULT_CONTROLLER_MODE = "heat"
DEFAULT_CONTROLLER_SETPOINT = 20

ATTR_OVERRIDE_ACTIVE = "override_active"
ATTR_TEMPERATURE_INCREASE = "temperature_increase"
ATTR_STORED_CONTROLLER_STATE = "stored_controller_state"
ATTR_STORED_CONTROLLER_SETPOINT = "stored_controller_setpoint"
ATTR_CURRENT_ZONE = "current_zone"
