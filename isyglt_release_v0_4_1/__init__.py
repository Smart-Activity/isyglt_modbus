"""ISYGLT integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import CONF_TIMEOUT, DOMAIN, PLATFORMS
from .modbus import ISYGLTModbusClient


@dataclass(slots=True)
class ISYGLTRuntimeData:
    """Runtime data for a controller config entry."""

    client: ISYGLTModbusClient
    controller_device_id: str


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ISYGLT from a config entry."""
    client = ISYGLTModbusClient(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        timeout=entry.data[CONF_TIMEOUT],
    )

    if not await client.async_connect():
        return False

    device_registry = dr.async_get(hass)
    controller = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"controller_{entry.entry_id}")},
        manufacturer="ISYGLT",
        model="Modbus TCP Controller",
        name=entry.title,
    )

    entry.runtime_data = ISYGLTRuntimeData(
        client=client,
        controller_device_id=controller.id,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an ISYGLT config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.client.async_close()
    return unloaded
