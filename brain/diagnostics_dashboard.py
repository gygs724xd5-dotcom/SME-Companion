from __future__ import annotations

from copy import deepcopy
from typing import Any


DASHBOARD_VERSION = "5.14.1"

RESPONSE_AUTHORITY = "Response Authority"
EVIDENCE_GAP = "Evidence Gap"
BUSINESS_SITUATION = "Business Situation"
CANONICAL_LAYERS = (RESPONSE_AUTHORITY, EVIDENCE_GAP, BUSINESS_SITUATION)

CONTRACT_MISSING = 0
CONTRACT_COMPLETE = 20
HELPER_COMPLETE = 40
SHADOW_WIRED = 60
ACCEPTANCE_GUARDED = 80
RUNTIME_AUDITED = 100

_COMPLETE_VALUES = {"complete", "completed", "pass", "passed", "ok", "true", "yes", "done"}

_RESPONSE_AUTHORITY_KEYS = (
    "response_authority_decision",
    "response_authority_mode",
    "response_authority_reason",
    "response_authority_workflow_allowed",
    "response_authority_shadow_mode",
)
_EVIDENCE_GAP_KEYS = (
    "evidence_gap_profile",
    "evidence_gap_detected",
    "evidence_gap_type",
    "evidence_missing_fields",
    "evidence_conflicting_fields",
    "evidence_smallest_next_question",
    "evidence_sufficient",
    "evidence_can_answer_with_assumptions",
    "evidence_gap_reason",
    "evidence_gap_confidence",
    "evidence_gap_shadow_mode",
)
_BUSINESS_SITUATION_KEYS = (
    "business_situation_profile",
    "business_situation_detected",
    "business_situation_type",
    "business_domain",
    "perspective_stance",
    "business_risk_level",
    "business_opportunity_level",
    "business_urgency_level",
    "owner_attention",
    "recommended_response_posture",
    "business_reasoning_summary",
    "business_situation_confidence",
    "business_situation_shadow_mode",
)


def _as_dict(value: Any) -> dict:
    return deepcopy(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    return deepcopy(value) if isinstance(value, list) else []


def _status_complete(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in _COMPLETE_VALUES


def _status_text(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, bool):
        return "complete" if value else "missing"
    return "missing"


def _risk_for_score(score: int, active_gate: str) -> str:
    if active_gate not in {"shadow_only", "inactive"} and score < RUNTIME_AUDITED:
        return "high"
    if score >= RUNTIME_AUDITED:
        return "low"
    if score >= SHADOW_WIRED:
        return "medium"
    return "high"


def _layer_status_by_name(layer_statuses: Any) -> dict:
    if not isinstance(layer_statuses, list):
        return {}
    result = {}
    for item in layer_statuses:
        if not isinstance(item, dict):
            continue
        name = item.get("layer_name") or item.get("name") or item.get("layer")
        if name in CANONICAL_LAYERS:
            result[name] = item
    return result


def _active_gate_for_layer(active_gate_status: dict, layer_name: str, layer_status: dict) -> str:
    explicit = layer_status.get("active_gate_status")
    if explicit not in (None, ""):
        return str(explicit)

    layer_gate = active_gate_status.get(layer_name)
    if isinstance(layer_gate, dict):
        if layer_gate.get("enabled") or layer_gate.get("active") or layer_gate.get("active_gate_enabled"):
            return "active"
        status = layer_gate.get("status")
        if status:
            return str(status)
    if layer_gate is True:
        return "active"

    return str(active_gate_status.get("default_status") or "shadow_only")


def _readiness_score(layer_status: dict) -> int:
    if isinstance(layer_status.get("readiness_score"), int):
        return max(CONTRACT_MISSING, min(RUNTIME_AUDITED, layer_status["readiness_score"]))

    score = CONTRACT_MISSING
    if _status_complete(layer_status.get("contract_status")):
        score = CONTRACT_COMPLETE
    if _status_complete(layer_status.get("helper_status")):
        score = HELPER_COMPLETE
    if _status_complete(layer_status.get("shadow_wiring_status")):
        score = SHADOW_WIRED
    if _status_complete(layer_status.get("acceptance_status")):
        score = ACCEPTANCE_GUARDED
    if _status_complete(layer_status.get("audit_status")):
        score = RUNTIME_AUDITED
    return score


def _layer_progress(layer_statuses: Any, active_gate_status: dict) -> list[dict]:
    statuses = _layer_status_by_name(layer_statuses)
    progress = []
    for layer_name in CANONICAL_LAYERS:
        status = _as_dict(statuses.get(layer_name))
        active_gate = _active_gate_for_layer(active_gate_status, layer_name, status)
        score = _readiness_score(status)
        progress.append(
            {
                "layer_name": layer_name,
                "readiness_score": score,
                "contract_status": _status_text(status.get("contract_status")),
                "helper_status": _status_text(status.get("helper_status")),
                "shadow_wiring_status": _status_text(status.get("shadow_wiring_status")),
                "acceptance_status": _status_text(status.get("acceptance_status")),
                "audit_status": _status_text(status.get("audit_status")),
                "active_gate_status": active_gate,
                "risk_level": str(status.get("risk_level") or _risk_for_score(score, active_gate)),
                "notes": _as_list(status.get("notes")),
            }
        )
    return progress


def _stable_subset(source: Any, keys: tuple[str, ...]) -> dict:
    if not isinstance(source, dict):
        return {}
    return {key: deepcopy(source[key]) for key in keys if key in source}


def _shadow_diagnostics(
    response_authority_diagnostics: Any,
    evidence_gap_diagnostics: Any,
    business_situation_diagnostics: Any,
) -> dict:
    return {
        "response_authority": _stable_subset(response_authority_diagnostics, _RESPONSE_AUTHORITY_KEYS),
        "evidence_gap": _stable_subset(evidence_gap_diagnostics, _EVIDENCE_GAP_KEYS),
        "business_situation": _stable_subset(business_situation_diagnostics, _BUSINESS_SITUATION_KEYS),
    }


def _has_active_gate_violation(active_gate_status: dict, layer_progress: list[dict]) -> bool:
    if not active_gate_status:
        return False
    if active_gate_status.get("active_gate_violation"):
        return True
    global_enabled = any(
        bool(active_gate_status.get(key))
        for key in ("enabled", "active", "active_gate_enabled", "runtime_gate_enabled")
    )
    layer_enabled = any(
        isinstance(value, dict)
        and any(bool(value.get(key)) for key in ("enabled", "active", "active_gate_enabled"))
        for value in active_gate_status.values()
    )
    if not (global_enabled or layer_enabled):
        return False
    return any(row["active_gate_status"] == "shadow_only" or row["readiness_score"] < RUNTIME_AUDITED for row in layer_progress)


def _truthy_trace(trace: dict, *keys: str) -> bool:
    return any(bool(trace.get(key)) for key in keys)


def _mismatch_flags(
    *,
    shadow_diagnostics: dict,
    current_turn_trace: dict,
    active_gate_status: dict,
    layer_progress: list[dict],
) -> list[str]:
    flags = []
    ra = shadow_diagnostics["response_authority"]
    evidence = shadow_diagnostics["evidence_gap"]
    business = shadow_diagnostics["business_situation"]
    diagnostics_missing = not any((ra, evidence, business))

    if diagnostics_missing:
        flags.append("diagnostics_missing")

    reasons = {
        ra.get("response_authority_reason"),
        evidence.get("evidence_gap_reason"),
        business.get("business_reasoning_summary"),
    }
    if any(str(reason or "").endswith("_shadow_error") for reason in reasons) or _truthy_trace(
        current_turn_trace,
        "shadow_layer_error",
    ):
        flags.append("shadow_layer_error")

    if _has_active_gate_violation(active_gate_status, layer_progress):
        flags.append("active_gate_violation")

    if evidence.get("evidence_sufficient") is True and _truthy_trace(
        current_turn_trace,
        "clarification_asked",
        "asked_clarification",
    ):
        flags.append("evidence_sufficient_but_clarification_asked")

    final_route = str(current_turn_trace.get("final_response_route") or "").strip().lower()
    response_mode = str(current_turn_trace.get("response_mode") or "").strip()
    if evidence.get("evidence_sufficient") is True and (
        final_route == "clarification" or response_mode == "CLARIFICATION_QUESTION"
    ):
        flags.append("evidence_sufficient_but_clarification_asked")

    authority_mode = ra.get("response_authority_mode") or ra.get("response_authority_decision")
    if authority_mode in {"DIRECT_SEMANTIC_ANSWER", "DIRECT_BUSINESS_ANALYSIS"} and (
        final_route == "workflow" or _truthy_trace(current_turn_trace, "workflow_started", "workflow_continued")
    ):
        flags.append("authority_direct_but_workflow_started")

    reset_status = str(current_turn_trace.get("reset_boundary_status") or "").strip().lower()
    if reset_status == "violated" or (
        _truthy_trace(current_turn_trace, "reset_boundary_active")
        and _truthy_trace(current_turn_trace, "stale_context_reused", "completed_workflow_context_reused")
    ):
        flags.append("stale_context_reused_after_reset")

    workflow_state = _as_dict(current_turn_trace.get("workflow_state_summary"))
    workflow_status = str(workflow_state.get("workflow_status") or workflow_state.get("status") or "").strip().lower()
    if _truthy_trace(current_turn_trace, "completed_workflow_forced_continuation") or (
        workflow_status == "completed" and (final_route == "workflow" or _truthy_trace(current_turn_trace, "workflow_continued"))
    ):
        flags.append("completed_workflow_forced_continuation")

    if business.get("business_situation_detected") is True and (
        final_route == "generic" or _truthy_trace(current_turn_trace, "generic_response")
    ):
        flags.append("business_situation_detected_but_generic_response")

    return list(dict.fromkeys(flags))


def _active_shadow_map(layer_progress: list[dict]) -> dict:
    return {
        row["layer_name"]: {
            "mode": "active" if row["active_gate_status"] not in {"shadow_only", "inactive"} else "shadow",
            "active_gate_status": row["active_gate_status"],
            "readiness_score": row["readiness_score"],
        }
        for row in layer_progress
    }


def _next_recommended_step(layer_progress: list[dict], protected_dirty_files: list, active_gate_status: dict) -> dict:
    for row in layer_progress:
        if row["readiness_score"] < RUNTIME_AUDITED:
            message = f"Complete {row['layer_name']} runtime audit before dashboard wiring."
            break
    else:
        message = "Proceed to V5.14.2 shadow diagnostics snapshot wiring."

    if (
        active_gate_status.get("recommend_active_gating")
        and all(row["readiness_score"] == RUNTIME_AUDITED for row in layer_progress)
        and not protected_dirty_files
    ):
        message = "Review explicit active-gate candidate scope; do not enable gating from this snapshot helper."

    notes = []
    if protected_dirty_files:
        notes.append("Protected dirty files are present; keep them untouched, but do not block the architecture recommendation.")
    return {"recommendation": message, "notes": notes}


def build_brain_diagnostics_snapshot(
    *,
    layer_statuses: list[dict] | None = None,
    response_authority_diagnostics: dict | None = None,
    evidence_gap_diagnostics: dict | None = None,
    business_situation_diagnostics: dict | None = None,
    test_health: dict | None = None,
    protected_dirty_files: list[str] | None = None,
    current_turn_trace: dict | None = None,
    active_gate_status: dict | None = None,
) -> dict:
    """Build a read-only V5.14.1 Brain Diagnostics Dashboard snapshot.

    The helper is pure and diagnostic-only. It does not render UI, call an LLM,
    mutate runtime state, activate gates, or influence final response behavior.
    """
    active_gate = _as_dict(active_gate_status)
    trace = _as_dict(current_turn_trace)
    protected_files = _as_list(protected_dirty_files)
    layer_rows = _layer_progress(layer_statuses, active_gate)
    shadow = _shadow_diagnostics(
        response_authority_diagnostics,
        evidence_gap_diagnostics,
        business_situation_diagnostics,
    )
    flags = _mismatch_flags(
        shadow_diagnostics=shadow,
        current_turn_trace=trace,
        active_gate_status=active_gate,
        layer_progress=layer_rows,
    )
    test_health_snapshot = _as_dict(test_health)
    test_health_snapshot.setdefault("protected_dirty_files", deepcopy(protected_files))

    return {
        "dashboard_version": DASHBOARD_VERSION,
        "layer_progress": layer_rows,
        "shadow_diagnostics": shadow,
        "current_turn_trace": trace,
        "regression_safety_status": _as_dict(test_health_snapshot.get("regression_safety_status")),
        "test_health": test_health_snapshot,
        "protected_dirty_files": protected_files,
        "active_vs_shadow_layer_map": _active_shadow_map(layer_rows),
        "mismatch_flags": flags,
        "next_recommended_step": _next_recommended_step(layer_rows, protected_files, active_gate),
        "diagnostics": {
            "snapshot_helper": "brain.diagnostics_dashboard.build_brain_diagnostics_snapshot",
            "snapshot_helper_complete": True,
            "runtime_mutation": False,
            "ui_rendered": False,
            "llm_called": False,
            "active_gate_changed": False,
            "response_behavior_changed": False,
            "shadow_mode_only_layers": list(CANONICAL_LAYERS),
        },
    }
