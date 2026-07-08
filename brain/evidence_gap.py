from __future__ import annotations

from typing import Any


NO_GAP = "NO_GAP"
MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
MISSING_BUSINESS_CONTEXT = "MISSING_BUSINESS_CONTEXT"
AMBIGUOUS_INTENT = "AMBIGUOUS_INTENT"
CONTRADICTORY_EVIDENCE = "CONTRADICTORY_EVIDENCE"
STALE_CONTEXT = "STALE_CONTEXT"
WORKFLOW_REQUIREMENT_GAP = "WORKFLOW_REQUIREMENT_GAP"
CALCULATION_INPUT_GAP = "CALCULATION_INPUT_GAP"
MEMORY_LOOKUP_GAP = "MEMORY_LOOKUP_GAP"
USER_CONFIRMATION_GAP = "USER_CONFIRMATION_GAP"


_CALCULATION_FIELD_MARKERS = {
    "amount",
    "average",
    "cost",
    "count",
    "discount",
    "margin",
    "percent",
    "percentage",
    "price",
    "profit",
    "quantity",
    "rate",
    "revenue",
    "sales",
    "tax",
    "total",
    "unit",
    "units",
}


def _normalized_text(value: Any) -> str:
    return str(value or "").strip()


def _as_field_list(value: Any) -> list[str]:
    if value in (None, "", [], {}, ()):
        return []
    if isinstance(value, (list, tuple, set)):
        return [_normalized_text(item) for item in value if _normalized_text(item)]
    return [_normalized_text(value)]


def _as_dict(value: Any) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def _clamp_confidence(value: Any) -> float:
    if value is None:
        return 1.0
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _value_present(value: Any) -> bool:
    return value not in (None, "", [], {})


def _dict_contains_field(source: dict, field: str) -> bool:
    if not isinstance(source, dict) or not field:
        return False
    if field in source and _value_present(source.get(field)):
        return True
    for value in source.values():
        if isinstance(value, dict) and _dict_contains_field(value, field):
            return True
    return False


def _field_present(field: str, *sources: dict) -> bool:
    return any(_dict_contains_field(source, field) for source in sources)


def _missing_fields(fields: list[str], *sources: dict) -> list[str]:
    return [field for field in fields if not _field_present(field, *sources)]


def _is_calculation_field(field: str) -> bool:
    normalized = field.lower().replace("-", "_").replace(" ", "_")
    parts = {part for part in normalized.split("_") if part}
    return bool(parts & _CALCULATION_FIELD_MARKERS)


def _question_for(field: str, gap_type: str) -> str | None:
    if not field:
        return None
    if gap_type == AMBIGUOUS_INTENT:
        return "What do you want to do?"
    label = field.replace("_", " ").strip()
    return f"What is the {label}?"


def _diagnostics(
    *,
    user_message: str,
    required_fields: list[str],
    provided_fields: dict,
    known_context: dict,
    completed_workflow_context: dict,
    active_workflow_requirements: list[str],
    reset_boundary_active: bool,
    malformed_inputs: list[str],
    stale_completed_fields_blocked: list[str],
    gap_type: str,
    missing_fields: list[str],
    conflicting_fields: list[str],
    smallest_next_question: str | None,
    evidence_sufficient: bool,
    can_answer_with_assumptions: bool,
    reason: str,
    confidence: float,
) -> dict:
    return {
        "evidence_gap_profile_version": "5.12.1",
        "user_message_present": bool(user_message),
        "required_field_count": len(required_fields),
        "provided_field_count": len(provided_fields),
        "known_context_field_count": len(known_context),
        "completed_workflow_context_present": bool(completed_workflow_context),
        "active_workflow_requirement_count": len(active_workflow_requirements),
        "reset_boundary_active": bool(reset_boundary_active),
        "completed_workflow_context_counted": bool(completed_workflow_context and not reset_boundary_active),
        "stale_completed_fields_blocked": list(stale_completed_fields_blocked),
        "malformed_inputs": list(malformed_inputs),
        "evidence_gap_detected": gap_type != NO_GAP,
        "evidence_gap_type": gap_type,
        "evidence_missing_fields": list(missing_fields),
        "evidence_conflicting_fields": list(conflicting_fields),
        "evidence_smallest_next_question": smallest_next_question,
        "evidence_sufficient": bool(evidence_sufficient),
        "evidence_can_answer_with_assumptions": bool(can_answer_with_assumptions),
        "evidence_gap_reason": reason,
        "evidence_gap_confidence": confidence,
    }


def _profile(
    *,
    user_message: str,
    required_fields: list[str],
    provided_fields: dict,
    known_context: dict,
    completed_workflow_context: dict,
    active_workflow_requirements: list[str],
    reset_boundary_active: bool,
    malformed_inputs: list[str],
    stale_completed_fields_blocked: list[str],
    evidence_sufficient: bool,
    gap_type: str,
    missing_fields: list[str] | None = None,
    conflicting_fields: list[str] | None = None,
    smallest_next_question: str | None = None,
    can_answer_with_assumptions: bool = False,
    assumption_notes: list[str] | None = None,
    confidence: float = 1.0,
    reason: str = "",
) -> dict:
    missing = list(missing_fields or [])
    conflicts = list(conflicting_fields or [])
    notes = list(assumption_notes or [])
    diagnostics = _diagnostics(
        user_message=user_message,
        required_fields=required_fields,
        provided_fields=provided_fields,
        known_context=known_context,
        completed_workflow_context=completed_workflow_context,
        active_workflow_requirements=active_workflow_requirements,
        reset_boundary_active=reset_boundary_active,
        malformed_inputs=malformed_inputs,
        stale_completed_fields_blocked=stale_completed_fields_blocked,
        gap_type=gap_type,
        missing_fields=missing,
        conflicting_fields=conflicts,
        smallest_next_question=smallest_next_question,
        evidence_sufficient=evidence_sufficient,
        can_answer_with_assumptions=can_answer_with_assumptions,
        reason=reason,
        confidence=confidence,
    )
    return {
        "evidence_sufficient": bool(evidence_sufficient),
        "gap_detected": gap_type != NO_GAP,
        "gap_type": gap_type,
        "missing_fields": missing,
        "conflicting_fields": conflicts,
        "smallest_next_question": smallest_next_question,
        "can_answer_with_assumptions": bool(can_answer_with_assumptions),
        "assumption_notes": notes,
        "confidence": confidence,
        "reason": reason,
        "diagnostics": diagnostics,
    }


def evaluate_evidence_gap(
    user_message: str,
    *,
    required_fields: list[str] | None = None,
    provided_fields: dict | None = None,
    known_context: dict | None = None,
    conflicting_fields: list[str] | None = None,
    active_workflow_requirements: list[str] | None = None,
    reset_boundary_active: bool = False,
    completed_workflow_context: dict | None = None,
    intent_ambiguous: bool = False,
    can_answer_with_assumptions: bool = False,
    assumption_notes: list[str] | None = None,
    confidence: float | None = None,
) -> dict:
    """Evaluate whether one turn has enough evidence to answer.

    This helper is pure and diagnostic-only. It does not mutate inputs, call
    external services, choose response mode, or generate final answer text.
    """
    message = _normalized_text(user_message)
    malformed_inputs: list[str] = []

    if required_fields is not None and not isinstance(required_fields, (list, tuple, set)):
        malformed_inputs.append("required_fields")
    if provided_fields is not None and not isinstance(provided_fields, dict):
        malformed_inputs.append("provided_fields")
    if known_context is not None and not isinstance(known_context, dict):
        malformed_inputs.append("known_context")
    if conflicting_fields is not None and not isinstance(conflicting_fields, (list, tuple, set)):
        malformed_inputs.append("conflicting_fields")
    if active_workflow_requirements is not None and not isinstance(active_workflow_requirements, (list, tuple, set)):
        malformed_inputs.append("active_workflow_requirements")
    if completed_workflow_context is not None and not isinstance(completed_workflow_context, dict):
        malformed_inputs.append("completed_workflow_context")
    if assumption_notes is not None and not isinstance(assumption_notes, (list, tuple, set)):
        malformed_inputs.append("assumption_notes")

    required = _as_field_list(required_fields)
    provided = _as_dict(provided_fields)
    known = _as_dict(known_context)
    conflicts = _as_field_list(conflicting_fields)
    workflow_requirements = _as_field_list(active_workflow_requirements)
    completed = _as_dict(completed_workflow_context)
    notes = _as_field_list(assumption_notes)
    clamped_confidence = _clamp_confidence(confidence)

    active_sources = [provided, known]
    if not reset_boundary_active:
        active_sources.append(completed)

    stale_completed_fields_blocked = []
    if reset_boundary_active and completed:
        stale_completed_fields_blocked = [
            field
            for field in required + workflow_requirements
            if _field_present(field, completed) and not _field_present(field, provided, known)
        ]

    base = {
        "user_message": message,
        "required_fields": required,
        "provided_fields": provided,
        "known_context": known,
        "completed_workflow_context": completed,
        "active_workflow_requirements": workflow_requirements,
        "reset_boundary_active": bool(reset_boundary_active),
        "malformed_inputs": malformed_inputs,
        "stale_completed_fields_blocked": stale_completed_fields_blocked,
        "confidence": clamped_confidence,
    }

    if conflicts:
        return _profile(
            **base,
            evidence_sufficient=False,
            gap_type=CONTRADICTORY_EVIDENCE,
            conflicting_fields=conflicts,
            reason="contradictory_evidence",
        )

    if intent_ambiguous:
        return _profile(
            **base,
            evidence_sufficient=False,
            gap_type=AMBIGUOUS_INTENT,
            smallest_next_question=_question_for("next step", AMBIGUOUS_INTENT),
            reason="ambiguous_intent",
        )

    missing_workflow = _missing_fields(workflow_requirements, *active_sources)
    if missing_workflow:
        first_missing = missing_workflow[0]
        return _profile(
            **base,
            evidence_sufficient=False,
            gap_type=WORKFLOW_REQUIREMENT_GAP,
            missing_fields=missing_workflow,
            smallest_next_question=_question_for(first_missing, WORKFLOW_REQUIREMENT_GAP),
            reason="missing_active_workflow_requirement",
        )

    missing_required = _missing_fields(required, *active_sources)
    if missing_required:
        first_missing = missing_required[0]
        gap_type = CALCULATION_INPUT_GAP if _is_calculation_field(first_missing) else MISSING_REQUIRED_FIELD
        assumption_allowed = bool(can_answer_with_assumptions and gap_type == MISSING_REQUIRED_FIELD)
        return _profile(
            **base,
            evidence_sufficient=assumption_allowed,
            gap_type=gap_type,
            missing_fields=missing_required,
            smallest_next_question=None if assumption_allowed else _question_for(first_missing, gap_type),
            can_answer_with_assumptions=assumption_allowed,
            assumption_notes=notes if assumption_allowed else [],
            reason="answerable_with_assumptions" if assumption_allowed else "missing_required_field",
        )

    reason = "current_turn_contains_required_evidence" if message else "empty_message_no_required_evidence"
    return _profile(
        **base,
        evidence_sufficient=True,
        gap_type=NO_GAP,
        can_answer_with_assumptions=False,
        assumption_notes=[],
        reason=reason,
    )
