"""ISYGLT switch platform."""

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
from .addressing import resolve_switch_address
from .const import (
    CONF_AREA_ID,
    CONF_ENTITY_UID,
    CONF_ISYGLT_ADDRESS,
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
            model="ISYGLT NE switch",
            name=config[CONF_NAME],
            via_device_id=runtime_data.controller_device_id,
        )
        if config.get(CONF_AREA_ID):
            device_registry.async_update_device(device.id, area_id=config[CONF_AREA_ID])
        area = area_registry.async_get_area(config.get(CONF_AREA_ID))
        entities.append(ISYGLTSwitch(runtime_data, entry, config, area.name if area else None))

    async_add_entities(entities, update_before_add=True)


class ISYGLTSwitch(ISYGLTEntity, SwitchEntity):
    """A native ISYGLT NE switch with legacy raw-register compatibility."""

    def __init__(self, runtime_data, entry, config, area_name) -> None:
        super().__init__(runtime_data)
        self._entry = entry
        self._config = config
        self._area_name = area_name
        self._available = True
        self._attr_name = config[CONF_NAME]
        self._attr_unique_id = f"{entry.entry_id}_{config[CONF_ENTITY_UID]}"

        # v0.5+ native configuration. Older v0.3/v0.4 switches used a raw
        # holding register plus configurable integer on/off values. Keep that
        # path intact so an upgrade does not break existing installations.
        self._native = CONF_ISYGLT_ADDRESS in config
        if self._native:
            self._address = resolve_switch_address(config[CONF_ISYGLT_ADDRESS])
            self._is_on = False
        else:
            self._value = config.get(CONF_OFF_VALUE, 0)

    @property
    def device_info(self) -> dict[str, Any]:
        model = "ISYGLT NE switch" if self._native else "Legacy Modbus switch channel"
        info = {
            "identifiers": {(DOMAIN, f"switch_{self._entry.entry_id}_{self._config[CONF_ENTITY_UID]}")},
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

    @property
    def is_on(self) -> bool:
        if self._native:
            return self._is_on
        return self._value == self._config.get(CONF_ON_VALUE, 100)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not self._native:
            return {"isyglt_addressing": "legacy_raw_modbus"}
        return {
            "isyglt_address": f"NE {self._address.native_address}",
            "modbus_reference": self._address.reference_address,
            "modbus_protocol_address": self._address.protocol_address,
        }

    async def async_update(self) -> None:
        try:
            if self._native:
                self._is_on = await self._runtime_data.client.async_read_coil(
                    self._config[CONF_SLAVE], self._address.protocol_address
                )
            else:
                self._value = await self._runtime_data.client.async_read_holding_register(
                    self._config[CONF_SLAVE], self._config[CONF_REGISTER]
                )
            self._available = True
        except ISYGLTModbusError as err:
            self._available = False
            _LOGGER.warning("Unable to read ISYGLT switch %s: %s", self._attr_name, err)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_write(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_write(False)

    async def _async_write(self, state: bool) -> None:
        try:
            if self._native:
                await self._runtime_data.client.async_write_coil(
                    self._config[CONF_SLAVE], self._address.protocol_address, state
                )
                self._is_on = state
            else:
                value = self._config.get(CONF_ON_VALUE, 100) if state else self._config.get(CONF_OFF_VALUE, 0)
                await self._runtime_data.client.async_write_holding_register(
                    self._config[CONF_SLAVE], self._config[CONF_REGISTER], value
                )
                self._value = value
        except ISYGLTModbusError as err:
            self._available = False
            raise HomeAssistantError(f"ISYGLT write failed for {self._attr_name}: {err}") from err

        self._available = True
        self.async_write_ha_state()
