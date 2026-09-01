"""Base entity support for ISYGLT."""

from __future__ import annotations

from homeassistant.helpers.entity import Entity

from . import ISYGLTRuntimeData


class ISYGLTEntity(Entity):
    """Base ISYGLT entity."""

    _attr_has_entity_name = False

    def __init__(self, runtime_data: ISYGLTRuntimeData) -> None:
        self._runtime_data = runtime_data
