from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, is_dataclass
from types import MappingProxyType
from typing import Any

from brain.perception_models import PERCEPTION_RUNTIME_MODE, PERCEPTION_VERSION


PERCEPTION_SITUATION_DIAGNOSTICS_VERSION = "5.5.2"
PERCEPTION_SITUATION_DIAGNOSTICS_SOURCE = "perception_situation_diagnostics"


def _plain(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "to_dict"):
        return _plain(value.to_dict())
    if is_dataclass(value):
        return _plain(asdict(value))
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


def _as_dict(value: Any) -> dict:
    plain = _plain(value)
    return plain if isinstance(plain, dict) else {}


def build_perception_situation_diagnostics(
    *,
    percept: Any = None,
    signal_set: Any = None,
) -> dict:
    """Summarize Perception inputs for Business Situation diagnostics only."""

    percept_payload = _as_dict(percept)
    signal_set_payload = _as_dict(signal_set)
    return {
        "perception_situation_diagnostics_created": True,
        "perception_situation_diagnostics_version": PERCEPTION_SITUATION_DIAGNOSTICS_VERSION,
        "perception_situation_diagnostics_source": PERCEPTION_SITUATION_DIAGNOSTICS_SOURCE,
        "runtime_mode": PERCEPTION_RUNTIME_MODE,
        "perception_version": percept_payload.get("version") or PERCEPTION_VERSION,
        "percept_id": percept_payload.get("percept_id"),
        "percept_signal_count": int(percept_payload.get("signal_count") or 0),
        "percept_detected_signal_types": list(percept_payload.get("detected_signal_types") or []),
        "percept_signal_sources": list(percept_payload.get("signal_sources") or []),
        "signal_set_id": signal_set_payload.get("signal_set_id"),
        "signal_set_created": bool((signal_set_payload.get("diagnostics") or {}).get("signal_set_created")),
        "signal_registry_created": bool(
            (signal_set_payload.get("diagnostics") or {}).get("signal_registry_created")
            or (percept_payload.get("diagnostics") or {}).get("signal_registry_created")
        ),
        "canonical_signal_count": int(signal_set_payload.get("signal_count") or 0),
        "canonical_signal_types": list(signal_set_payload.get("signal_types") or []),
        "canonical_signal_sources": list(signal_set_payload.get("signal_sources") or []),
        "handoff_changed_business_situation": False,
        "routing_changed": False,
        "planner_changed": False,
        "workflow_changed": False,
        "responses_changed": False,
        "memory_changed": False,
        "execution_changed": False,
        "commit_boundary_changed": False,
    }
