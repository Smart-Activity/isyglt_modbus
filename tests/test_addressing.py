"""Pure-Python checks for the ISYGLT address mapping."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

path = Path(__file__).parents[1] / "custom_components" / "isyglt" / "addressing.py"
spec = spec_from_file_location("isyglt_addressing", path)
module = module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_m() -> None:
    result = module.resolve_m("8")
    assert result.protocol_address == 7
    assert result.reference_address == "400008"


def test_ne_first() -> None:
    result = module.resolve_ne("1.1")
    assert result.protocol_address == 0
    assert result.reference_address == "000001"


def test_ne_group() -> None:
    result = module.resolve_ne("30.3")
    assert result.protocol_address == 234
    assert result.reference_address == "000235"


def test_na() -> None:
    result = module.resolve_na("2.1")
    assert result.protocol_address == 8
    assert result.reference_address == "100009"


def test_sm() -> None:
    result = module.resolve_sm("204")
    assert result.protocol_address == 203
    assert result.reference_address == "300204"


def test_switch_uses_ne_addressing():
    result = module.resolve_switch_address("30.3")
    assert result.address_type == "NE"
    assert result.register_type == "coil"
    assert result.native_address == "30.3"
    assert result.reference_address == "000235"
    assert result.protocol_address == 234


def test_cover_ne_address():
    address = module.resolve_cover_address("20.2")
    assert address.address_type == "NE"
    assert address.protocol_address == 153
    assert address.reference_address == "000154"
