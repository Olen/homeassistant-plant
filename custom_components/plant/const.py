"""Constants"""

DOMAIN = "plant"
DOMAIN_SENSOR = "sensor"
DOMAIN_PLANTBOOK = "openplantbook"

REQUEST_TIMEOUT = 30

# ATTRs are used by machines
ATTR_BATTERY = "battery"
ATTR_BRIGHTNESS = "brightness"
ATTR_MOISTURE = "moisture"
ATTR_CONDUCTIVITY = "conductivity"
ATTR_ILLUMINANCE = "illuminance"
ATTR_HUMIDITY = "humidity"
ATTR_PPFD = "ppfd"
ATTR_MMOL = "mmol"
ATTR_MOL = "mol"
ATTR_DLI = "dli"

ATTR_TEMPERATURE = "temperature"
ATTR_PROBLEM = "problem"
ATTR_SENSORS = "sensors"
ATTR_SENSOR = "sensor"
ATTR_METERS = "meters"
ATTR_THRESHOLDS = "thresholds"
ATTR_ENTITY = "entity"
ATTR_SELECT = "select"
ATTR_OPTIONS = "options"
ATTR_PLANT = "plant"
ATTR_SPECIES = "species"
ATTR_IMAGE = "image"
ATTR_SEARCH_FOR = "search_for"

# Readings are used by humans
READING_BATTERY = "battery"
READING_TEMPERATURE = "temperature"
READING_MOISTURE = "soil moisture"
READING_CONDUCTIVITY = "conductivity"
READING_ILLUMINANCE = "illuminance"
READING_HUMIDITY = "air humidity"
READING_PPFD = "ppfd (mol)"
READING_MMOL = "mmol"
READING_MOL = "mol"
READING_DLI = "dli"


ATTR_MAX_ILLUMINANCE_HISTORY = "max_illuminance"
ATTR_LIMITS = "limits"
ATTR_MIN = "min"
ATTR_MAX = "max"
ATTR_CURRENT = "current"


DEFAULT_MIN_BATTERY_LEVEL = 20
DEFAULT_MIN_TEMPERATURE = 10
DEFAULT_MAX_TEMPERATURE = 40
DEFAULT_MIN_MOISTURE = 20
DEFAULT_MAX_MOISTURE = 60
DEFAULT_MIN_CONDUCTIVITY = 500
DEFAULT_MAX_CONDUCTIVITY = 3000
DEFAULT_MIN_ILLUMINANCE = 0
DEFAULT_MAX_ILLUMINANCE = 100000
DEFAULT_MIN_HUMIDITY = 20
DEFAULT_MAX_HUMIDITY = 60
DEFAULT_MIN_MMOL = 2000
DEFAULT_MAX_MMOL = 20000
DEFAULT_MIN_MOL = 2
DEFAULT_MAX_MOL = 30
DEFAULT_MIN_DLI = 2
DEFAULT_MAX_DLI = 30

DEFAULT_IMAGE_PATH = "/config/www/images/plants/"
DEFAULT_IMAGE_LOCAL_URL = "/local/images/plants/"


DATA_SOURCE = "data_source"
DATA_SOURCE_PLANTBOOK = "OpenPlantbook"
DATA_SOURCE_MANUAL = "Manual"
DATA_SOURCE_DEFAULT = "Default values"
DATA_UPDATED = "plant_data_updated"


UNIT_PPFD = "mol/s⋅m²"
UNIT_MICRO_PPFD = "μmol/s⋅m²"
UNIT_DLI = "mol/d⋅m²"
UNIT_MICRO_DLI = "μmol/d⋅m²"
UNIT_CONDUCTIVITY = "μS/cm"

FLOW_WRONG_PLANT = "wrong_plant"
FLOW_RIGHT_PLANT = "right_plant"
FLOW_ERROR_NOTFOUND = "opb_notfound"
FLOW_STRING_DESCRIPTION = "desc"

FLOW_PLANT_INFO = "plant_info"
FLOW_PLANT_SPECIES = "plant_species"
FLOW_PLANT_NAME = "plant_name"
FLOW_PLANT_IMAGE = "image_url"
FLOW_PLANT_LIMITS = "limits"

FLOW_SENSOR_TEMPERATURE = "temperature_sensor"
FLOW_SENSOR_MOISTURE = "moisture_sensor"
FLOW_SENSOR_CONDUCTIVITY = "conductivity_sensor"
FLOW_SENSOR_ILLUMINANCE = "illuminance_sensor"
FLOW_SENSOR_HUMIDITY = "humidity_sensor"

FLOW_TEMP_UNIT = "temperature_unit"
FLOW_ILLUMINANCE_TRIGGER = "illuminance_trigger"
FLOW_HUMIDITY_TRIGGER = "humidity_trigger"
FLOW_TEMPERATURE_TRIGGER = "temperature_trigger"
FLOW_DLI_TRIGGER = "dli_trigger"
FLOW_MOISTURE_TRIGGER = "moisture_trigger"
FLOW_CONDUCTIVITY_TRIGGER = "conductivity_trigger"

FLOW_FORCE_SPECIES_UPDATE = "force_update"

ICON_CONDUCTIVITY = "mdi:spa-outline"
ICON_DLI = "mdi:counter"
ICON_HUMIDITY = "mdi:water-percent"
ICON_ILLUMINANCE = "mdi:brightness-6"
ICON_MOISTURE = "mdi:water"
ICON_TEMPERATURE = "mdi:thermometer"

OPB_GET = "get"
OPB_SEARCH = "search"
OPB_SEARCH_RESULT = "search_result"
OPB_PID = "pid"
OPB_DISPLAY_PID = "display_pid"

# PPFD to DLI: /1000000 * 3600 to get from microseconds to hours
PPFD_DLI_FACTOR = 0.0036
# See https://www.apogeeinstruments.com/conversion-ppfd-to-lux/
# This equals normal sunlight
DEFAULT_LUX_TO_PPFD = 0.0185


SERVICE_REPLACE_SENSOR = "replace_sensor"

STATE_LOW = "Low"
STATE_HIGH = "High"
STATE_DLI_LOW = "Previous DLI Low"
STATE_DLI_HIGH = "Previous DLI High"


CONF_MIN_BATTERY_LEVEL = f"min_{ATTR_BATTERY}"
CONF_MIN_TEMPERATURE = f"min_{ATTR_TEMPERATURE}"
CONF_MAX_TEMPERATURE = f"max_{ATTR_TEMPERATURE}"
CONF_MIN_MOISTURE = f"min_{ATTR_MOISTURE}"
CONF_MAX_MOISTURE = f"max_{ATTR_MOISTURE}"
CONF_MIN_CONDUCTIVITY = f"min_{ATTR_CONDUCTIVITY}"
CONF_MAX_CONDUCTIVITY = f"max_{ATTR_CONDUCTIVITY}"
CONF_MIN_ILLUMINANCE = f"min_{ATTR_ILLUMINANCE}"
CONF_MAX_ILLUMINANCE = f"max_{ATTR_ILLUMINANCE}"
CONF_MIN_HUMIDITY = f"min_{ATTR_HUMIDITY}"
CONF_MAX_HUMIDITY = f"max_{ATTR_HUMIDITY}"
CONF_MIN_MMOL = f"min_{ATTR_MMOL}"
CONF_MAX_MMOL = f"max_{ATTR_MMOL}"
CONF_MIN_MOL = f"min_{ATTR_MOL}"
CONF_MAX_MOL = f"max_{ATTR_MOL}"
CONF_MIN_DLI = f"min_{ATTR_DLI}"
CONF_MAX_DLI = f"max_{ATTR_DLI}"
CONF_MIN_BRIGHTNESS = "min_brightness"  # DEPRECATED. Only used for config migration
CONF_MAX_BRIGHTNESS = "max_brightness"  # DEPRECATED. Only used for config migration


CONF_CHECK_DAYS = "check_days"
CONF_SPECIES = "species"
CONF_IMAGE = "entity_picture"

CONF_PLANTBOOK = "openplantbook"
CONF_PLANTBOOK_MAPPING = {
    CONF_MIN_TEMPERATURE: "min_temp",
    CONF_MAX_TEMPERATURE: "max_temp",
    CONF_MIN_MOISTURE: "min_soil_moist",
    CONF_MAX_MOISTURE: "max_soil_moist",
    CONF_MIN_ILLUMINANCE: "min_light_lux",
    CONF_MAX_ILLUMINANCE: "max_light_lux",
    CONF_MIN_CONDUCTIVITY: "min_soil_ec",
    CONF_MAX_CONDUCTIVITY: "max_soil_ec",
    CONF_MIN_HUMIDITY: "min_env_humid",
    CONF_MAX_HUMIDITY: "max_env_humid",
    CONF_MIN_MMOL: "min_light_mmol",
    CONF_MAX_MMOL: "max_light_mmol",
}
