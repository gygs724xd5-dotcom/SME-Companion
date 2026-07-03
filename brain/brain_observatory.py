from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, is_dataclass
from types import MappingProxyType
from typing import Any


BRAIN_OBSERVATORY_VERSION = "5.8.1"
BRAIN_OBSERVATORY_SOURCE = "brain_observatory"
BRAIN_OBSERVATORY_RUNTIME_MODE = "developer_diagnostics_only"

COGNITIVE_LAYERS = (
    "Reality",
    "Perception",
    "Business Situation",
    "Evidence",
    "Truth Status",
    "Evidence Gap",
    "Perspective",
    "Knowledge",
    "Business Judgment",
    "Decision",
)

CONSTITUTION_FLAGS = (
    "routing_changed",
    "planner_changed",
    "workflow_changed",
    "responses_changed",
    "execution_changed",
    "commit_changed",
)


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
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, set):
        return [_plain(item) for item in sorted(value, key=str)]
    return deepcopy(value)


def _as_dict(value: Any) -> dict:
    plain = _plain(value)
    return plain if isinstance(plain, dict) else {}


def _as_list(value: Any) -> list:
    plain = _plain(value)
    if isinstance(plain, list):
        return plain
    if plain in (None, "", {}, ()):
        return []
    return [plain]


def _first_present(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return default


def _bool_from_any(value: Any) -> bool:
    return bool(value is True or str(value).strip().lower() == "true")


def _collect_flag_values(value: Any, flag: str) -> list[bool]:
    plain = _plain(value)
    found: list[bool] = []
    if isinstance(plain, dict):
        if flag in plain:
            found.append(_bool_from_any(plain.get(flag)))
        if flag == "commit_changed" and "commit_boundary_changed" in plain:
            found.append(_bool_from_any(plain.get("commit_boundary_changed")))
        for item in plain.values():
            found.extend(_collect_flag_values(item, flag))
    elif isinstance(plain, list):
        for item in plain:
            found.extend(_collect_flag_values(item, flag))
    return found


def _status(*, exists: bool, placeholder: bool = False, violation: bool = False) -> str:
    if violation:
        return "violation"
    if placeholder:
        return "placeholder"
    return "observed" if exists else "not_available"


def _layer(
    *,
    name: str,
    runtime_state: Any = None,
    diagnostics: Any = None,
    confidence: Any = None,
    source: str = "",
    status: str = "",
) -> dict:
    runtime = _plain(runtime_state)
    diagnostic_payload = _plain(diagnostics) or {}
    exists = runtime not in (None, "", [], {}) or diagnostic_payload not in (None, "", [], {})
    return {
        "layer": name,
        "runtime_state": runtime if runtime is not None else {},
        "diagnostics": diagnostic_payload,
        "confidence": confidence,
        "source": source or "unknown",
        "status": status or _status(exists=exists),
    }


def _reality_layer(route: dict) -> dict:
    understanding = _as_dict(route.get("conversation_understanding"))
    user_message = _first_present(route.get("user_message"), understanding.get("raw_text"), (route.get("planner_output") or {}).get("goal"), default="")
    return _layer(
        name="Reality",
        runtime_state={
            "user_message": user_message,
            "uploaded_documents": _as_list(route.get("uploaded_documents")),
            "uploaded_images": _as_list(route.get("uploaded_images")),
            "active_workspace": route.get("active_workspace") or "",
        },
        diagnostics={
            "reality_observed": bool(user_message),
            "diagnostic_only": True,
            "runtime_only": True,
        },
        confidence=1.0 if user_message else 0.0,
        source="runtime_input",
    )


def _perception_layer(business_situation: dict) -> dict:
    diagnostics = _as_dict(_as_dict(business_situation.get("diagnostics")).get("perception"))
    return _layer(
        name="Perception",
        runtime_state={
            "percept_id": diagnostics.get("percept_id"),
            "signal_set_id": diagnostics.get("signal_set_id"),
            "signal_count": diagnostics.get("canonical_signal_count"),
            "signal_types": diagnostics.get("canonical_signal_types") or [],
            "signal_sources": diagnostics.get("canonical_signal_sources") or [],
        },
        diagnostics=diagnostics,
        confidence=None,
        source=diagnostics.get("perception_situation_diagnostics_source") or "perception",
    )


def _business_situation_layer(business_situation: dict) -> dict:
    diagnostics = _as_dict(business_situation.get("diagnostics"))
    return _layer(
        name="Business Situation",
        runtime_state={
            "current_business": business_situation.get("current_business"),
            "current_goal": business_situation.get("current_goal"),
            "current_problem": business_situation.get("current_problem"),
            "current_operation": business_situation.get("current_operation"),
            "current_focus": business_situation.get("current_focus"),
            "conversation_purpose": business_situation.get("conversation_purpose"),
            "business_topic": business_situation.get("business_topic"),
        },
        diagnostics=diagnostics,
        confidence=business_situation.get("situation_confidence"),
        source=business_situation.get("situation_source") or diagnostics.get("business_situation_source"),
    )


def _evidence_layer(business_situation: dict) -> dict:
    evidence = _as_dict(_as_dict(business_situation.get("diagnostics")).get("evidence"))
    diagnostics = _as_dict(evidence.get("evidence_diagnostics"))
    return _layer(
        name="Evidence",
        runtime_state={
            "evidence_available": evidence.get("evidence_available"),
            "evidence_items": evidence.get("evidence_items") or [],
            "missing_evidence": evidence.get("missing_evidence") or [],
            "conflicting_evidence": evidence.get("conflicting_evidence") or [],
        },
        diagnostics=diagnostics,
        confidence=evidence.get("evidence_confidence"),
        source=evidence.get("evidence_source") or diagnostics.get("evidence_runtime_source"),
    )


def _truth_status_layer(business_situation: dict) -> dict:
    truth = _as_dict(_as_dict(business_situation.get("diagnostics")).get("truth"))
    diagnostics = _as_dict(truth.get("diagnostics"))
    return _layer(
        name="Truth Status",
        runtime_state={
            "truth_items": truth.get("truth_items") or [],
            "truth_summary": truth.get("truth_summary") or {},
            "runtime_truth": truth.get("runtime_truth") or [],
            "historical_truth": truth.get("historical_truth") or [],
            "conflicting_truths": truth.get("conflicting_truths") or [],
            "unknown_truths": truth.get("unknown_truths") or [],
        },
        diagnostics=diagnostics,
        confidence=None,
        source=truth.get("source") or diagnostics.get("truth_runtime_source"),
    )


def _evidence_gap_layer(business_situation: dict) -> dict:
    evidence_gap = _as_dict(_as_dict(business_situation.get("diagnostics")).get("evidence_gap"))
    diagnostics = _as_dict(evidence_gap.get("diagnostics"))
    gap_items = evidence_gap.get("gap_items") or []
    priority_queue = evidence_gap.get("priority_queue") or []
    next_question = evidence_gap.get("next_best_question") or {}
    duplicate_guard = evidence_gap.get("duplicate_question_guard") or {}
    completeness = evidence_gap.get("completeness_status") or {}
    return _layer(
        name="Evidence Gap",
        runtime_state={
            "gap_items": gap_items,
            "gap_type": [item.get("gap_type") for item in _as_list(gap_items) if isinstance(item, dict)],
            "missing_evidence": evidence_gap.get("missing_evidence") or [],
            "priority_queue": priority_queue,
            "question_intent": [item.get("question_intent") for item in _as_list(gap_items) if isinstance(item, dict)],
            "next_best_question": next_question,
            "duplicate_question_guard": duplicate_guard,
            "duplicate_guard_reason": duplicate_guard.get("duplicate_guard_reason") or diagnostics.get("duplicate_guard_reason"),
            "duplicate_guard_hits": duplicate_guard.get("duplicate_guard_hits") or diagnostics.get("duplicate_guard_hits") or {},
            "suppressed_questions": duplicate_guard.get("suppressed_questions") or diagnostics.get("suppressed_questions") or [],
            "completeness_status": completeness,
            "completeness_reason": completeness.get("completeness_reason") or diagnostics.get("completeness_reason"),
        },
        diagnostics=diagnostics,
        confidence=None,
        source=evidence_gap.get("source") or diagnostics.get("evidence_gap_runtime_source"),
    )


def _perspective_layer(business_situation: dict) -> dict:
    perspective = _as_dict(_as_dict(business_situation.get("diagnostics")).get("perspective"))
    diagnostics = _as_dict(perspective.get("diagnostics"))
    invariants = perspective.get("constitutional_invariants") or diagnostics.get("constitutional_invariants") or {}
    return _layer(
        name="Perspective",
        runtime_state={
            "selected_frame": perspective.get("selected_frame"),
            "candidate_frames": perspective.get("candidate_frames") or [],
            "frame_confidence": perspective.get("frame_confidence"),
            "frame_selection_reason": perspective.get("frame_selection_reason"),
            "frame_status": perspective.get("frame_status"),
            "source_layers": perspective.get("source_layers") or diagnostics.get("source_layers") or {},
            "constitutional_invariants": invariants,
        },
        diagnostics=diagnostics,
        confidence=perspective.get("frame_confidence"),
        source=perspective.get("source") or diagnostics.get("perspective_runtime_source"),
    )


def _placeholder_layer(name: str) -> dict:
    return _layer(
        name=name,
        runtime_state={},
        diagnostics={
            "placeholder": True,
            "diagnostic_only": True,
            "runtime_only": True,
            "not_implemented_in_version": BRAIN_OBSERVATORY_VERSION,
        },
        confidence=None,
        source="placeholder",
        status="placeholder",
    )


def _constitution_monitor(payload: dict) -> dict:
    flags = {}
    violations = []
    for flag in CONSTITUTION_FLAGS:
        values = _collect_flag_values(payload, flag)
        changed = any(values)
        flags[flag] = changed
        if changed:
            violations.append(flag)
    return {
        "flags": flags,
        "violations": violations,
        "violation_count": len(violations),
        "status": "violation" if violations else "clear",
        "highlight_violations": bool(violations),
    }


def _diagnostics_timeline(layers: list[dict]) -> list[dict]:
    timeline = []
    for index, layer in enumerate(layers, start=1):
        diagnostics = _as_dict(layer.get("diagnostics"))
        timeline.append(
            {
                "order": index,
                "layer": layer.get("layer"),
                "status": layer.get("status"),
                "source": layer.get("source"),
                "confidence": layer.get("confidence"),
                "diagnostics": diagnostics,
            }
        )
    return timeline


def build_brain_observatory(task_route: dict | None) -> dict:
    """Build a developer-only observability projection of cognitive runtime state.

    The observatory is a passive diagnostics surface. It does not route, plan,
    execute workflows, build responses, determine truth, produce judgment, or
    commit memory.
    """

    route = _as_dict(task_route)
    business_situation = _as_dict(
        route.get("business_situation")
        or _as_dict(route.get("planner_output")).get("business_situation")
    )
    layers = [
        _reality_layer(route),
        _perception_layer(business_situation),
        _business_situation_layer(business_situation),
        _evidence_layer(business_situation),
        _truth_status_layer(business_situation),
        _evidence_gap_layer(business_situation),
        _perspective_layer(business_situation),
        _placeholder_layer("Knowledge"),
        _placeholder_layer("Business Judgment"),
        _placeholder_layer("Decision"),
    ]
    constitution = _constitution_monitor({"route": route, "layers": layers})
    return {
        "observatory_created": True,
        "observatory_version": BRAIN_OBSERVATORY_VERSION,
        "observatory_source": BRAIN_OBSERVATORY_SOURCE,
        "runtime_mode": BRAIN_OBSERVATORY_RUNTIME_MODE,
        "developer_only": True,
        "diagnostic_only": True,
        "runtime_only": True,
        "layers": layers,
        "layer_order": list(COGNITIVE_LAYERS),
        "constitution_monitor": constitution,
        "diagnostics_timeline": _diagnostics_timeline(layers),
        "invariants": {
            "routing_changed": False,
            "planner_changed": False,
            "workflow_changed": False,
            "responses_changed": False,
            "execution_changed": False,
            "commit_changed": False,
            "used_for_routing": False,
            "used_for_planner": False,
            "used_for_workflow": False,
            "used_for_response": False,
            "used_for_execution": False,
            "used_for_commit": False,
        },
    }
