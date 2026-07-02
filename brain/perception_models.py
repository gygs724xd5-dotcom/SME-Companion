from __future__ import annotations

from dataclasses import dataclass, fields
from types import MappingProxyType
from typing import Any, TypeVar


PERCEPTION_VERSION = "5.5.0"
PERCEPTION_CREATED_BY = "perception_engine"
PERCEPTION_RUNTIME_MODE = "diagnostics_only"


T = TypeVar("T", bound="Percept")


def _freeze(value: Any) -> Any:
    if isinstance(value, MappingProxyType):
        return value
    if isinstance(value, dict):
        return MappingProxyType(
            {
                str(key): _freeze(value[key])
                for key in sorted(value.keys(), key=lambda item: str(item))
            }
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return tuple(_freeze(item) for item in sorted(value, key=str))
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, MappingProxyType):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True)
class Percept:
    percept_id: str = ""
    timestamp: str = ""
    version: str = PERCEPTION_VERSION

    user_message: str = ""
    conversation_history_reference: Any = None
    business_memory_reference: Any = None
    store_profile_reference: Any = None
    uploaded_documents: tuple = ()
    uploaded_images: tuple = ()
    dashboard_state: Any = None
    active_workspace: str = ""
    current_context: Any = None

    detected_signal_types: tuple = ()
    signal_sources: tuple = ()
    signal_count: int = 0

    diagnostics: Any = None
    runtime_mode: str = PERCEPTION_RUNTIME_MODE
    created_by: str = PERCEPTION_CREATED_BY

    def __post_init__(self) -> None:
        object.__setattr__(self, "user_message", str(self.user_message or ""))
        object.__setattr__(self, "active_workspace", str(self.active_workspace or ""))
        object.__setattr__(self, "timestamp", str(self.timestamp or ""))
        object.__setattr__(self, "version", str(self.version or PERCEPTION_VERSION))
        object.__setattr__(self, "runtime_mode", str(self.runtime_mode or PERCEPTION_RUNTIME_MODE))
        object.__setattr__(self, "created_by", str(self.created_by or PERCEPTION_CREATED_BY))

        for name in (
            "conversation_history_reference",
            "business_memory_reference",
            "store_profile_reference",
            "uploaded_documents",
            "uploaded_images",
            "dashboard_state",
            "current_context",
            "detected_signal_types",
            "signal_sources",
            "diagnostics",
        ):
            object.__setattr__(self, name, _freeze(getattr(self, name)))

    def to_dict(self) -> dict:
        return {item.name: _thaw(getattr(self, item.name)) for item in fields(self)}

    @classmethod
    def from_dict(cls: type[T], data: dict | None) -> T:
        source = data or {}
        allowed = {item.name for item in fields(cls)}
        values = {key: source[key] for key in source if key in allowed}
        return cls(**values)
