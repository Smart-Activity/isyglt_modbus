"""Constants for the ISYGLT integration."""

DOMAIN = "isyglt"
PLATFORMS = ["light", "switch", "cover", "climate"]

CONF_CONTROLLER_NAME = "controller_name"
CONF_TIMEOUT = "timeout"
CONF_LIGHTS = "lights"
CONF_SWITCHES = "switches"
CONF_COVERS = "covers"
CONF_CLIMATES = "climates"
CONF_AREA_ID = "area_id"
CONF_SLAVE = "slave"
CONF_REGISTER = "register"  # Legacy v0.3 raw Modbus register field.
CONF_ENTITY_UID = "entity_uid"
CONF_LIGHT_KIND = "light_kind"
CONF_ISYGLT_ADDRESS = "isyglt_address"
CONF_ON_VALUE = "on_value"
CONF_OFF_VALUE = "off_value"
CONF_COMMAND_REGISTER = "command_register"
CONF_POSITION_REGISTER = "position_register"
CONF_OPEN_VALUE = "open_value"
CONF_CLOSE_VALUE = "close_value"
CONF_STOP_VALUE = "stop_value"
CONF_CURRENT_TEMP_REGISTER = "current_temperature_register"
CONF_TARGET_TEMP_REGISTER = "target_temperature_register"
CONF_TEMP_SCALE = "temperature_scale"
CONF_MIN_TEMP = "min_temperature"
CONF_MAX_TEMP = "max_temperature"
CONF_TEMP_STEP = "temperature_step"

LIGHT_KIND_DIMMABLE = "dimmable"
LIGHT_KIND_SWITCHABLE = "switchable"

DEFAULT_CONTROLLER_NAME = "ISYGLT Hoofdcontroller"
DEFAULT_PORT = 502
DEFAULT_TIMEOUT = 3
DEFAULT_SLAVE = 1
DEFAULT_REGISTER = 8
DEFAULT_SCAN_INTERVAL = 5
DEFAULT_LIGHT_KIND = LIGHT_KIND_DIMMABLE
DEFAULT_LIGHT_ADDRESS = "8"

MODBUS_MIN = 0
MODBUS_MAX = 100
