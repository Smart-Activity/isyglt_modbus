"""ISYGLT Modbus light platform."""

from __future__ import annotations

import logging
import math
from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.color import brightness_to_value, value_to_brightness

from . import ISYGLTRuntimeData
from .addressing import ISYGLTAddress, resolve_light_address
from .const import (
    CONF_AREA_ID,
    CONF_ENTITY_UID,
    CONF_ISYGLT_ADDRESS,
    CONF_LIGHT_KIND,
    CONF_LIGHTS,
    CONF_REGISTER,
    CONF_SLAVE,
    DOMAIN,
    LIGHT_KIND_DIMMABLE,
    LIGHT_KIND_SWITCHABLE,
    MODBUS_MAX,
    MODBUS_MIN,
)
from .entity import ISYGLTEntity
from .modbus import ISYGLTModbusError

_LOGGER = logging.getLogger(__name__)
BRIGHTNESS_SCALE = (1, MODBUS_MAX)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up configured ISYGLT lights."""
    runtime_data: ISYGLTRuntimeData = entry.runtime_data
    device_registry = dr.async_get(hass)
    area_registry = ar.async_get(hass)

    entities: list[ISYGLTLight] = []
    for config in entry.options.get(CONF_LIGHTS, []):
        light_kind = config.get(CONF_LIGHT_KIND, LIGHT_KIND_DIMMABLE)
        model = (
            "ISYGLT dimmer (M)"
            if light_kind == LIGHT_KIND_DIMMABLE
            else "ISYGLT switched light (NE)"
        )
        # Older v0.3 lights do not contain CONF_LIGHT_KIND and keep their raw
        # holding-register behaviour for safe, non-breaking upgrades.
        if CONF_LIGHT_KIND not in config:
            model = "Legacy Modbus dimmer channel"

        identifier = (DOMAIN, f"light_{entry.entry_id}_{config[CONF_ENTITY_UID]}")
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

        entities.append(
            ISYGLTLight(
                runtime_data=runtime_data,
                entry=entry,
                config=config,
                device_id=device.id,
                area_name=area_name,
            )
        )

    async_add_entities(entities, update_before_add=True)


class ISYGLTLight(ISYGLTEntity, LightEntity):
    """ISYGLT light using M for dimming or NE for switched output."""

    def __init__(
        self,
        runtime_data: ISYGLTRuntimeData,
        entry: ConfigEntry,
        config: dict[str, Any],
        device_id: str,
        area_name: str | None,
    ) -> None:
        super().__init__(runtime_data)
        self._entry = entry
        self._config = config
        self._device_id = device_id
        self._area_name = area_name
        self._legacy = CONF_LIGHT_KIND not in config
        self._light_kind = config.get(CONF_LIGHT_KIND, LIGHT_KIND_DIMMABLE)
        self._address: ISYGLTAddress | None = None
        if not self._legacy:
            self._address = resolve_light_address(
                self._light_kind, config[CONF_ISYGLT_ADDRESS]
            )

        self._value = 0
        self._last_nonzero = MODBUS_MAX
        self._available = True

        if self._light_kind == LIGHT_KIND_SWITCHABLE and not self._legacy:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF
        else:
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS

        self._attr_name = config[CONF_NAME]
        self._attr_unique_id = f"{entry.entry_id}_{config[CONF_ENTITY_UID]}"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info for entity registry linking."""
        if self._legacy:
            model = "Legacy Modbus dimmer channel"
        elif self._light_kind == LIGHT_KIND_DIMMABLE:
            model = "ISYGLT dimmer (M)"
        else:
            model = "ISYGLT switched light (NE)"

        info: dict[str, Any] = {
            "identifiers": {
                (DOMAIN, f"light_{self._entry.entry_id}_{self._config[CONF_ENTITY_UID]}")
            },
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
        """Return entity availability."""
        return self._available

    @property
    def is_on(self) -> bool:
        """Return true when the output is active."""
        return self._value > MODBUS_MIN

    @property
    def brightness(self) -> int | None:
        """Return brightness for dimmable lights only."""
        if self._light_kind == LIGHT_KIND_SWITCHABLE and not self._legacy:
            return None
        if self._value <= MODBUS_MIN:
            return 0
        return value_to_brightness(BRIGHTNESS_SCALE, self._value)

    async def async_update(self) -> None:
        """Read feedback from the automatically resolved ISYGLT address."""
        try:
            if self._legacy:
                raw = await self._runtime_data.client.async_read_holding_register(
                    self._config[CONF_SLAVE], self._config[CONF_REGISTER]
                )
                self._value = max(MODBUS_MIN, min(MODBUS_MAX, raw))
            elif self._light_kind == LIGHT_KIND_DIMMABLE:
                raw = await self._runtime_data.client.async_read_holding_register(
                    self._config[CONF_SLAVE], self._address.protocol_address
                )
                self._value = max(MODBUS_MIN, min(MODBUS_MAX, raw))
            else:
                state = await self._runtime_data.client.async_read_coil(
                    self._config[CONF_SLAVE], self._address.protocol_address
                )
                self._value = 1 if state else 0
        except ISYGLTModbusError as err:
            self._available = False
            _LOGGER.warning(
                "Unable to read ISYGLT light %s (slave %s): %s",
                self._attr_name,
                self._config[CONF_SLAVE],
                err,
            )
            return

        self._available = True
        if self._value > 0 and self._light_kind == LIGHT_KIND_DIMMABLE:
            self._last_nonzero = self._value

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on, optionally setting brightness for an M dimmer."""
        if self._light_kind == LIGHT_KIND_SWITCHABLE and not self._legacy:
            await self._async_write_switchable(True)
            return

        if ATTR_BRIGHTNESS in kwargs:
            brightness = int(kwargs[ATTR_BRIGHTNESS])
            if brightness <= 0:
                value = 0
            else:
                value = math.ceil(brightness_to_value(BRIGHTNESS_SCALE, brightness))
                value = max(1, min(MODBUS_MAX, value))
        else:
            value = self._last_nonzero if self._last_nonzero > 0 else MODBUS_MAX

        await self._async_write_dimmable(value)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        if self._light_kind == LIGHT_KIND_SWITCHABLE and not self._legacy:
            await self._async_write_switchable(False)
        else:
            await self._async_write_dimmable(0)

    async def _async_write_dimmable(self, value: int) -> None:
        try:
            address = (
                self._config[CONF_REGISTER]
                if self._legacy
                else self._address.protocol_address
            )
            await self._runtime_data.client.async_write_holding_register(
                self._config[CONF_SLAVE], address, value
            )
        except ISYGLTModbusError as err:
            self._available = False
            raise HomeAssistantError(
                f"ISYGLT write failed for {self._attr_name}: {err}"
            ) from err

        self._available = True
        self._value = value
        if value > 0:
            self._last_nonzero = value
        self.async_write_ha_state()

    async def _async_write_switchable(self, state: bool) -> None:
        try:
            await self._runtime_data.client.async_write_coil(
                self._config[CONF_SLAVE], self._address.protocol_address, state
            )
        except ISYGLTModbusError as err:
            self._available = False
            raise HomeAssistantError(
                f"ISYGLT write failed for {self._attr_name}: {err}"
            ) from err

        self._available = True
        self._value = 1 if state else 0
        self.async_write_ha_state()
