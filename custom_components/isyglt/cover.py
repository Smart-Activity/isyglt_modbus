"""ISYGLT Modbus cover platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import ATTR_POSITION, CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ISYGLTRuntimeData
from .addressing import resolve_cover_address
from .const import (
    CONF_AREA_ID,
    CONF_CLOSE_VALUE,
    CONF_COMMAND_REGISTER,
    CONF_COVERS,
    CONF_DOWN_ADDRESS,
    CONF_ENTITY_UID,
    CONF_OPEN_VALUE,
    CONF_POSITION_REGISTER,
    CONF_SLAVE,
    CONF_STOP_VALUE,
    CONF_UP_ADDRESS,
    COVER_LONG_PRESS_SECONDS,
    COVER_SHORT_PRESS_SECONDS,
    DOMAIN,
)
from .entity import ISYGLTEntity
from .modbus import ISYGLTModbusError

_LOGGER = logging.getLogger(__name__)


def _is_native_cover(config: dict[str, Any]) -> bool:
    return CONF_UP_ADDRESS in config and CONF_DOWN_ADDRESS in config


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime_data: ISYGLTRuntimeData = entry.runtime_data
    device_registry = dr.async_get(hass)
    area_registry = ar.async_get(hass)
    entities: list[CoverEntity] = []
    for config in entry.options.get(CONF_COVERS, []):
        identifier = (DOMAIN, f"cover_{entry.entry_id}_{config[CONF_ENTITY_UID]}")
        model = "ISYGLT NE cover" if _is_native_cover(config) else "Modbus cover channel (legacy)"
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
        area_name = area.name if area else None
        if _is_native_cover(config):
            entities.append(ISYGLTNativeCover(runtime_data, entry, config, area_name))
        else:
            entities.append(ISYGLTLegacyCover(runtime_data, entry, config, area_name))
    async_add_entities(entities, update_before_add=True)


class ISYGLTNativeCover(ISYGLTEntity, CoverEntity):
    """Cover controlled by two native ISYGLT NE pushbutton addresses."""

    _isyglt_periodic_update = False
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )
    _attr_should_poll = False

    def __init__(self, runtime_data, entry, config, area_name) -> None:
        super().__init__(runtime_data)
        self._entry = entry
        self._config = config
        self._area_name = area_name
        self._available = True
        self._last_direction: str | None = None
        self._attr_name = config[CONF_NAME]
        self._attr_unique_id = f"{entry.entry_id}_{config[CONF_ENTITY_UID]}"
        self._up = resolve_cover_address(config[CONF_UP_ADDRESS])
        self._down = resolve_cover_address(config[CONF_DOWN_ADDRESS])

    @property
    def device_info(self) -> dict[str, Any]:
        info = {
            "identifiers": {(DOMAIN, f"cover_{self._entry.entry_id}_{self._config[CONF_ENTITY_UID]}")},
            "name": self._config[CONF_NAME],
            "manufacturer": "ISYGLT",
            "model": "ISYGLT NE cover",
            "via_device_id": self._runtime_data.controller_device_id,
        }
        if self._area_name:
            info["suggested_area"] = self._area_name
        return info

    @property
    def available(self) -> bool:
        return self._available

    @property
    def is_closed(self) -> bool | None:
        # ISYGLT provides no real cover position feedback for this model.
        return None

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._pulse(self._up.protocol_address, COVER_LONG_PRESS_SECONDS)
        self._last_direction = "up"

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._pulse(self._down.protocol_address, COVER_LONG_PRESS_SECONDS)
        self._last_direction = "down"

    async def async_stop_cover(self, **kwargs: Any) -> None:
        if self._last_direction == "up":
            address = self._up.protocol_address
        elif self._last_direction == "down":
            address = self._down.protocol_address
        else:
            # Without feedback there is no safe way to know which physical button
            # should receive the stop pulse if HA did not start the movement.
            raise HomeAssistantError(
                f"ISYGLT stop for {self._attr_name} is unavailable because the movement direction is unknown"
            )
        await self._pulse(address, COVER_SHORT_PRESS_SECONDS)
        self._last_direction = None

    async def _pulse(self, address: int, duration: float) -> None:
        try:
            await self._runtime_data.client.async_pulse_coil(
                self._config[CONF_SLAVE], address, duration
            )
        except ISYGLTModbusError as err:
            self._available = False
            self.async_write_ha_state()
            raise HomeAssistantError(
                f"ISYGLT cover pulse failed for {self._attr_name}: {err}"
            ) from err
        self._available = True
        self.async_write_ha_state()


class ISYGLTLegacyCover(ISYGLTEntity, CoverEntity):
    """Legacy v0.3-v0.5 raw-register cover for backwards compatibility."""

    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

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
            "name": self._config[CONF_NAME],
            "manufacturer": "ISYGLT",
            "model": "Modbus cover channel (legacy)",
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
            _LOGGER.warning("Unable to read ISYGLT legacy cover %s: %s", self._attr_name, err)

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
            raise HomeAssistantError(
                f"ISYGLT position write failed for {self._attr_name}: {err}"
            ) from err
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
            raise HomeAssistantError(
                f"ISYGLT cover command failed for {self._attr_name}: {err}"
            ) from err
        self._available = True
