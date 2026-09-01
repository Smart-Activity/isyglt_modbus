"""ISYGLT Modbus switch platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ISYGLTRuntimeData
from .const import (
    CONF_AREA_ID,
    CONF_ENTITY_UID,
    CONF_OFF_VALUE,
    CONF_ON_VALUE,
    CONF_REGISTER,
    CONF_SLAVE,
    CONF_SWITCHES,
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
    entities: list[ISYGLTSwitch] = []

    for config in entry.options.get(CONF_SWITCHES, []):
        identifier = (DOMAIN, f"switch_{entry.entry_id}_{config[CONF_ENTITY_UID]}")
        device = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={identifier},
            manufacturer="ISYGLT",
            model="Modbus switch channel",
            name=config[CONF_NAME],
            via_device_id=runtime_data.controller_device_id,
        )
        if config.get(CONF_AREA_ID):
            device_registry.async_update_device(device.id, area_id=config[CONF_AREA_ID])
        area = area_registry.async_get_area(config.get(CONF_AREA_ID))
        entities.append(ISYGLTSwitch(runtime_data, entry, config, area.name if area else None))

    async_add_entities(entities, update_before_add=True)


class ISYGLTSwitch(ISYGLTEntity, SwitchEntity):
    def __init__(self, runtime_data, entry, config, area_name) -> None:
        super().__init__(runtime_data)
        self._entry = entry
        self._config = config
        self._area_name = area_name
        self._value = config[CONF_OFF_VALUE]
        self._available = True
        self._attr_name = config[CONF_NAME]
        self._attr_unique_id = f"{entry.entry_id}_{config[CONF_ENTITY_UID]}"

    @property
    def device_info(self) -> dict[str, Any]:
        info = {
            "identifiers": {(DOMAIN, f"switch_{self._entry.entry_id}_{self._config[CONF_ENTITY_UID]}")},
            "name": self._config[CONF_NAME],
            "manufacturer": "ISYGLT",
            "model": "Modbus switch channel",
            "via_device_id": self._runtime_data.controller_device_id,
        }
        if self._area_name:
            info["suggested_area"] = self._area_name
        return info

    @property
    def available(self) -> bool:
        return self._available

    @property
    def is_on(self) -> bool:
        return self._value == self._config[CONF_ON_VALUE]

    async def async_update(self) -> None:
        try:
            self._value = await self._runtime_data.client.async_read_holding_register(
                self._config[CONF_SLAVE], self._config[CONF_REGISTER]
            )
            self._available = True
        except ISYGLTModbusError as err:
            self._available = False
            _LOGGER.warning("Unable to read ISYGLT switch %s: %s", self._attr_name, err)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_write(self._config[CONF_ON_VALUE])

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_write(self._config[CONF_OFF_VALUE])

    async def _async_write(self, value: int) -> None:
        try:
            await self._runtime_data.client.async_write_holding_register(
                self._config[CONF_SLAVE], self._config[CONF_REGISTER], value
            )
        except ISYGLTModbusError as err:
            self._available = False
            raise HomeAssistantError(f"ISYGLT write failed for {self._attr_name}: {err}") from err
        self._value = value
        self._available = True
        self.async_write_ha_state()
