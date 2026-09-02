"""Button entities for native ISYGLT covers and scene storage."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ISYGLTRuntimeData
from .addressing import resolve_climate_command_address, resolve_cover_address, resolve_scene_trigger_address
from .const import (
    CONF_AREA_ID,
    CONF_CLIMATES,
    CONF_COVERS,
    CONF_IS_AIRCO,
    CONF_FAN_HIGH_NE,
    CONF_FAN_MEDIUM_NE,
    CONF_FAN_LOW_NE,
    CONF_AIRCO_POWER_NE,
    CONF_DOWN_ADDRESS,
    CONF_ENTITY_UID,
    CONF_SLAVE,
    CONF_UP_ADDRESS,
    CONF_SCENES,
    CONF_SCENE_TRIGGER_ADDRESS,
    COVER_SHORT_PRESS_SECONDS,
    SCENE_STORE_PRESS_SECONDS,
    CLIMATE_BUTTON_PRESS_SECONDS,
    DOMAIN,
)
from .entity import ISYGLTEntity
from .modbus import ISYGLTModbusError


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime_data: ISYGLTRuntimeData = entry.runtime_data
    area_registry = ar.async_get(hass)
    entities: list[ButtonEntity] = []
    for config in entry.options.get(CONF_COVERS, []):
        if CONF_UP_ADDRESS not in config or CONF_DOWN_ADDRESS not in config:
            continue
        area = area_registry.async_get_area(config.get(CONF_AREA_ID))
        area_name = area.name if area else None
        entities.extend([
            ISYGLTCoverShortPressButton(runtime_data, entry, config, area_name, "up"),
            ISYGLTCoverShortPressButton(runtime_data, entry, config, area_name, "down"),
        ])
    for config in entry.options.get(CONF_SCENES, []):
        area = area_registry.async_get_area(config.get(CONF_AREA_ID))
        area_name = area.name if area else None
        entities.append(ISYGLTSceneStoreButton(runtime_data, entry, config, area_name))

    for config in entry.options.get(CONF_CLIMATES, []):
        if not config.get(CONF_IS_AIRCO):
            continue
        area = area_registry.async_get_area(config.get(CONF_AREA_ID))
        area_name = area.name if area else None
        entities.extend([
            ISYGLTAircoCommandButton(runtime_data, entry, config, area_name, CONF_FAN_HIGH_NE, "Fan High", "fan_high"),
            ISYGLTAircoCommandButton(runtime_data, entry, config, area_name, CONF_FAN_MEDIUM_NE, "Fan Medium", "fan_medium"),
            ISYGLTAircoCommandButton(runtime_data, entry, config, area_name, CONF_FAN_LOW_NE, "Fan Low", "fan_low"),
            ISYGLTAircoCommandButton(runtime_data, entry, config, area_name, CONF_AIRCO_POWER_NE, "Airco On/Off", "power"),
        ])

    async_add_entities(entities)


class ISYGLTCoverShortPressButton(ISYGLTEntity, ButtonEntity):
    """A 200 ms pushbutton pulse for one cover direction."""

    _attr_should_poll = False
    _isyglt_periodic_update = False

    def __init__(self, runtime_data, entry, config, area_name, direction: str) -> None:
        super().__init__(runtime_data)
        self._entry = entry
        self._config = config
        self._area_name = area_name
        self._direction = direction
        address_key = CONF_UP_ADDRESS if direction == "up" else CONF_DOWN_ADDRESS
        self._resolved = resolve_cover_address(config[address_key])
        suffix = "Omhoog short press" if direction == "up" else "Omlaag short press"
        self._attr_name = f"{config[CONF_NAME]} {suffix}"
        self._attr_unique_id = f"{entry.entry_id}_{config[CONF_ENTITY_UID]}_{direction}_short_press"

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

    async def async_press(self) -> None:
        try:
            await self._runtime_data.client.async_pulse_coil(
                self._config[CONF_SLAVE],
                self._resolved.protocol_address,
                COVER_SHORT_PRESS_SECONDS,
            )
        except ISYGLTModbusError as err:
            raise HomeAssistantError(
                f"ISYGLT short press failed for {self._attr_name}: {err}"
            ) from err


class ISYGLTSceneStoreButton(ISYGLTEntity, ButtonEntity):
    """Store the current ISYGLT state in a preset using a 5-second NE press."""

    _attr_should_poll = False
    _isyglt_periodic_update = False

    def __init__(self, runtime_data, entry, config, area_name) -> None:
        super().__init__(runtime_data)
        self._entry = entry
        self._config = config
        self._area_name = area_name
        self._trigger = resolve_scene_trigger_address(config[CONF_SCENE_TRIGGER_ADDRESS])
        self._attr_name = f"{config[CONF_NAME]} Opslaan"
        self._attr_unique_id = f"{entry.entry_id}_{config[CONF_ENTITY_UID]}_store"

    @property
    def device_info(self) -> dict[str, Any]:
        info = {
            "identifiers": {(DOMAIN, f"scene_{self._entry.entry_id}_{self._config[CONF_ENTITY_UID]}")},
            "name": self._config[CONF_NAME],
            "manufacturer": "ISYGLT",
            "model": "ISYGLT NE/NA scene",
            "via_device_id": self._runtime_data.controller_device_id,
        }
        if self._area_name:
            info["suggested_area"] = self._area_name
        return info

    async def async_press(self) -> None:
        try:
            await self._runtime_data.client.async_pulse_coil(
                self._config[CONF_SLAVE],
                self._trigger.protocol_address,
                SCENE_STORE_PRESS_SECONDS,
            )
        except ISYGLTModbusError as err:
            raise HomeAssistantError(
                f"ISYGLT scene store failed for {self._attr_name}: {err}"
            ) from err


class ISYGLTAircoCommandButton(ISYGLTEntity, ButtonEntity):
    """Short-press an Airco NE command; Climate NA feedback remains authoritative."""

    _attr_should_poll = False
    _isyglt_periodic_update = False

    def __init__(self, runtime_data, entry, config, area_name, address_key: str, label: str, uid_suffix: str) -> None:
        super().__init__(runtime_data)
        self._entry = entry
        self._config = config
        self._area_name = area_name
        self._resolved = resolve_climate_command_address(config[address_key])
        self._attr_name = f"{config[CONF_NAME]} {label}"
        self._attr_unique_id = f"{entry.entry_id}_{config[CONF_ENTITY_UID]}_{uid_suffix}"

    @property
    def device_info(self) -> dict[str, Any]:
        info = {
            "identifiers": {(DOMAIN, f"climate_{self._entry.entry_id}_{self._config[CONF_ENTITY_UID]}")},
            "name": self._config[CONF_NAME],
            "manufacturer": "ISYGLT",
            "model": "ISYGLT M/SM Airco",
            "via_device_id": self._runtime_data.controller_device_id,
        }
        if self._area_name:
            info["suggested_area"] = self._area_name
        return info

    async def async_press(self) -> None:
        try:
            await self._runtime_data.client.async_pulse_coil(
                self._config[CONF_SLAVE],
                self._resolved.protocol_address,
                CLIMATE_BUTTON_PRESS_SECONDS,
            )
        except ISYGLTModbusError as err:
            raise HomeAssistantError(
                f"ISYGLT Airco button failed for {self._attr_name}: {err}"
            ) from err
