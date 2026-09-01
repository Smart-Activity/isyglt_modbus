"""Constants for the ISYGLT integration."""

DOMAIN = "isyglt"
PLATFORMS = ["light", "switch", "cover", "button", "climate", "scene"]

CONF_CONTROLLER_NAME = "controller_name"
CONF_TIMEOUT = "timeout"
CONF_LIGHTS = "lights"
CONF_SWITCHES = "switches"
CONF_COVERS = "covers"
CONF_CLIMATES = "climates"
CONF_SCENES = "scenes"
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
CONF_UP_ADDRESS = "up_address"
CONF_DOWN_ADDRESS = "down_address"
CONF_SCENE_TRIGGER_ADDRESS = "scene_trigger_address"
CONF_SCENE_FEEDBACK_ADDRESS = "scene_feedback_address"
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
DEFAULT_SWITCH_ADDRESS = "1.1"
DEFAULT_COVER_UP_ADDRESS = "1.1"
DEFAULT_COVER_DOWN_ADDRESS = "1.2"
COVER_SHORT_PRESS_SECONDS = 0.2
COVER_LONG_PRESS_SECONDS = 3.0
SCENE_ACTIVATE_PRESS_SECONDS = 0.2
SCENE_STORE_PRESS_SECONDS = 5.0
DEFAULT_SCENE_TRIGGER_ADDRESS = "1.1"
DEFAULT_SCENE_FEEDBACK_ADDRESS = "1.1"


# Native Climate configuration (v0.8+)
CONF_TARGET_TEMP_ADDRESS = "target_temperature_address"
CONF_CURRENT_TEMP_ADDRESS = "current_temperature_address"
CONF_IS_AIRCO = "is_airco"
CONF_FAN_HIGH_NE = "fan_high_ne"
CONF_FAN_HIGH_NA = "fan_high_na"
CONF_FAN_MEDIUM_NE = "fan_medium_ne"
CONF_FAN_MEDIUM_NA = "fan_medium_na"
CONF_FAN_LOW_NE = "fan_low_ne"
CONF_FAN_LOW_NA = "fan_low_na"
CONF_AIRCO_POWER_NE = "airco_power_ne"
CONF_AIRCO_POWER_NA = "airco_power_na"

DEFAULT_CLIMATE_TARGET_ADDRESS = "1"
DEFAULT_CLIMATE_CURRENT_ADDRESS = "1"
DEFAULT_CLIMATE_MIN_TEMP = 10
DEFAULT_CLIMATE_MAX_TEMP = 40
DEFAULT_CLIMATE_TEMP_STEP = 1
DEFAULT_CLIMATE_TEMP_SCALE = 1
CLIMATE_BUTTON_PRESS_SECONDS = 0.2

MODBUS_MIN = 0
MODBUS_MAX = 100
