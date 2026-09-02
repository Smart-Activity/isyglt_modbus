"""Base entity support for ISYGLT."""

from __future__ import annotations

from homeassistant.helpers.entity import Entity

from . import ISYGLTRuntimeData


class ISYGLTEntity(Entity):
    """Base ISYGLT entity."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _isyglt_periodic_update = True

    def __init__(self, runtime_data: ISYGLTRuntimeData) -> None:
        self._runtime_data = runtime_data

    async def async_added_to_hass(self) -> None:
        """Register readable entities with the controller polling manager."""
        await super().async_added_to_hass()
        if self._isyglt_periodic_update:
            self._runtime_data.polling.register(self)
            self.async_on_remove(lambda: self._runtime_data.polling.unregister(self))
