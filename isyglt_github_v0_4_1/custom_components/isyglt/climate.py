"""ISYGLT Modbus climate platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, CONF_NAME, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ISYGLTRuntimeData
from .const import (
    CONF_AREA_ID, CONF_CLIMATES, CONF_CURRENT_TEMP_REGISTER, CONF_ENTITY_UID,
    CONF_MAX_TEMP, CONF_MIN_TEMP, CONF_SLAVE, CONF_TARGET_TEMP_REGISTER,
    CONF_TEMP_SCALE, CONF_TEMP_STEP, DOMAIN,
)
from .entity import ISYGLTEntity
from .modbus import ISYGLTModbusError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    runtime_data: ISYGLTRuntimeData = entry.runtime_data
    device_registry = dr.async_get(hass)
    area_registry = ar.async_get(hass)
    entities: list[ISYGLTClimate] = []
    for config in entry.options.get(CONF_CLIMATES, []):
        identifier = (DOMAIN, f"climate_{entry.entry_id}_{config[CONF_ENTITY_UID]}")
        device = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id, identifiers={identifier}, manufacturer="ISYGLT",
            model="Modbus climate channel", name=config[CONF_NAME], via_device_id=runtime_data.controller_device_id,
        )
        if config.get(CONF_AREA_ID):
            device_registry.async_update_device(device.id, area_id=config[CONF_AREA_ID])
        area = area_registry.async_get_area(config.get(CONF_AREA_ID))
        entities.append(ISYGLTClimate(runtime_data, entry, config, area.name if area else None))
    async_add_entities(entities, update_before_add=True)


class ISYGLTClimate(ISYGLTEntity, ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.HEAT
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(self, runtime_data, entry, config, area_name) -> None:
        super().__init__(runtime_data)
        self._entry = entry
        self._config = config
        self._area_name = area_name
        self._available = True
        self._attr_name = config[CONF_NAME]
        self._attr_unique_id = f"{entry.entry_id}_{config[CONF_ENTITY_UID]}"
        self._attr_min_temp = float(config[CONF_MIN_TEMP])
        self._attr_max_temp = float(config[CONF_MAX_TEMP])
        self._attr_target_temperature_step = float(config[CONF_TEMP_STEP])
        self._attr_current_temperature = None
        self._attr_target_temperature = None

    @property
    def device_info(self) -> dict[str, Any]:
        info = {
            "identifiers": {(DOMAIN, f"climate_{self._entry.entry_id}_{self._config[CONF_ENTITY_UID]}")},
            "name": self._config[CONF_NAME], "manufacturer": "ISYGLT", "model": "Modbus climate channel",
            "via_device_id": self._runtime_data.controller_device_id,
        }
        if self._area_name:
            info["suggested_area"] = self._area_name
        return info

    @property
    def available(self) -> bool:
        return self._available

    async def async_update(self) -> None:
        scale = float(self._config[CONF_TEMP_SCALE])
        try:
            current_raw = await self._runtime_data.client.async_read_holding_register(
                self._config[CONF_SLAVE], self._config[CONF_CURRENT_TEMP_REGISTER]
            )
            target_raw = await self._runtime_data.client.async_read_holding_register(
                self._config[CONF_SLAVE], self._config[CONF_TARGET_TEMP_REGISTER]
            )
            self._attr_current_temperature = current_raw / scale
            self._attr_target_temperature = target_raw / scale
            self._available = True
        except ISYGLTModbusError as err:
            self._available = False
            _LOGGER.warning("Unable to read ISYGLT climate %s: %s", self._attr_name, err)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if ATTR_TEMPERATURE not in kwargs:
            return
        temperature = float(kwargs[ATTR_TEMPERATURE])
        temperature = max(self._attr_min_temp, min(self._attr_max_temp, temperature))
        scale = float(self._config[CONF_TEMP_SCALE])
        raw = int(round(temperature * scale))
        try:
            await self._runtime_data.client.async_write_holding_register(
                self._config[CONF_SLAVE], self._config[CONF_TARGET_TEMP_REGISTER], raw
            )
        except ISYGLTModbusError as err:
            self._available = False
            raise HomeAssistantError(f"ISYGLT setpoint write failed for {self._attr_name}: {err}") from err
        self._attr_target_temperature = temperature
        self._available = True
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode != HVACMode.HEAT:
            raise HomeAssistantError("This ISYGLT climate configuration only supports HEAT mode")
