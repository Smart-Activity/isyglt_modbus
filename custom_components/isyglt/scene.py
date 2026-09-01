"""Native ISYGLT scene platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.scene import BaseScene
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ISYGLTRuntimeData
from .addressing import resolve_scene_feedback_address, resolve_scene_trigger_address
from .const import (
    CONF_AREA_ID,
    CONF_ENTITY_UID,
    CONF_SCENE_FEEDBACK_ADDRESS,
    CONF_SCENE_TRIGGER_ADDRESS,
    CONF_SCENES,
    CONF_SLAVE,
    DOMAIN,
    SCENE_ACTIVATE_PRESS_SECONDS,
)
from .entity import ISYGLTEntity
from .modbus import ISYGLTModbusError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up native ISYGLT scenes."""
    runtime_data: ISYGLTRuntimeData = entry.runtime_data
    device_registry = dr.async_get(hass)
    area_registry = ar.async_get(hass)
    entities: list[ISYGLTScene] = []

    for config in entry.options.get(CONF_SCENES, []):
        identifier = (DOMAIN, f"scene_{entry.entry_id}_{config[CONF_ENTITY_UID]}")
        device = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={identifier},
            manufacturer="ISYGLT",
            model="ISYGLT NE/NA scene",
            name=config[CONF_NAME],
            via_device_id=runtime_data.controller_device_id,
        )
        if config.get(CONF_AREA_ID):
            device_registry.async_update_device(device.id, area_id=config[CONF_AREA_ID])
        area = area_registry.async_get_area(config.get(CONF_AREA_ID))
        entities.append(
            ISYGLTScene(runtime_data, entry, config, area.name if area else None)
        )

    async_add_entities(entities, update_before_add=True)


class ISYGLTScene(ISYGLTEntity, BaseScene):
    """Scene activated by NE short press, confirmed by NA feedback."""

    _attr_should_poll = True

    def __init__(self, runtime_data, entry, config, area_name) -> None:
        super().__init__(runtime_data)
        self._entry = entry
        self._config = config
        self._area_name = area_name
        self._trigger = resolve_scene_trigger_address(config[CONF_SCENE_TRIGGER_ADDRESS])
        self._feedback = resolve_scene_feedback_address(config[CONF_SCENE_FEEDBACK_ADDRESS])
        self._available = True
        self._feedback_active = False
        self._feedback_initialized = False
        self._attr_name = config[CONF_NAME]
        self._attr_unique_id = f"{entry.entry_id}_{config[CONF_ENTITY_UID]}"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
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

    @property
    def available(self) -> bool:
        """Return whether feedback communication is available."""
        return self._available

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose native addresses and current NA feedback for diagnostics."""
        return {
            "isyglt_ne_address": f"NE {self._trigger.native_address}",
            "isyglt_na_feedback": f"NA {self._feedback.native_address}",
            "feedback_active": self._feedback_active,
            "ne_modbus_reference": self._trigger.reference_address,
            "na_modbus_reference": self._feedback.reference_address,
        }

    async def _async_activate(self, **kwargs: Any) -> None:
        """Activate the scene with a short press on its NE address.

        The activation timestamp is intentionally recorded from the NA feedback
        transition instead of immediately on the command. This keeps Home
        Assistant aligned with what ISYGLT reports as the active preset.
        """
        try:
            await self._runtime_data.client.async_pulse_coil(
                self._config[CONF_SLAVE],
                self._trigger.protocol_address,
                SCENE_ACTIVATE_PRESS_SECONDS,
            )
        except ISYGLTModbusError as err:
            self._available = False
            raise HomeAssistantError(
                f"ISYGLT scene activation failed for {self._attr_name}: {err}"
            ) from err

        self._available = True

    async def async_update(self) -> None:
        """Read NA feedback and record external/confirmed scene activation."""
        try:
            active = await self._runtime_data.client.async_read_discrete_input(
                self._config[CONF_SLAVE], self._feedback.protocol_address
            )
            self._available = True
        except ISYGLTModbusError as err:
            self._available = False
            _LOGGER.warning(
                "Unable to read ISYGLT scene feedback %s: %s", self._attr_name, err
            )
            return

        # Record only a false -> true transition. On initial setup, a feedback
        # that is already high is also a valid indication that this preset is
        # currently active, so record that once.
        if active and (not self._feedback_initialized or not self._feedback_active):
            self._async_record_activation()

        self._feedback_active = active
        self._feedback_initialized = True
