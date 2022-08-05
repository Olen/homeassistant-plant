"""Dummy sensors for monitoring plants."""
from datetime import datetime
import logging
import random

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_NAME,
    LIGHT_LUX,
    PERCENTAGE,
    STATE_UNKNOWN,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    FLOW_PLANT_INFO,
    READING_CONDUCTIVITY,
    READING_HUMIDITY,
    READING_ILLUMINANCE,
    READING_MOISTURE,
    READING_TEMPERATURE,
    UNIT_CONDUCTIVITY,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up OpenPlantBook from a config entry."""
    _LOGGER.info(entry.data)
    sensor_entities = [
        PlantDummyMoisture(hass, entry),
        PlantDummyTemperature(hass, entry),
        PlantDummyIlluminance(hass, entry),
        PlantDummyConductivity(hass, entry),
        PlantDummyHumidity(hass, entry),
    ]
    async_add_entities(sensor_entities)
    return True


class PlantDummyStatus(SensorEntity):
    """Simple dummy sensors. Parent class"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Initialize the dummy sensor."""
        self._config = config
        self._default_state = STATE_UNKNOWN
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN}.{{}}", self.name, current_ids={}
        )
        if not self._attr_native_value or self._attr_native_value == STATE_UNKNOWN:
            self._attr_native_value = self._default_state


class PlantDummyIlluminance(PlantDummyStatus):
    """Dummy sensor"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Init the dummy sensor"""
        self._attr_name = (
            f"dummy {config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_ILLUMINANCE}"
        )
        self._attr_unique_id = f"{config.entry_id}-dummy-illuminance"
        self._attr_icon = "mdi:illuminance-6"
        self._attr_native_unit_of_measurement = LIGHT_LUX
        super().__init__(hass, config)

    async def async_update(self) -> int:
        """Give out a dummy value"""
        if datetime.now().hour < 5:
            self._attr_native_value = random.randint(1, 10) * 100
        elif datetime.now().hour < 15:
            self._attr_native_value = random.randint(20, 50) * 1000
        else:
            self._attr_native_value = random.randint(1, 10) * 100

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.ILLUMINANCE


class PlantDummyConductivity(PlantDummyStatus):
    """Dummy sensor"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Init the dummy sensor"""
        self._attr_name = (
            f"dummy {config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_CONDUCTIVITY}"
        )
        self._attr_unique_id = f"{config.entry_id}-dummy-conductivity"
        self._attr_icon = "mdi:spa-outline"
        self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY
        super().__init__(hass, config)

    async def async_update(self) -> int:
        """Give out a dummy value"""
        self._attr_native_value = random.randint(40, 200) * 10


class PlantDummyMoisture(PlantDummyStatus):
    """Dummy sensor"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Init the dummy sensor"""
        self._attr_name = (
            f"dummy {config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_MOISTURE}"
        )
        self._attr_unique_id = f"{config.entry_id}-dummy-moisture"
        self._attr_icon = "mdi:water"
        self._attr_native_unit_of_measurement = PERCENTAGE

        super().__init__(hass, config)

    async def async_update(self) -> int:
        """Give out a dummy value"""
        self._attr_native_value = random.randint(10, 70)

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.HUMIDITY


class PlantDummyTemperature(PlantDummyStatus):
    """Dummy sensor"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Init the dummy sensor"""

        self._attr_name = (
            f"dummy {config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_TEMPERATURE}"
        )
        self._attr_unique_id = f"{config.entry_id}-dummy-temperature"
        self._attr_icon = "mdi:thermometer"
        self._attr_native_unit_of_measurement = TEMP_CELSIUS

        super().__init__(hass, config)

    async def async_update(self) -> int:
        """Give out a dummy value"""
        self._attr_native_value = random.randint(15, 20)

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.TEMPERATURE


class PlantDummyHumidity(PlantDummyStatus):
    """Dummy sensor"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Init the dummy sensor"""
        self._attr_name = (
            f"dummy {config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_HUMIDITY}"
        )
        self._attr_unique_id = f"{config.entry_id}-dummy-humidity"
        self._attr_icon = "mdi:water-percent"
        self._attr_native_unit_of_measurement = PERCENTAGE
        super().__init__(hass, config)

    async def async_update(self) -> int:
        """Give out a dummy value"""
        self._attr_native_value = random.randint(25, 90)

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.HUMIDITY
