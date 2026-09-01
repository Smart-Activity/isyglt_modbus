"""Shared Modbus TCP communication for ISYGLT."""

from __future__ import annotations

import asyncio
import logging

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

_LOGGER = logging.getLogger(__name__)


class ISYGLTModbusError(Exception):
    """Raised when ISYGLT Modbus communication fails."""


class ISYGLTModbusClient:
    """Serialize and manage Modbus TCP requests for one controller."""

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self._client = AsyncModbusTcpClient(
            host,
            port=port,
            timeout=timeout,
            retries=2,
            name="isyglt",
        )
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        """Return whether the TCP client is connected."""
        return self._client.connected

    async def async_connect(self) -> bool:
        """Connect to the controller."""
        try:
            return bool(await self._client.connect())
        except (ModbusException, OSError) as err:
            _LOGGER.debug("ISYGLT Modbus connect failed: %s", err)
            return False

    async def async_close(self) -> None:
        """Close the Modbus connection."""
        self._client.close()

    async def _ensure_connected(self) -> None:
        if self._client.connected:
            return
        if not await self.async_connect():
            raise ISYGLTModbusError("Unable to connect to ISYGLT Modbus TCP controller")

    async def async_read_holding_register(self, slave: int, address: int) -> int:
        """Read one holding register (FC03)."""
        async with self._lock:
            await self._ensure_connected()
            try:
                result = await self._client.read_holding_registers(
                    address,
                    count=1,
                    device_id=slave,
                )
            except (ModbusException, OSError) as err:
                raise ISYGLTModbusError(str(err)) from err

            if result is None or result.isError() or not getattr(result, "registers", None):
                raise ISYGLTModbusError(
                    f"Read failed for slave {slave}, holding register {address}"
                )
            return int(result.registers[0])

    async def async_write_holding_register(
        self, slave: int, address: int, value: int
    ) -> None:
        """Write one holding register (FC06)."""
        async with self._lock:
            await self._ensure_connected()
            try:
                result = await self._client.write_register(
                    address,
                    value,
                    device_id=slave,
                )
            except (ModbusException, OSError) as err:
                raise ISYGLTModbusError(str(err)) from err

            if result is None or result.isError():
                raise ISYGLTModbusError(
                    f"Write failed for slave {slave}, holding register {address}"
                )

    async def async_read_coil(self, slave: int, address: int) -> bool:
        """Read one coil (FC01)."""
        async with self._lock:
            await self._ensure_connected()
            try:
                result = await self._client.read_coils(
                    address,
                    count=1,
                    device_id=slave,
                )
            except (ModbusException, OSError) as err:
                raise ISYGLTModbusError(str(err)) from err

            if result is None or result.isError() or not getattr(result, "bits", None):
                raise ISYGLTModbusError(
                    f"Read failed for slave {slave}, coil {address}"
                )
            return bool(result.bits[0])


    async def async_read_discrete_input(self, slave: int, address: int) -> bool:
        """Read one discrete input (FC02)."""
        async with self._lock:
            await self._ensure_connected()
            try:
                result = await self._client.read_discrete_inputs(
                    address,
                    count=1,
                    device_id=slave,
                )
            except (ModbusException, OSError) as err:
                raise ISYGLTModbusError(str(err)) from err

            if result is None or result.isError() or not getattr(result, "bits", None):
                raise ISYGLTModbusError(
                    f"Read failed for slave {slave}, discrete input {address}"
                )
            return bool(result.bits[0])

    async def async_write_coil(
        self, slave: int, address: int, value: bool
    ) -> None:
        """Write one coil (FC05)."""
        async with self._lock:
            await self._ensure_connected()
            try:
                result = await self._client.write_coil(
                    address,
                    value,
                    device_id=slave,
                )
            except (ModbusException, OSError) as err:
                raise ISYGLTModbusError(str(err)) from err

            if result is None or result.isError():
                raise ISYGLTModbusError(
                    f"Write failed for slave {slave}, coil {address}"
                )


    async def async_pulse_coil(
        self, slave: int, address: int, duration: float
    ) -> None:
        """Pulse one coil ON and always attempt to return it to OFF."""
        await self.async_write_coil(slave, address, True)
        try:
            await asyncio.sleep(duration)
        finally:
            await self.async_write_coil(slave, address, False)
