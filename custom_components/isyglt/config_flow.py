"""Config flow for ISYGLT."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

import voluptuous as vol
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector

from .addressing import (
    ISYGLTAddressError,
    resolve_cover_address,
    resolve_climate_command_address,
    resolve_climate_current_address,
    resolve_climate_feedback_address,
    resolve_climate_target_address,
    resolve_light_address,
    resolve_scene_feedback_address,
    resolve_scene_trigger_address,
    resolve_switch_address,
)
from .const import (
    CONF_AREA_ID, CONF_CLIMATES, CONF_CLOSE_VALUE, CONF_COMMAND_REGISTER,
    CONF_TARGET_TEMP_ADDRESS, CONF_CURRENT_TEMP_ADDRESS, CONF_IS_AIRCO,
    CONF_FAN_HIGH_NE, CONF_FAN_HIGH_NA, CONF_FAN_MEDIUM_NE, CONF_FAN_MEDIUM_NA,
    CONF_FAN_LOW_NE, CONF_FAN_LOW_NA, CONF_AIRCO_POWER_NE, CONF_AIRCO_POWER_NA,
    CONF_SCENES, CONF_SCENE_FEEDBACK_ADDRESS, CONF_SCENE_TRIGGER_ADDRESS,
    CONF_DOWN_ADDRESS,
    CONF_ISYGLT_ADDRESS, CONF_LIGHT_KIND,
    CONF_COVERS, CONF_CURRENT_TEMP_REGISTER, CONF_ENTITY_UID, CONF_LIGHTS,
    CONF_MAX_TEMP, CONF_MIN_TEMP, CONF_OFF_VALUE, CONF_ON_VALUE, CONF_OPEN_VALUE,
    CONF_POSITION_REGISTER, CONF_REGISTER, CONF_SLAVE, CONF_STOP_VALUE,
    CONF_UP_ADDRESS,
    CONF_SWITCHES, CONF_TARGET_TEMP_REGISTER, CONF_TEMP_SCALE, CONF_TEMP_STEP,
    CONF_TIMEOUT, DEFAULT_CONTROLLER_NAME, DEFAULT_PORT, DEFAULT_REGISTER,
    DEFAULT_CLIMATE_TARGET_ADDRESS, DEFAULT_CLIMATE_CURRENT_ADDRESS,
    DEFAULT_CLIMATE_MIN_TEMP, DEFAULT_CLIMATE_MAX_TEMP, DEFAULT_CLIMATE_TEMP_STEP,
    DEFAULT_CLIMATE_TEMP_SCALE,
    DEFAULT_COVER_DOWN_ADDRESS, DEFAULT_COVER_UP_ADDRESS, DEFAULT_LIGHT_ADDRESS, DEFAULT_LIGHT_KIND, DEFAULT_SWITCH_ADDRESS, DEFAULT_SCENE_TRIGGER_ADDRESS, DEFAULT_SCENE_FEEDBACK_ADDRESS, DEFAULT_SLAVE, DEFAULT_TIMEOUT, DOMAIN,
    LIGHT_KIND_DIMMABLE, LIGHT_KIND_SWITCHABLE,
)


async def _async_test_connection(host: str, port: int, timeout: float) -> bool:
    client = AsyncModbusTcpClient(host, port=port, timeout=timeout, retries=0)
    try:
        return bool(await client.connect())
    except (ModbusException, OSError):
        return False
    finally:
        client.close()


def _entity_base_schema() -> dict:
    return {
        vol.Required(CONF_NAME): selector.TextSelector(),
        vol.Required(CONF_AREA_ID): selector.AreaSelector(),
        vol.Required(CONF_SLAVE, default=DEFAULT_SLAVE): vol.All(vol.Coerce(int), vol.Range(min=0, max=247)),
    }


class ISYGLTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]
            timeout = user_input[CONF_TIMEOUT]
            if await _async_test_connection(host, port, timeout):
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={CONF_HOST: host, CONF_PORT: port, CONF_TIMEOUT: timeout},
                    options={CONF_LIGHTS: [], CONF_SWITCHES: [], CONF_COVERS: [], CONF_CLIMATES: [], CONF_SCENES: []},
                )
            errors["base"] = "cannot_connect"
        schema = vol.Schema({
            vol.Required(CONF_NAME, default=DEFAULT_CONTROLLER_NAME): str,
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Required(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=30)),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "ISYGLTOptionsFlow":
        return ISYGLTOptionsFlow()


class ISYGLTOptionsFlow(OptionsFlowWithReload):
    def __init__(self) -> None:
        super().__init__()
        self._pending_climate: dict[str, Any] | None = None

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        menu = ["add_light", "add_switch", "add_cover", "add_climate", "add_scene"]
        for key, step in ((CONF_LIGHTS, "remove_light"), (CONF_SWITCHES, "remove_switch"), (CONF_COVERS, "remove_cover"), (CONF_CLIMATES, "remove_climate"), (CONF_SCENES, "remove_scene")):
            if self.config_entry.options.get(key):
                menu.append(step)
        return self.async_show_menu(step_id="init", menu_options=menu)

    def _save_entity(self, collection: str, user_input: dict[str, Any]) -> ConfigFlowResult:
        options = deepcopy(dict(self.config_entry.options))
        items = list(options.get(collection, []))
        items.append({CONF_ENTITY_UID: uuid4().hex, **user_input})
        options[collection] = items
        return self.async_create_entry(data=options)

    async def async_step_add_light(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                resolved = resolve_light_address(
                    user_input[CONF_LIGHT_KIND], user_input[CONF_ISYGLT_ADDRESS]
                )
            except ISYGLTAddressError:
                errors[CONF_ISYGLT_ADDRESS] = "invalid_isyglt_address"
            else:
                # Store the normalized native ISYGLT address, never a raw Modbus offset.
                user_input[CONF_ISYGLT_ADDRESS] = resolved.native_address
                return self._save_entity(CONF_LIGHTS, user_input)

        schema = _entity_base_schema()
        schema.update({
            vol.Required(CONF_LIGHT_KIND, default=DEFAULT_LIGHT_KIND): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=LIGHT_KIND_DIMMABLE, label="Dimbaar (M)"),
                        selector.SelectOptionDict(value=LIGHT_KIND_SWITCHABLE, label="Schakelbaar (NE)"),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(CONF_ISYGLT_ADDRESS, default=DEFAULT_LIGHT_ADDRESS): selector.TextSelector(),
        })
        return self.async_show_form(
            step_id="add_light", data_schema=vol.Schema(schema), errors=errors
        )

    async def async_step_add_switch(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                resolved = resolve_switch_address(user_input[CONF_ISYGLT_ADDRESS])
            except ISYGLTAddressError:
                errors[CONF_ISYGLT_ADDRESS] = "invalid_switch_address"
            else:
                user_input[CONF_ISYGLT_ADDRESS] = resolved.native_address
                return self._save_entity(CONF_SWITCHES, user_input)

        schema = _entity_base_schema()
        schema.update({
            vol.Required(CONF_ISYGLT_ADDRESS, default=DEFAULT_SWITCH_ADDRESS): selector.TextSelector(),
        })
        return self.async_show_form(
            step_id="add_switch", data_schema=vol.Schema(schema), errors=errors
        )

    async def async_step_add_cover(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                up = resolve_cover_address(user_input[CONF_UP_ADDRESS])
            except ISYGLTAddressError:
                errors[CONF_UP_ADDRESS] = "invalid_cover_address"
            else:
                try:
                    down = resolve_cover_address(user_input[CONF_DOWN_ADDRESS])
                except ISYGLTAddressError:
                    errors[CONF_DOWN_ADDRESS] = "invalid_cover_address"
                else:
                    if up.protocol_address == down.protocol_address:
                        errors[CONF_DOWN_ADDRESS] = "cover_addresses_equal"
                    else:
                        user_input[CONF_UP_ADDRESS] = up.native_address
                        user_input[CONF_DOWN_ADDRESS] = down.native_address
                        return self._save_entity(CONF_COVERS, user_input)

        schema = _entity_base_schema()
        schema.update({
            vol.Required(CONF_UP_ADDRESS, default=DEFAULT_COVER_UP_ADDRESS): selector.TextSelector(),
            vol.Required(CONF_DOWN_ADDRESS, default=DEFAULT_COVER_DOWN_ADDRESS): selector.TextSelector(),
        })
        return self.async_show_form(step_id="add_cover", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_add_scene(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                trigger = resolve_scene_trigger_address(user_input[CONF_SCENE_TRIGGER_ADDRESS])
            except ISYGLTAddressError:
                errors[CONF_SCENE_TRIGGER_ADDRESS] = "invalid_scene_trigger_address"
            else:
                try:
                    feedback = resolve_scene_feedback_address(user_input[CONF_SCENE_FEEDBACK_ADDRESS])
                except ISYGLTAddressError:
                    errors[CONF_SCENE_FEEDBACK_ADDRESS] = "invalid_scene_feedback_address"
                else:
                    user_input[CONF_SCENE_TRIGGER_ADDRESS] = trigger.native_address
                    user_input[CONF_SCENE_FEEDBACK_ADDRESS] = feedback.native_address
                    return self._save_entity(CONF_SCENES, user_input)

        schema = _entity_base_schema()
        schema.update({
            vol.Required(CONF_SCENE_TRIGGER_ADDRESS, default=DEFAULT_SCENE_TRIGGER_ADDRESS): selector.TextSelector(),
            vol.Required(CONF_SCENE_FEEDBACK_ADDRESS, default=DEFAULT_SCENE_FEEDBACK_ADDRESS): selector.TextSelector(),
        })
        return self.async_show_form(step_id="add_scene", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_add_climate(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                target = resolve_climate_target_address(user_input[CONF_TARGET_TEMP_ADDRESS])
            except ISYGLTAddressError:
                errors[CONF_TARGET_TEMP_ADDRESS] = "invalid_climate_target_address"
            else:
                try:
                    current = resolve_climate_current_address(user_input[CONF_CURRENT_TEMP_ADDRESS])
                except ISYGLTAddressError:
                    errors[CONF_CURRENT_TEMP_ADDRESS] = "invalid_climate_current_address"
                else:
                    user_input[CONF_TARGET_TEMP_ADDRESS] = target.native_address
                    user_input[CONF_CURRENT_TEMP_ADDRESS] = current.native_address
                    # Fixed first native implementation: 10-40 °C, 1 °C steps, raw value == °C.
                    user_input[CONF_MIN_TEMP] = DEFAULT_CLIMATE_MIN_TEMP
                    user_input[CONF_MAX_TEMP] = DEFAULT_CLIMATE_MAX_TEMP
                    user_input[CONF_TEMP_STEP] = DEFAULT_CLIMATE_TEMP_STEP
                    user_input[CONF_TEMP_SCALE] = DEFAULT_CLIMATE_TEMP_SCALE
                    if user_input[CONF_IS_AIRCO]:
                        self._pending_climate = user_input
                        return await self.async_step_add_climate_airco()
                    return self._save_entity(CONF_CLIMATES, user_input)

        schema = _entity_base_schema()
        schema.update({
            vol.Required(CONF_TARGET_TEMP_ADDRESS, default=DEFAULT_CLIMATE_TARGET_ADDRESS): selector.TextSelector(),
            vol.Required(CONF_CURRENT_TEMP_ADDRESS, default=DEFAULT_CLIMATE_CURRENT_ADDRESS): selector.TextSelector(),
            vol.Required(CONF_IS_AIRCO, default=False): selector.BooleanSelector(),
        })
        return self.async_show_form(step_id="add_climate", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_add_climate_airco(self, user_input=None) -> ConfigFlowResult:
        if self._pending_climate is None:
            return await self.async_step_add_climate()

        errors: dict[str, str] = {}
        fields = (
            (CONF_FAN_HIGH_NE, resolve_climate_command_address, "invalid_climate_ne_address"),
            (CONF_FAN_HIGH_NA, resolve_climate_feedback_address, "invalid_climate_na_address"),
            (CONF_FAN_MEDIUM_NE, resolve_climate_command_address, "invalid_climate_ne_address"),
            (CONF_FAN_MEDIUM_NA, resolve_climate_feedback_address, "invalid_climate_na_address"),
            (CONF_FAN_LOW_NE, resolve_climate_command_address, "invalid_climate_ne_address"),
            (CONF_FAN_LOW_NA, resolve_climate_feedback_address, "invalid_climate_na_address"),
            (CONF_AIRCO_POWER_NE, resolve_climate_command_address, "invalid_climate_ne_address"),
            (CONF_AIRCO_POWER_NA, resolve_climate_feedback_address, "invalid_climate_na_address"),
        )
        if user_input is not None:
            normalized = dict(user_input)
            protocol_seen: set[tuple[str, int]] = set()
            for key, resolver, error_key in fields:
                try:
                    resolved = resolver(user_input[key])
                except ISYGLTAddressError:
                    errors[key] = error_key
                    continue
                normalized[key] = resolved.native_address
                marker = (resolved.register_type, resolved.protocol_address)
                if marker in protocol_seen:
                    errors[key] = "duplicate_climate_address"
                protocol_seen.add(marker)
            if not errors:
                climate = {**self._pending_climate, **normalized}
                self._pending_climate = None
                return self._save_entity(CONF_CLIMATES, climate)

        schema = vol.Schema({
            vol.Required(CONF_FAN_HIGH_NE): selector.TextSelector(),
            vol.Required(CONF_FAN_HIGH_NA): selector.TextSelector(),
            vol.Required(CONF_FAN_MEDIUM_NE): selector.TextSelector(),
            vol.Required(CONF_FAN_MEDIUM_NA): selector.TextSelector(),
            vol.Required(CONF_FAN_LOW_NE): selector.TextSelector(),
            vol.Required(CONF_FAN_LOW_NA): selector.TextSelector(),
            vol.Required(CONF_AIRCO_POWER_NE): selector.TextSelector(),
            vol.Required(CONF_AIRCO_POWER_NA): selector.TextSelector(),
        })
        return self.async_show_form(step_id="add_climate_airco", data_schema=schema, errors=errors)

    async def _remove(self, collection: str, step_id: str, user_input, empty_reason: str) -> ConfigFlowResult:
        items = list(self.config_entry.options.get(collection, []))
        if not items:
            return self.async_abort(reason=empty_reason)
        if user_input is not None:
            uid = user_input[CONF_ENTITY_UID]
            options = deepcopy(dict(self.config_entry.options))
            options[collection] = [item for item in items if item[CONF_ENTITY_UID] != uid]
            return self.async_create_entry(data=options)
        choices = [selector.SelectOptionDict(value=item[CONF_ENTITY_UID], label=f"{item[CONF_NAME]} — slave {item[CONF_SLAVE]}") for item in items]
        return self.async_show_form(step_id=step_id, data_schema=vol.Schema({
            vol.Required(CONF_ENTITY_UID): selector.SelectSelector(selector.SelectSelectorConfig(options=choices, mode=selector.SelectSelectorMode.DROPDOWN))
        }))

    async def async_step_remove_light(self, user_input=None):
        return await self._remove(CONF_LIGHTS, "remove_light", user_input, "no_lights")

    async def async_step_remove_switch(self, user_input=None):
        return await self._remove(CONF_SWITCHES, "remove_switch", user_input, "no_switches")

    async def async_step_remove_cover(self, user_input=None):
        return await self._remove(CONF_COVERS, "remove_cover", user_input, "no_covers")

    async def async_step_remove_climate(self, user_input=None):
        return await self._remove(CONF_CLIMATES, "remove_climate", user_input, "no_climates")

    async def async_step_remove_scene(self, user_input=None):
        return await self._remove(CONF_SCENES, "remove_scene", user_input, "no_scenes")
