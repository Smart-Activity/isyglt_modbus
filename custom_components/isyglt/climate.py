"""ISYGLT Modbus climate platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, CONF_NAME, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ISYGLTRuntimeData
from .addressing import (
    resolve_climate_command_address,
    resolve_climate_current_address,
    resolve_climate_feedback_address,
    resolve_climate_target_address,
)
from .const import (
    CLIMATE_BUTTON_PRESS_SECONDS,
    CONF_AIRCO_POWER_NA,
    CONF_AIRCO_POWER_NE,
    CONF_AREA_ID,
    CONF_CLIMATES,
    CONF_CURRENT_TEMP_ADDRESS,
    CONF_CURRENT_TEMP_REGISTER,
    CONF_ENTITY_UID,
    CONF_FAN_HIGH_NA,
    CONF_FAN_HIGH_NE,
    CONF_FAN_LOW_NA,
    CONF_FAN_LOW_NE,
    CONF_FAN_MEDIUM_NA,
    CONF_FAN_MEDIUM_NE,
    CONF_IS_AIRCO,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_SLAVE,
    CONF_TARGET_TEMP_ADDRESS,
    CONF_TARGET_TEMP_REGISTER,
    CONF_TEMP_SCALE,
    CONF_TEMP_STEP,
    DOMAIN,
)
from .entity import ISYGLTEntity
from .modbus import ISYGLTModbusError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime_data: ISYGLTRuntimeData = entry.runtime_data
    device_registry = dr.async_get(hass)
    area_registry = ar.async_get(hass)
    entities: list[ISYGLTClimate] = []
    for config in entry.options.get(CONF_CLIMATES, []):
        identifier = (DOMAIN, f"climate_{entry.entry_id}_{config[CONF_ENTITY_UID]}")
        native = CONF_TARGET_TEMP_ADDRESS in config and CONF_CURRENT_TEMP_ADDRESS in config
        model = "ISYGLT M/SM Airco" if native and config.get(CONF_IS_AIRCO) else (
            "ISYGLT M/SM climate" if native else "Modbus climate channel"
        )
        device = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={identifier},
            manufacturer="ISYGLT",
            model=model,
            name=config[CONF_NAME],
            via_device_id=runtime_data.controller_device_id,
        )
        if config.get(CONF_AREA_ID):
            device_registry.async_update_device(device.id, area_id=config[CONF_AREA_ID])
        area = area_registry.async_get_area(config.get(CONF_AREA_ID))
        entities.append(ISYGLTClimate(runtime_data, entry, config, area.name if area else None))
    async_add_entities(entities, update_before_add=True)


class ISYGLTClimate(ISYGLTEntity, ClimateEntity):
    """Climate entity backed by an ISYGLT M setpoint and SM measurement."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, runtime_data, entry, config, area_name) -> None:
        super().__init__(runtime_data)
        self._entry = entry
        self._config = config
        self._area_name = area_name
        self._available = True
        self._native = CONF_TARGET_TEMP_ADDRESS in config and CONF_CURRENT_TEMP_ADDRESS in config
        self._is_airco = bool(config.get(CONF_IS_AIRCO, False)) if self._native else False
        self._attr_name = config[CONF_NAME]
        self._attr_unique_id = f"{entry.entry_id}_{config[CONF_ENTITY_UID]}"
        self._attr_min_temp = float(config[CONF_MIN_TEMP])
        self._attr_max_temp = float(config[CONF_MAX_TEMP])
        self._attr_target_temperature_step = float(config[CONF_TEMP_STEP])
        self._attr_current_temperature = None
        self._attr_target_temperature = None

        if self._is_airco:
            self._attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL]
            self._attr_hvac_mode = HVACMode.OFF
            self._attr_fan_modes = [FAN_LOW, FAN_MEDIUM, FAN_HIGH]
            self._attr_fan_mode = None
            self._attr_supported_features = (
                ClimateEntityFeature.TARGET_TEMPERATURE
                | ClimateEntityFeature.FAN_MODE
                | ClimateEntityFeature.TURN_ON
                | ClimateEntityFeature.TURN_OFF
            )
            self._fan_commands = {
                FAN_HIGH: resolve_climate_command_address(config[CONF_FAN_HIGH_NE]),
                FAN_MEDIUM: resolve_climate_command_address(config[CONF_FAN_MEDIUM_NE]),
                FAN_LOW: resolve_climate_command_address(config[CONF_FAN_LOW_NE]),
            }
            self._fan_feedback = {
                FAN_HIGH: resolve_climate_feedback_address(config[CONF_FAN_HIGH_NA]),
                FAN_MEDIUM: resolve_climate_feedback_address(config[CONF_FAN_MEDIUM_NA]),
                FAN_LOW: resolve_climate_feedback_address(config[CONF_FAN_LOW_NA]),
            }
            self._power_command = resolve_climate_command_address(config[CONF_AIRCO_POWER_NE])
            self._power_feedback = resolve_climate_feedback_address(config[CONF_AIRCO_POWER_NA])
        else:
            self._attr_hvac_modes = [HVACMode.HEAT]
            self._attr_hvac_mode = HVACMode.HEAT
            self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

        if self._native:
            self._target_address = resolve_climate_target_address(config[CONF_TARGET_TEMP_ADDRESS])
            self._current_address = resolve_climate_current_address(config[CONF_CURRENT_TEMP_ADDRESS])

    @property
    def device_info(self) -> dict[str, Any]:
        model = "ISYGLT M/SM Airco" if self._is_airco else (
            "ISYGLT M/SM climate" if self._native else "Modbus climate channel"
        )
        info = {
            "identifiers": {(DOMAIN, f"climate_{self._entry.entry_id}_{self._config[CONF_ENTITY_UID]}")},
            "name": self._config[CONF_NAME],
            "manufacturer": "ISYGLT",
            "model": model,
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
            if self._native:
                current_raw = await self._runtime_data.client.async_read_input_register(
                    self._config[CONF_SLAVE], self._current_address.protocol_address
                )
                target_raw = await self._runtime_data.client.async_read_holding_register(
                    self._config[CONF_SLAVE], self._target_address.protocol_address
                )
            else:
                # Backwards compatibility for v0.3-v0.7 raw Modbus Climate entries.
                current_raw = await self._runtime_data.client.async_read_holding_register(
                    self._config[CONF_SLAVE], self._config[CONF_CURRENT_TEMP_REGISTER]
                )
                target_raw = await self._runtime_data.client.async_read_holding_register(
                    self._config[CONF_SLAVE], self._config[CONF_TARGET_TEMP_REGISTER]
                )

            self._attr_current_temperature = current_raw / scale
            self._attr_target_temperature = target_raw / scale

            if self._is_airco:
                power_on = await self._runtime_data.client.async_read_discrete_input(
                    self._config[CONF_SLAVE], self._power_feedback.protocol_address
                )
                self._attr_hvac_mode = HVACMode.COOL if power_on else HVACMode.OFF

                active_fans: list[str] = []
                for fan_mode, address in self._fan_feedback.items():
                    if await self._runtime_data.client.async_read_discrete_input(
                        self._config[CONF_SLAVE], address.protocol_address
                    ):
                        active_fans.append(fan_mode)
                # In normal ISYGLT operation only one of these feedbacks should be active.
                self._attr_fan_mode = active_fans[0] if active_fans else None

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
            address = (
                self._target_address.protocol_address
                if self._native
                else self._config[CONF_TARGET_TEMP_REGISTER]
            )
            await self._runtime_data.client.async_write_holding_register(
                self._config[CONF_SLAVE], address, raw
            )
        except ISYGLTModbusError as err:
            self._available = False
            raise HomeAssistantError(
                f"ISYGLT setpoint write failed for {self._attr_name}: {err}"
            ) from err
        self._attr_target_temperature = temperature
        self._available = True
        self.async_write_ha_state()

    async def _async_pulse(self, address) -> None:
        try:
            await self._runtime_data.client.async_pulse_coil(
                self._config[CONF_SLAVE],
                address.protocol_address,
                CLIMATE_BUTTON_PRESS_SECONDS,
            )
        except ISYGLTModbusError as err:
            self._available = False
            raise HomeAssistantError(
                f"ISYGLT Airco command failed for {self._attr_name}: {err}"
            ) from err

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if not self._is_airco:
            if hvac_mode != HVACMode.HEAT:
                raise HomeAssistantError("This ISYGLT climate configuration only supports HEAT mode")
            return
        if hvac_mode not in (HVACMode.OFF, HVACMode.COOL):
            raise HomeAssistantError("This ISYGLT Airco supports only COOL and OFF")
        if hvac_mode == self._attr_hvac_mode:
            return
        await self._async_pulse(self._power_command)
        # Feedback is authoritative; this is only optimistic until the next poll.
        self._attr_hvac_mode = hvac_mode
        self._available = True
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        if not self._is_airco:
            return
        await self.async_set_hvac_mode(HVACMode.COOL)

    async def async_turn_off(self) -> None:
        if not self._is_airco:
            return
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if not self._is_airco or fan_mode not in self._fan_commands:
            raise HomeAssistantError(f"Unsupported ISYGLT Airco fan mode: {fan_mode}")
        if fan_mode == self._attr_fan_mode:
            return
        await self._async_pulse(self._fan_commands[fan_mode])
        # Feedback remains authoritative; optimistic state keeps the UI responsive.
        self._attr_fan_mode = fan_mode
        self._available = True
        self.async_write_ha_state()
