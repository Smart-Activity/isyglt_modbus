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


def test_scene_trigger_uses_ne():
    address = module.resolve_scene_trigger_address("3.2")
    assert address.address_type == "NE"
    assert address.register_type == "coil"
    assert address.protocol_address == 17
    assert address.reference_address == "000018"


def test_scene_feedback_uses_na():
    address = module.resolve_scene_feedback_address("3.2")
    assert address.address_type == "NA"
    assert address.register_type == "discrete_input"
    assert address.protocol_address == 17
    assert address.reference_address == "100018"


def test_climate_target_uses_m():
    address = module.resolve_climate_target_address("21")
    assert address.address_type == "M"
    assert address.register_type == "holding_register"
    assert address.protocol_address == 20
    assert address.reference_address == "400021"


def test_climate_current_uses_sm():
    address = module.resolve_climate_current_address("21")
    assert address.address_type == "SM"
    assert address.register_type == "input_register"
    assert address.protocol_address == 20
    assert address.reference_address == "300021"


def test_climate_command_uses_ne():
    address = module.resolve_climate_command_address("10.4")
    assert address.address_type == "NE"
    assert address.protocol_address == 75


def test_climate_feedback_uses_na():
    address = module.resolve_climate_feedback_address("10.4")
    assert address.address_type == "NA"
    assert address.protocol_address == 75
