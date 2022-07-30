"""Constants"""
from homeassistant.const import ATTR_TEMPERATURE

DOMAIN = "plant"

ATTR_TEMPERATURE = "temperature"
ATTR_PROBLEM = "problem"
ATTR_SENSORS = "sensors"
ATTR_METERS = "meters"
ATTR_THRESHOLDS = "thresholds"

PROBLEM_NONE = "none"
ATTR_MAX_ILLUMINANCE_HISTORY = "max_illuminance"
ATTR_SPECIES = "species"
ATTR_LIMITS = "limits"
ATTR_IMAGE = "image"
ATTR_MIN = "min"
ATTR_MAX = "max"

READING_BATTERY = "battery"
READING_TEMPERATURE = ATTR_TEMPERATURE
READING_MOISTURE = "moisture"
READING_CONDUCTIVITY = "conductivity"
READING_ILLUMINANCE = "illuminance"
READING_HUMIDITY = "humidity"
READING_MMOL = "mmol"
READING_MOL = "mol"
READING_DLI = "dli"

UNIT_PPFD = "mol/s⋅m²"
UNIT_MICRO_PPFD = "μmol/s⋅m²"
UNIT_DLI = "mol/d⋅m²"
UNIT_MICRO_DLI = "μmol/d⋅m²"
UNIT_CONDUCTIVITY = "μS/cm"

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

FLOW_ILLUMINANCE_TRIGGER = "illuminance_trigger"

OPB_SEARCH = "search"
OPB_SEARCH_RESULT = "search_result"
OPB_PID = "pid"
OPB_DISPLAY_PID = "display_pid"

# PPFD to DLI: /1000000 * 3600 to get from microseconds to hours
PPFD_DLI_FACTOR = 0.0036

CONF_MIN_BATTERY_LEVEL = f"min_{READING_BATTERY}"
CONF_MIN_TEMPERATURE = f"min_{READING_TEMPERATURE}"
CONF_MAX_TEMPERATURE = f"max_{READING_TEMPERATURE}"
CONF_MIN_MOISTURE = f"min_{READING_MOISTURE}"
CONF_MAX_MOISTURE = f"max_{READING_MOISTURE}"
CONF_MIN_CONDUCTIVITY = f"min_{READING_CONDUCTIVITY}"
CONF_MAX_CONDUCTIVITY = f"max_{READING_CONDUCTIVITY}"
CONF_MIN_ILLUMINANCE = f"min_{READING_ILLUMINANCE}"
CONF_MAX_ILLUMINANCE = f"max_{READING_ILLUMINANCE}"
CONF_MIN_HUMIDITY = f"min_{READING_HUMIDITY}"
CONF_MAX_HUMIDITY = f"max_{READING_HUMIDITY}"
CONF_MIN_MMOL = f"min_{READING_MMOL}"
CONF_MAX_MMOL = f"max_{READING_MMOL}"
CONF_MIN_MOL = f"min_{READING_MOL}"
CONF_MAX_MOL = f"max_{READING_MOL}"


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
