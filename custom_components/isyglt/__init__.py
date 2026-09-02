"""ISYGLT integration."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry

from .const import (
    CONF_CLIMATES,
    CONF_COVERS,
    CONF_ENTITY_UID,
    CONF_LIGHTS,
    CONF_SCENES,
    CONF_SWITCHES,
    CONF_TIMEOUT,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .modbus import ISYGLTModbusClient


class ISYGLTPollingManager:
    """Poll all readable entities of one ISYGLT controller at one interval."""

    def __init__(self, hass: HomeAssistant, interval: float) -> None:
        self._hass = hass
        self.interval = float(interval)
        self._entities: set[Any] = set()
        self._task: asyncio.Task | None = None

    def register(self, entity: Any) -> None:
        self._entities.add(entity)

    def unregister(self, entity: Any) -> None:
        self._entities.discard(entity)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = self._hass.async_create_background_task(
                self._run(), "ISYGLT controller polling"
            )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self.interval)
            entities = tuple(self._entities)
            if not entities:
                continue
            await asyncio.gather(
                *(entity.async_update_ha_state(force_refresh=True) for entity in entities),
                return_exceptions=True,
            )


@dataclass(slots=True)
class ISYGLTRuntimeData:
    """Runtime data for a controller config entry."""

    client: ISYGLTModbusClient
    controller_device_id: str
    polling: ISYGLTPollingManager


_COLLECTION_PREFIXES: tuple[tuple[str, str], ...] = (
    (CONF_LIGHTS, "light"),
    (CONF_SWITCHES, "switch"),
    (CONF_COVERS, "cover"),
    (CONF_CLIMATES, "climate"),
    (CONF_SCENES, "scene"),
)


def _configured_device_identifiers(entry: ConfigEntry) -> set[tuple[str, str]]:
    """Return all ISYGLT device identifiers which should currently exist."""
    identifiers = {(DOMAIN, f"controller_{entry.entry_id}")}
    for collection, prefix in _COLLECTION_PREFIXES:
        for item in entry.options.get(collection, []):
            uid = item.get(CONF_ENTITY_UID)
            if uid:
                identifiers.add((DOMAIN, f"{prefix}_{entry.entry_id}_{uid}"))
    return identifiers


def _entry_device_identifier(
    entry: ConfigEntry, device_entry: DeviceEntry
) -> tuple[str, str] | None:
    """Find the ISYGLT identifier belonging to this config entry and device."""
    marker = f"_{entry.entry_id}_"
    controller = f"controller_{entry.entry_id}"
    for identifier in device_entry.identifiers:
        if identifier[0] != DOMAIN:
            continue
        if identifier[1] == controller or marker in identifier[1]:
            return identifier
    return None


def _remove_identifier_from_options(
    entry: ConfigEntry, identifier: tuple[str, str]
) -> dict | None:
    """Return options with the device represented by identifier removed."""
    value = identifier[1]
    for collection, prefix in _COLLECTION_PREFIXES:
        expected_prefix = f"{prefix}_{entry.entry_id}_"
        if not value.startswith(expected_prefix):
            continue
        uid = value[len(expected_prefix) :]
        options = deepcopy(dict(entry.options))
        old_items = list(options.get(collection, []))
        new_items = [item for item in old_items if item.get(CONF_ENTITY_UID) != uid]
        if len(new_items) == len(old_items):
            return None
        options[collection] = new_items
        return options
    return None


def _remove_stale_devices(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove orphaned ISYGLT devices left behind by older versions."""
    registry = dr.async_get(hass)
    expected = _configured_device_identifiers(entry)
    entry_marker = f"_{entry.entry_id}_"
    controller = f"controller_{entry.entry_id}"

    # In HA 2026.8+ registry.devices is a mapping-like registry container.
    # Iterate over its values (DeviceEntry objects), not its keys (device IDs),
    # and snapshot them because async_remove_device mutates the registry.
    for device in tuple(registry.devices.values()):
        matching = {
            identifier
            for identifier in device.identifiers
            if identifier[0] == DOMAIN
            and (identifier[1] == controller or entry_marker in identifier[1])
        }
        if matching and matching.isdisjoint(expected):
            registry.async_remove_device(device.id)


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

    scan_interval = float(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
    polling = ISYGLTPollingManager(hass, scan_interval)
    entry.runtime_data = ISYGLTRuntimeData(
        client=client,
        controller_device_id=controller.id,
        polling=polling,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    polling.start()

    # Entity removal does not automatically remove its device from Home\n    # Assistant. Clean any device from this entry which no longer has a\n    # corresponding item in the ISYGLT options. This also repairs orphans\n    # created by v0.8.0 and earlier.
    _remove_stale_devices(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an ISYGLT config entry."""
    await entry.runtime_data.polling.stop()
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.client.async_close()
    else:
        entry.runtime_data.polling.start()
    return unloaded


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Allow an ISYGLT child device to be deleted from the HA device UI."""
    identifier = _entry_device_identifier(config_entry, device_entry)
    if identifier is None:
        return False

    # The controller represents the complete config entry and should be removed
    # by deleting the integration itself, not as an individual child device.
    if identifier[1] == f"controller_{config_entry.entry_id}":
        return False

    options = _remove_identifier_from_options(config_entry, identifier)
    if options is None:
        # The configuration no longer contains this device, so it is already an
        # orphan and can safely be removed from the registry.
        return True

    hass.config_entries.async_update_entry(config_entry, options=options)

    # Remove the corresponding entities immediately as well. On setup the stale
    # device cleanup sees the updated options and will not recreate the device.
    await hass.config_entries.async_reload(config_entry.entry_id)
    return True
