from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from types import MappingProxyType
from typing import Any

from brain.perception_models import (
    PERCEPTION_CREATED_BY,
    PERCEPTION_RUNTIME_MODE,
    PERCEPTION_VERSION,
    Percept,
)


PERCEPTION_DIAGNOSTICS = {
    "perception_created": True,
    "runtime_mode": PERCEPTION_RUNTIME_MODE,
    "routing_changed": False,
    "planner_changed": False,
    "workflow_changed": False,
    "responses_changed": False,
    "commit_boundary_changed": False,
    "memory_changed": False,
    "execution_changed": False,
    "created_by": PERCEPTION_CREATED_BY,
    "version": PERCEPTION_VERSION,
}


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


def _as_tuple(value: Any) -> tuple:
    if value in (None, "", [], {}, ()):
        return ()
    if isinstance(value, (list, tuple, set)):
        return tuple(_plain(item) for item in value)
    return (_plain(value),)


def _has_signal(value: Any) -> bool:
    return value not in (None, "", [], {}, ())


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _stable_id(payload: dict) -> str:
    digest = hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()[:16]
    return f"percept_{digest}"


def _detected_signals(signals: dict) -> tuple[tuple[str, str], ...]:
    definitions = (
        ("user_message", "current_user_message"),
        ("conversation_history_reference", "conversation_history_reference"),
        ("business_memory_reference", "business_memory_reference"),
        ("store_profile_reference", "store_profile_reference"),
        ("uploaded_documents", "uploaded_documents"),
        ("uploaded_images", "uploaded_images"),
        ("dashboard_state", "dashboard_state"),
        ("active_workspace", "active_workspace"),
        ("current_context", "current_context"),
    )
    return tuple((field_name, signal_type) for field_name, signal_type in definitions if _has_signal(signals[field_name]))


def build_percept(
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
    percept_id: str | None = None,
    timestamp: str | None = None,
) -> Percept:
    """Normalize available runtime signals into a diagnostics-only Percept.

    Perception observes incoming signals only. It does not route, plan,
    execute workflow, prepare responses, call tools, call an LLM, or write
    memory.
    """

    signals = {
        "user_message": str(user_message or ""),
        "conversation_history_reference": _plain(conversation_history_reference),
        "business_memory_reference": _plain(business_memory_reference),
        "store_profile_reference": _plain(store_profile_reference),
        "uploaded_documents": _as_tuple(uploaded_documents),
        "uploaded_images": _as_tuple(uploaded_images),
        "dashboard_state": _plain(dashboard_state),
        "active_workspace": str(active_workspace or ""),
        "current_context": _plain(current_context),
    }
    detected = _detected_signals(signals)
    detected_signal_types = tuple(signal_type for _, signal_type in detected)
    signal_sources = tuple(field_name for field_name, _ in detected)
    normalized_timestamp = str(timestamp or "")

    id_payload = {
        "timestamp": normalized_timestamp,
        "version": PERCEPTION_VERSION,
        "signals": signals,
        "detected_signal_types": detected_signal_types,
        "signal_sources": signal_sources,
    }
    normalized_percept_id = str(percept_id or _stable_id(id_payload))

    return Percept(
        percept_id=normalized_percept_id,
        timestamp=normalized_timestamp,
        version=PERCEPTION_VERSION,
        user_message=signals["user_message"],
        conversation_history_reference=signals["conversation_history_reference"],
        business_memory_reference=signals["business_memory_reference"],
        store_profile_reference=signals["store_profile_reference"],
        uploaded_documents=signals["uploaded_documents"],
        uploaded_images=signals["uploaded_images"],
        dashboard_state=signals["dashboard_state"],
        active_workspace=signals["active_workspace"],
        current_context=signals["current_context"],
        detected_signal_types=detected_signal_types,
        signal_sources=signal_sources,
        signal_count=len(detected_signal_types),
        diagnostics=deepcopy(PERCEPTION_DIAGNOSTICS),
        runtime_mode=PERCEPTION_RUNTIME_MODE,
        created_by=PERCEPTION_CREATED_BY,
    )
