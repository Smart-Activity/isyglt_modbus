"""ISYGLT Modbus cover platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_POSITION, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ISYGLTRuntimeData
from .const import (
    CONF_AREA_ID,
    CONF_CLOSE_VALUE,
    CONF_COMMAND_REGISTER,
    CONF_COVERS,
    CONF_ENTITY_UID,
    CONF_OPEN_VALUE,
    CONF_POSITION_REGISTER,
    CONF_SLAVE,
    CONF_STOP_VALUE,
    DOMAIN,
)
from .entity import ISYGLTEntity
from .modbus import ISYGLTModbusError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    runtime_data: ISYGLTRuntimeData = entry.runtime_data
    device_registry = dr.async_get(hass)
    area_registry = ar.async_get(hass)
    entities: list[ISYGLTCover] = []
    for config in entry.options.get(CONF_COVERS, []):
        identifier = (DOMAIN, f"cover_{entry.entry_id}_{config[CONF_ENTITY_UID]}")
        device = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id, identifiers={identifier}, manufacturer="ISYGLT",
            model="Modbus cover channel", name=config[CONF_NAME], via_device_id=runtime_data.controller_device_id,
        )
        if config.get(CONF_AREA_ID):
            device_registry.async_update_device(device.id, area_id=config[CONF_AREA_ID])
        area = area_registry.async_get_area(config.get(CONF_AREA_ID))
        entities.append(ISYGLTCover(runtime_data, entry, config, area.name if area else None))
    async_add_entities(entities, update_before_add=True)


class ISYGLTCover(ISYGLTEntity, CoverEntity):
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP | CoverEntityFeature.SET_POSITION

    def __init__(self, runtime_data, entry, config, area_name) -> None:
        super().__init__(runtime_data)
        self._entry = entry
        self._config = config
        self._area_name = area_name
        self._position = 0
        self._available = True
        self._attr_name = config[CONF_NAME]
        self._attr_unique_id = f"{entry.entry_id}_{config[CONF_ENTITY_UID]}"

    @property
    def device_info(self) -> dict[str, Any]:
        info = {
            "identifiers": {(DOMAIN, f"cover_{self._entry.entry_id}_{self._config[CONF_ENTITY_UID]}")},
            "name": self._config[CONF_NAME], "manufacturer": "ISYGLT", "model": "Modbus cover channel",
            "via_device_id": self._runtime_data.controller_device_id,
        }
        if self._area_name:
            info["suggested_area"] = self._area_name
        return info

    @property
    def available(self) -> bool:
        return self._available

    @property
    def current_cover_position(self) -> int | None:
        return self._position

    @property
    def is_closed(self) -> bool | None:
        return self._position == 0

    async def async_update(self) -> None:
        try:
            raw = await self._runtime_data.client.async_read_holding_register(
                self._config[CONF_SLAVE], self._config[CONF_POSITION_REGISTER]
            )
            self._position = max(0, min(100, int(raw)))
            self._available = True
        except ISYGLTModbusError as err:
            self._available = False
            _LOGGER.warning("Unable to read ISYGLT cover %s: %s", self._attr_name, err)

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._write_command(self._config[CONF_OPEN_VALUE])

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._write_command(self._config[CONF_CLOSE_VALUE])

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self._write_command(self._config[CONF_STOP_VALUE])

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        position = max(0, min(100, int(kwargs[ATTR_POSITION])))
        try:
            await self._runtime_data.client.async_write_holding_register(
                self._config[CONF_SLAVE], self._config[CONF_POSITION_REGISTER], position
            )
        except ISYGLTModbusError as err:
            self._available = False
            raise HomeAssistantError(f"ISYGLT position write failed for {self._attr_name}: {err}") from err
        self._position = position
        self._available = True
        self.async_write_ha_state()

    async def _write_command(self, value: int) -> None:
        try:
            await self._runtime_data.client.async_write_holding_register(
                self._config[CONF_SLAVE], self._config[CONF_COMMAND_REGISTER], value
            )
        except ISYGLTModbusError as err:
            self._available = False
            raise HomeAssistantError(f"ISYGLT cover command failed for {self._attr_name}: {err}") from err
        self._available = True
