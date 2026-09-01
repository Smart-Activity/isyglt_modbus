"""Translate native ISYGLT addresses to zero-based Modbus protocol addresses."""

from __future__ import annotations

from dataclasses import dataclass
import re

REGISTER_COIL = "coil"
REGISTER_DISCRETE_INPUT = "discrete_input"
REGISTER_INPUT_REGISTER = "input_register"
REGISTER_HOLDING_REGISTER = "holding_register"


class ISYGLTAddressError(ValueError):
    """Raised when an ISYGLT address cannot be translated."""


@dataclass(frozen=True, slots=True)
class ISYGLTAddress:
    """Resolved ISYGLT address."""

    address_type: str
    native_address: str
    register_type: str
    protocol_address: int
    reference_address: str


def _validate_protocol_address(value: int) -> int:
    if not 0 <= value <= 65535:
        raise ISYGLTAddressError("Address is outside the Modbus protocol range")
    return value


def resolve_m(value: str | int) -> ISYGLTAddress:
    """Resolve M n to 4xxxxx / holding-register space.

    ISYGLT/Modbus documentation is one-based (M 1 == 400001), while
    PyModbus addresses the protocol PDU zero-based (M 1 == address 0).
    """
    text = str(value).strip().upper()
    text = re.sub(r"^M\s*", "", text)
    if not text.isdigit():
        raise ISYGLTAddressError("M address must be a positive whole number")
    number = int(text)
    if number < 1:
        raise ISYGLTAddressError("M address must start at 1")
    protocol = _validate_protocol_address(number - 1)
    return ISYGLTAddress(
        address_type="M",
        native_address=str(number),
        register_type=REGISTER_HOLDING_REGISTER,
        protocol_address=protocol,
        reference_address=f"4{number:05d}",
    )


def _resolve_bit_address(prefix: str, value: str, register_type: str, reference_prefix: str) -> ISYGLTAddress:
    text = str(value).strip().upper()
    text = re.sub(rf"^{prefix}\s*", "", text)
    match = re.fullmatch(r"(\d+)\s*[\.]\s*([1-8])", text)
    if not match:
        raise ISYGLTAddressError(f"{prefix} address must use group.bit, for example 1.1 or 30.3")

    group = int(match.group(1))
    bit = int(match.group(2))
    if group < 1:
        raise ISYGLTAddressError(f"{prefix} group must start at 1")

    one_based = ((group - 1) * 8) + bit
    protocol = _validate_protocol_address(one_based - 1)
    return ISYGLTAddress(
        address_type=prefix,
        native_address=f"{group}.{bit}",
        register_type=register_type,
        protocol_address=protocol,
        reference_address=f"{reference_prefix}{one_based:05d}",
    )


def resolve_ne(value: str) -> ISYGLTAddress:
    """Resolve NE group.bit to 0xxxxx / coil space."""
    return _resolve_bit_address("NE", value, REGISTER_COIL, "0")


def resolve_na(value: str) -> ISYGLTAddress:
    """Resolve NA group.bit to 1xxxxx / discrete-input space."""
    return _resolve_bit_address("NA", value, REGISTER_DISCRETE_INPUT, "1")


def resolve_sm(value: str | int) -> ISYGLTAddress:
    """Resolve SM n to 3xxxxx / input-register space."""
    text = str(value).strip().upper()
    text = re.sub(r"^SM\s*", "", text)
    if not text.isdigit():
        raise ISYGLTAddressError("SM address must be a positive whole number")
    number = int(text)
    if number < 1:
        raise ISYGLTAddressError("SM address must start at 1")
    protocol = _validate_protocol_address(number - 1)
    return ISYGLTAddress(
        address_type="SM",
        native_address=str(number),
        register_type=REGISTER_INPUT_REGISTER,
        protocol_address=protocol,
        reference_address=f"3{number:05d}",
    )


def resolve_light_address(light_kind: str, value: str) -> ISYGLTAddress:
    """Resolve a Light address using its ISYGLT light kind."""
    if light_kind == "dimmable":
        return resolve_m(value)
    if light_kind == "switchable":
        return resolve_ne(value)
    raise ISYGLTAddressError(f"Unsupported light kind: {light_kind}")
