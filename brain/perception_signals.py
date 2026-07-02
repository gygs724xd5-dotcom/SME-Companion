from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, dataclass, fields, is_dataclass
from types import MappingProxyType
from typing import Any, TypeVar

from brain.perception_models import PERCEPTION_RUNTIME_MODE
from brain.perception_signal_registry import (
    SIGNAL_REGISTRY_VERSION,
    get_signal_type_definition,
    signal_type_exists,
)


SIGNAL_VERSION = "5.5.1"
SIGNAL_SET_VERSION = "5.5.1"

SIGNAL_DIAGNOSTICS = MappingProxyType(
    {
        "signal_registry_created": True,
        "runtime_mode": PERCEPTION_RUNTIME_MODE,
        "routing_changed": False,
        "planner_changed": False,
        "workflow_changed": False,
        "responses_changed": False,
        "memory_changed": False,
        "execution_changed": False,
        "commit_boundary_changed": False,
        "version": SIGNAL_VERSION,
    }
)

SIGNAL_SET_DIAGNOSTICS = MappingProxyType(
    {
        "signal_registry_created": True,
        "signal_set_created": True,
        "runtime_mode": PERCEPTION_RUNTIME_MODE,
        "routing_changed": False,
        "planner_changed": False,
        "workflow_changed": False,
        "responses_changed": False,
        "memory_changed": False,
        "execution_changed": False,
        "commit_boundary_changed": False,
        "version": SIGNAL_SET_VERSION,
        "registry_version": SIGNAL_REGISTRY_VERSION,
    }
)


TSignal = TypeVar("TSignal", bound="Signal")
TSignalSet = TypeVar("TSignalSet", bound="SignalSet")


def _plain(value: Any) -> Any:
    if value is None:
        return None
    if is_dataclass(value):
        return _plain(asdict(value))
    if hasattr(value, "to_dict"):
        return _plain(value.to_dict())
    if isinstance(value, MappingProxyType):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, dict):
        return {
            str(key): _plain(value[key])
            for key in sorted(value.keys(), key=lambda item: str(item))
        }
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, set):
        return [_plain(item) for item in sorted(value, key=str)]
    return deepcopy(value)


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
    return deepcopy(value)


def _thaw(value: Any) -> Any:
    if isinstance(value, MappingProxyType):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return deepcopy(value)


def _stable_json(value: Any) -> str:
    return json.dumps(_plain(value), ensure_ascii=False, sort_keys=True, default=str)


def _stable_id(prefix: str, payload: dict) -> str:
    digest = hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _has_signal(value: Any) -> bool:
    return value not in (None, "", [], {}, ())


def _payload_summary(value: Any) -> Any:
    plain = _plain(value)
    if isinstance(plain, str):
        return plain
    if isinstance(plain, dict):
        return {
            "kind": "mapping",
            "keys": sorted(str(key) for key in plain.keys()),
        }
    if isinstance(plain, list):
        return {"kind": "list", "count": len(plain)}
    return plain


def _signal_source(signal_type: str, fallback: str = "") -> str:
    definition = get_signal_type_definition(signal_type)
    return str(fallback or definition.get("source") or "unknown")


def _signal_modality(signal_type: str, fallback: str = "") -> str:
    definition = get_signal_type_definition(signal_type)
    return str(fallback or definition.get("modality") or "unknown")


@dataclass(frozen=True)
class Signal:
    signal_id: str = ""
    signal_type: str = ""
    source: str = ""
    source_ref: Any = None
    captured_at: str = ""
    modality: str = ""
    payload_summary: Any = None
    metadata: Any = None
    diagnostics: Any = None
    version: str = SIGNAL_VERSION

    def __post_init__(self) -> None:
        signal_type = str(self.signal_type or "unknown")
        source = _signal_source(signal_type, self.source)
        modality = _signal_modality(signal_type, self.modality)
        diagnostics = dict(SIGNAL_DIAGNOSTICS)
        diagnostics["signal_type_registered"] = signal_type_exists(signal_type)
        diagnostics["unknown_signal_type"] = not signal_type_exists(signal_type)
        id_payload = {
            "signal_type": signal_type,
            "source": source,
            "source_ref": _plain(self.source_ref),
            "captured_at": str(self.captured_at or ""),
            "modality": modality,
            "payload_summary": _plain(self.payload_summary),
            "metadata": _plain(self.metadata),
            "version": str(self.version or SIGNAL_VERSION),
        }
        object.__setattr__(self, "signal_type", signal_type)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "modality", modality)
        object.__setattr__(self, "captured_at", str(self.captured_at or ""))
        object.__setattr__(self, "version", str(self.version or SIGNAL_VERSION))
        object.__setattr__(self, "signal_id", str(self.signal_id or _stable_id("signal", id_payload)))
        object.__setattr__(self, "source_ref", _freeze(self.source_ref))
        object.__setattr__(self, "payload_summary", _freeze(self.payload_summary))
        object.__setattr__(self, "metadata", _freeze(self.metadata or {}))
        object.__setattr__(self, "diagnostics", _freeze(diagnostics))

    def to_dict(self) -> dict:
        return {item.name: _thaw(getattr(self, item.name)) for item in fields(self)}

    @classmethod
    def from_dict(cls: type[TSignal], data: dict | None) -> TSignal:
        source = data or {}
        allowed = {item.name for item in fields(cls)}
        values = {key: source[key] for key in source if key in allowed}
        return cls(**values)


@dataclass(frozen=True)
class SignalSet:
    signal_set_id: str = ""
    signals: tuple = ()
    signal_count: int = 0
    signal_types: tuple = ()
    signal_sources: tuple = ()
    diagnostics: Any = None
    version: str = SIGNAL_SET_VERSION

    def __post_init__(self) -> None:
        signals = tuple(item if isinstance(item, Signal) else Signal.from_dict(item) for item in (self.signals or ()))
        signal_types = tuple(signal.signal_type for signal in signals)
        signal_sources = tuple(signal.source for signal in signals)
        id_payload = {
            "signals": [signal.to_dict() for signal in signals],
            "version": str(self.version or SIGNAL_SET_VERSION),
        }
        object.__setattr__(self, "signals", signals)
        object.__setattr__(self, "signal_count", len(signals))
        object.__setattr__(self, "signal_types", signal_types)
        object.__setattr__(self, "signal_sources", signal_sources)
        object.__setattr__(self, "version", str(self.version or SIGNAL_SET_VERSION))
        object.__setattr__(self, "signal_set_id", str(self.signal_set_id or _stable_id("signal_set", id_payload)))
        object.__setattr__(self, "diagnostics", _freeze(dict(SIGNAL_SET_DIAGNOSTICS)))

    def to_dict(self) -> dict:
        return {
            "signal_set_id": self.signal_set_id,
            "signals": [signal.to_dict() for signal in self.signals],
            "signal_count": self.signal_count,
            "signal_types": list(self.signal_types),
            "signal_sources": list(self.signal_sources),
            "diagnostics": _thaw(self.diagnostics),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls: type[TSignalSet], data: dict | None) -> TSignalSet:
        source = data or {}
        return cls(
            signal_set_id=source.get("signal_set_id", ""),
            signals=tuple(Signal.from_dict(item) for item in source.get("signals", []) or []),
            version=source.get("version", SIGNAL_SET_VERSION),
        )


def build_signal(
    *,
    signal_type: str,
    source_ref: Any = None,
    captured_at: str = "",
    source: str = "",
    modality: str = "",
    payload_summary: Any = None,
    metadata: Any = None,
    signal_id: str = "",
) -> Signal:
    summary = _payload_summary(source_ref) if payload_summary is None else payload_summary
    return Signal(
        signal_id=signal_id,
        signal_type=signal_type,
        source=source,
        source_ref=_plain(source_ref),
        captured_at=captured_at,
        modality=modality,
        payload_summary=summary,
        metadata=_plain(metadata or {}),
    )


def build_signal_set(signals: Any = None, *, signal_set_id: str = "") -> SignalSet:
    return SignalSet(signal_set_id=signal_set_id, signals=tuple(signals or ()))


def build_signal_set_from_percept_fields(
    *,
    user_message: str = "",
    conversation_history_reference: Any = None,
    business_memory_reference: Any = None,
    store_profile_reference: Any = None,
    uploaded_documents: Any = None,
    uploaded_images: Any = None,
    dashboard_state: Any = None,
    active_workspace: str = "",
    current_context: Any = None,
    captured_at: str = "",
) -> SignalSet:
    signals = []
    if _has_signal(user_message):
        signals.append(build_signal(signal_type="user_message", source_ref=str(user_message or ""), captured_at=captured_at))
    if _has_signal(conversation_history_reference):
        signals.append(
            build_signal(
                signal_type="conversation_history",
                source_ref=conversation_history_reference,
                captured_at=captured_at,
            )
        )
    if _has_signal(business_memory_reference):
        signals.append(
            build_signal(
                signal_type="business_memory_reference",
                source_ref=business_memory_reference,
                captured_at=captured_at,
            )
        )
    if _has_signal(store_profile_reference):
        signals.append(
            build_signal(
                signal_type="store_profile_reference",
                source_ref=store_profile_reference,
                captured_at=captured_at,
            )
        )
    for document in uploaded_documents or ():
        signals.append(build_signal(signal_type="uploaded_document", source_ref=document, captured_at=captured_at))
    for image in uploaded_images or ():
        signals.append(build_signal(signal_type="uploaded_image", source_ref=image, captured_at=captured_at))
    if _has_signal(dashboard_state):
        signals.append(build_signal(signal_type="dashboard_state", source_ref=dashboard_state, captured_at=captured_at))
    if _has_signal(active_workspace):
        signals.append(build_signal(signal_type="active_workspace", source_ref=str(active_workspace or ""), captured_at=captured_at))
    if _has_signal(current_context):
        signals.append(build_signal(signal_type="current_context", source_ref=current_context, captured_at=captured_at))
    return build_signal_set(signals)
