from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


WORKFLOW_ADMISSION_GATE_VERSION = "5.8.3"


class WorkflowAdmissionDecision(str, Enum):
    ADMIT = "ADMIT"
    DEFER_FOR_CLARIFICATION = "DEFER_FOR_CLARIFICATION"
    REJECT_TO_CONVERSATION = "REJECT_TO_CONVERSATION"


class WorkflowAdmissionReason(str, Enum):
    EXPLICIT_EXECUTABLE_REQUEST = "EXPLICIT_EXECUTABLE_REQUEST"
    SUFFICIENT_REQUIRED_ENTITIES = "SUFFICIENT_REQUIRED_ENTITIES"
    CLEAR_WORKFLOW_COMMAND = "CLEAR_WORKFLOW_COMMAND"
    AMBIGUOUS_BUSINESS_ASSESSMENT = "AMBIGUOUS_BUSINESS_ASSESSMENT"
    ANALYTICAL_QUESTION_NOT_EXECUTABLE = "ANALYTICAL_QUESTION_NOT_EXECUTABLE"
    LOW_UNDERSTANDING_CONFIDENCE = "LOW_UNDERSTANDING_CONFIDENCE"
    INSUFFICIENT_WORKFLOW_SPECIFICITY = "INSUFFICIENT_WORKFLOW_SPECIFICITY"
    WORKFLOW_KEYWORD_ONLY_MATCH = "WORKFLOW_KEYWORD_ONLY_MATCH"
    NO_WORKFLOW_CANDIDATE = "NO_WORKFLOW_CANDIDATE"
    LEGACY_COMPATIBILITY_ALLOW = "LEGACY_COMPATIBILITY_ALLOW"


REQUIRED_ENTITIES_BY_WORKFLOW = {
    "PROFIT_CALCULATION": ("price", "cost"),
    "COST_CALCULATION": ("cost", "quantity"),
    "SALES_PLAN_7_DAY": ("product", "daily_capacity_or_available_quantity", "selling_window_or_sales_channel"),
    "CONTENT_PLAN": ("product_or_business_type",),
    "DASHBOARD_REQUEST": (),
    "RECEIPT_CAPTURE": (),
    "GENERAL_BUSINESS_HELP": (),
}

EXECUTABLE_SIGNALS = (
    "\u0e04\u0e33\u0e19\u0e27\u0e13",
    "\u0e0a\u0e48\u0e27\u0e22\u0e04\u0e33\u0e19\u0e27\u0e13",
    "\u0e04\u0e34\u0e14\u0e01\u0e33\u0e44\u0e23",
    "\u0e04\u0e34\u0e14\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19",
    "\u0e2a\u0e23\u0e49\u0e32\u0e07",
    "\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01",
    "\u0e40\u0e1e\u0e34\u0e48\u0e21",
    "\u0e25\u0e1a",
    "\u0e2d\u0e31\u0e1b\u0e40\u0e14\u0e15",
    "\u0e2d\u0e2d\u0e01\u0e43\u0e1a",
    "\u0e17\u0e33\u0e23\u0e32\u0e22\u0e01\u0e32\u0e23",
    "calculate",
)

ANALYTICAL_SIGNALS = (
    "\u0e14\u0e35\u0e44\u0e2b\u0e21",
    "\u0e40\u0e1b\u0e47\u0e19\u0e22\u0e31\u0e07\u0e44\u0e07",
    "\u0e17\u0e33\u0e44\u0e21",
    "\u0e27\u0e34\u0e40\u0e04\u0e23\u0e32\u0e30\u0e2b\u0e4c",
    "\u0e1b\u0e23\u0e30\u0e40\u0e21\u0e34\u0e19",
    "\u0e42\u0e2d\u0e40\u0e04\u0e44\u0e2b\u0e21",
    "\u0e1b\u0e01\u0e15\u0e34\u0e44\u0e2b\u0e21",
    "\u0e40\u0e01\u0e34\u0e14\u0e2d\u0e30\u0e44\u0e23\u0e02\u0e36\u0e49\u0e19",
    "\u0e04\u0e27\u0e23\u0e14\u0e39\u0e2d\u0e30\u0e44\u0e23",
    "why",
    "analyze",
    "assess",
)

BUSINESS_LEVEL_SIGNALS = (
    "\u0e23\u0e49\u0e32\u0e19\u0e02\u0e2d\u0e07\u0e09\u0e31\u0e19",
    "\u0e18\u0e38\u0e23\u0e01\u0e34\u0e08\u0e09\u0e31\u0e19",
    "\u0e18\u0e38\u0e23\u0e01\u0e34\u0e08\u0e02\u0e2d\u0e07\u0e09\u0e31\u0e19",
    "\u0e0a\u0e48\u0e27\u0e07\u0e19\u0e35\u0e49\u0e23\u0e49\u0e32\u0e19",
    "\u0e20\u0e32\u0e1e\u0e23\u0e27\u0e21",
    "my shop",
    "my business",
    "overall",
)

WORKFLOW_KEYWORDS = (
    "\u0e01\u0e33\u0e44\u0e23",
    "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19",
    "\u0e23\u0e32\u0e04\u0e32",
    "\u0e2a\u0e15\u0e4a\u0e2d\u0e01",
    "\u0e22\u0e2d\u0e14\u0e02\u0e32\u0e22",
    "\u0e02\u0e32\u0e22",
    "profit",
    "cost",
    "price",
    "stock",
    "sales",
)

LEGACY_AUTO_ADMIT_WORKFLOWS = {"DASHBOARD_REQUEST", "RECEIPT_CAPTURE", "GENERAL_BUSINESS_HELP"}


@dataclass(frozen=True)
class WorkflowAdmissionResult:
    workflow_candidate: str | None
    decision: str
    reason: str
    admitted: bool
    admission_confidence: float
    executable_request_detected: bool
    analytical_question_detected: bool
    business_level_scope_detected: bool
    keyword_only_match_detected: bool
    understanding_confidence: Any = None
    resolver_confidence: Any = None
    required_entities: list[str] = field(default_factory=list)
    completed_entities: list[str] = field(default_factory=list)
    missing_entities: list[str] = field(default_factory=list)
    workflow_executable: bool = False
    fallback_target: str | None = None
    diagnostic_summary: str = ""
    version: str = WORKFLOW_ADMISSION_GATE_VERSION
    diagnostic_only: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def build_workflow_admission_decision(
    *,
    raw_user_message: str | None = None,
    conversation_understanding: dict | None = None,
    intent_resolution: dict | None = None,
    planner_output: dict | None = None,
    workflow_candidate: str | None = None,
    workflow_required_entities: list[str] | tuple[str, ...] | None = None,
    extracted_entities: dict | None = None,
    missing_entities: list[str] | tuple[str, ...] | None = None,
    workflow_executable: bool | None = None,
    **_: Any,
) -> dict:
    """Decide whether a candidate workflow is admitted to runtime ownership.

    The gate is intentionally deterministic and read-only. It separates planner
    candidacy from workflow admission without mutating planner, entity, or
    cognitive runtime inputs.
    """

    message = str(raw_user_message or "").strip()
    normalized = message.lower()
    understanding = deepcopy(conversation_understanding or {})
    resolver = deepcopy(intent_resolution or {})
    planner = deepcopy(planner_output or {})
    candidate = workflow_candidate or planner.get("workflow") or resolver.get("resolved_workflow")
    required = list(workflow_required_entities or REQUIRED_ENTITIES_BY_WORKFLOW.get(candidate, ()))
    entities = deepcopy(extracted_entities or {})
    completed = [field for field in required if _has_entity(field, entities)]
    missing = list(missing_entities) if missing_entities is not None else [field for field in required if field not in completed]
    executable = bool(workflow_executable) if workflow_executable is not None else bool(required and not missing)

    relationship_analysis = _looks_like_relationship_analysis(normalized)
    executable_signal = _contains_any(normalized, EXECUTABLE_SIGNALS) and not relationship_analysis
    analytical_signal = _contains_any(normalized, ANALYTICAL_SIGNALS) or relationship_analysis
    business_scope = _contains_any(normalized, BUSINESS_LEVEL_SIGNALS)
    keyword_match = _contains_any(normalized, WORKFLOW_KEYWORDS)
    keyword_only = bool(keyword_match and not executable_signal and not executable and (analytical_signal or _looks_like_question(normalized)))
    low_understanding = _is_low_confidence(understanding.get("confidence_score"), understanding.get("confidence"))
    high_resolver = _is_high_confidence(resolver.get("confidence_score"), resolver.get("confidence"))

    if not candidate:
        return _result(
            candidate,
            WorkflowAdmissionDecision.REJECT_TO_CONVERSATION,
            WorkflowAdmissionReason.NO_WORKFLOW_CANDIDATE,
            0.99,
            executable_signal,
            analytical_signal,
            business_scope,
            keyword_only,
            understanding,
            resolver,
            required,
            completed,
            missing,
            False,
            "conversation",
        )

    if candidate in LEGACY_AUTO_ADMIT_WORKFLOWS:
        return _result(
            candidate,
            WorkflowAdmissionDecision.ADMIT,
            WorkflowAdmissionReason.LEGACY_COMPATIBILITY_ALLOW,
            0.82,
            executable_signal,
            analytical_signal,
            business_scope,
            False,
            understanding,
            resolver,
            required,
            completed,
            missing,
            executable,
            None,
        )

    if business_scope and analytical_signal:
        return _result(
            candidate,
            WorkflowAdmissionDecision.REJECT_TO_CONVERSATION,
            WorkflowAdmissionReason.AMBIGUOUS_BUSINESS_ASSESSMENT,
            0.93,
            executable_signal,
            analytical_signal,
            business_scope,
            keyword_only,
            understanding,
            resolver,
            required,
            completed,
            missing,
            executable,
            "conversation",
        )

    if analytical_signal and not executable_signal:
        return _result(
            candidate,
            WorkflowAdmissionDecision.REJECT_TO_CONVERSATION,
            WorkflowAdmissionReason.ANALYTICAL_QUESTION_NOT_EXECUTABLE,
            0.9,
            executable_signal,
            analytical_signal,
            business_scope,
            keyword_only,
            understanding,
            resolver,
            required,
            completed,
            missing,
            executable,
            "conversation",
        )

    if executable_signal:
        return _result(
            candidate,
            WorkflowAdmissionDecision.ADMIT,
            WorkflowAdmissionReason.EXPLICIT_EXECUTABLE_REQUEST,
            0.92,
            executable_signal,
            analytical_signal,
            business_scope,
            False,
            understanding,
            resolver,
            required,
            completed,
            missing,
            executable,
            None,
        )

    if executable:
        return _result(
            candidate,
            WorkflowAdmissionDecision.ADMIT,
            WorkflowAdmissionReason.SUFFICIENT_REQUIRED_ENTITIES,
            0.9,
            executable_signal,
            analytical_signal,
            business_scope,
            False,
            understanding,
            resolver,
            required,
            completed,
            missing,
            executable,
            None,
        )

    if completed and keyword_match and not analytical_signal and not business_scope:
        return _result(
            candidate,
            WorkflowAdmissionDecision.ADMIT,
            WorkflowAdmissionReason.CLEAR_WORKFLOW_COMMAND,
            0.86,
            executable_signal,
            analytical_signal,
            business_scope,
            False,
            understanding,
            resolver,
            required,
            completed,
            missing,
            executable,
            None,
        )

    if keyword_only:
        reason = WorkflowAdmissionReason.LOW_UNDERSTANDING_CONFIDENCE if low_understanding and high_resolver else WorkflowAdmissionReason.WORKFLOW_KEYWORD_ONLY_MATCH
        return _result(
            candidate,
            WorkflowAdmissionDecision.DEFER_FOR_CLARIFICATION,
            reason,
            0.86,
            executable_signal,
            analytical_signal,
            business_scope,
            True,
            understanding,
            resolver,
            required,
            completed,
            missing,
            executable,
            "clarification",
        )

    if low_understanding and high_resolver and keyword_match:
        return _result(
            candidate,
            WorkflowAdmissionDecision.DEFER_FOR_CLARIFICATION,
            WorkflowAdmissionReason.LOW_UNDERSTANDING_CONFIDENCE,
            0.84,
            executable_signal,
            analytical_signal,
            business_scope,
            True,
            understanding,
            resolver,
            required,
            completed,
            missing,
            executable,
            "clarification",
        )

    return _result(
        candidate,
        WorkflowAdmissionDecision.DEFER_FOR_CLARIFICATION,
        WorkflowAdmissionReason.INSUFFICIENT_WORKFLOW_SPECIFICITY,
        0.74,
        executable_signal,
        analytical_signal,
        business_scope,
        keyword_match and not executable_signal,
        understanding,
        resolver,
        required,
        completed,
        missing,
        executable,
        "clarification",
    )


def blocked_workflow_payload(admission: dict, *, detected_intent: str | None = None) -> dict:
    decision = admission.get("decision")
    reason = admission.get("reason")
    return {
        "workflow_action": "interrupt",
        "workflow_state": None,
        "workflow_candidate": admission.get("workflow_candidate"),
        "workflow_status": None,
        "workflow_confidence": admission.get("admission_confidence"),
        "workflow_reason": f"workflow admission gate {str(decision).lower()}: {reason}",
        "workflow_interrupted": False,
        "workflow_resume_available": False,
        "workflow_released": False,
        "workflow_complete": False,
        "workflow_stage": "admission_blocked",
        "workflow_progress": {"completed": len(admission.get("completed_entities") or []), "required": len(admission.get("required_entities") or []), "percent": 0.0},
        "required_entities": list(admission.get("required_entities") or []),
        "completed_entities": list(admission.get("completed_entities") or []),
        "missing_entities": list(admission.get("missing_entities") or []),
        "entity_completeness": {"completed": len(admission.get("completed_entities") or []), "required": len(admission.get("required_entities") or []), "percent": 0.0},
        "next_question": None,
        "detected_intent": detected_intent,
        "readiness_decision": {
            "workflow_executable": False,
            "missing_fields": list(admission.get("missing_entities") or []),
            "reason": "workflow_admission_not_admitted",
        },
        "workflow_readiness_decision": {
            "workflow_id": admission.get("workflow_candidate"),
            "required_entities": list(admission.get("required_entities") or []),
            "completed_entities": list(admission.get("completed_entities") or []),
            "missing_entities": list(admission.get("missing_entities") or []),
            "workflow_complete": False,
            "reason_by_field": {},
        },
        "workflow_admission_gate": deepcopy(admission),
    }


def _result(
    candidate: str | None,
    decision: WorkflowAdmissionDecision,
    reason: WorkflowAdmissionReason,
    confidence: float,
    executable_signal: bool,
    analytical_signal: bool,
    business_scope: bool,
    keyword_only: bool,
    understanding: dict,
    resolver: dict,
    required: list[str],
    completed: list[str],
    missing: list[str],
    executable: bool,
    fallback: str | None,
) -> dict:
    admitted = decision == WorkflowAdmissionDecision.ADMIT
    summary = f"{decision.value}: {reason.value}"
    return WorkflowAdmissionResult(
        workflow_candidate=candidate,
        decision=decision.value,
        reason=reason.value,
        admitted=admitted,
        admission_confidence=confidence,
        executable_request_detected=executable_signal,
        analytical_question_detected=analytical_signal,
        business_level_scope_detected=business_scope,
        keyword_only_match_detected=keyword_only,
        understanding_confidence=understanding.get("confidence_score", understanding.get("confidence")),
        resolver_confidence=resolver.get("confidence_score", resolver.get("confidence")),
        required_entities=required,
        completed_entities=completed,
        missing_entities=missing,
        workflow_executable=executable,
        fallback_target=fallback,
        diagnostic_summary=summary,
    ).to_dict()


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle and needle.lower() in text for needle in needles)


def _looks_like_relationship_analysis(text: str) -> bool:
    return (
        ("\u0e40\u0e1e\u0e34\u0e48\u0e21" in text and "\u0e25\u0e14" in text)
        or ("\u0e02\u0e32\u0e22\u0e14\u0e35" in text and "\u0e01\u0e33\u0e44\u0e23" in text)
        or ("\u0e40\u0e07\u0e34\u0e19\u0e44\u0e21\u0e48\u0e40\u0e2b\u0e25\u0e37\u0e2d" in text)
    )


def _looks_like_question(text: str) -> bool:
    return "?" in text or any(token in text for token in ("\u0e44\u0e2b\u0e21", "\u0e2d\u0e30\u0e44\u0e23", "\u0e17\u0e33\u0e44\u0e21", "\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23", "what", "why", "how"))


def _is_low_confidence(score: Any, label: Any) -> bool:
    numeric = _score(score)
    if numeric is not None:
        return numeric < 0.55
    return str(label or "").strip().upper() in {"LOW", "UNKNOWN", ""}


def _is_high_confidence(score: Any, label: Any) -> bool:
    numeric = _score(score)
    if numeric is not None:
        return numeric >= 0.75
    return str(label or "").strip().upper() == "HIGH"


def _score(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _has_entity(entity: str, values: dict | None) -> bool:
    data = values or {}
    aliases = {
        "product": ("product", "product_or_service", "product_or_service_names", "business_type", "product_name"),
        "product_or_business_type": ("product_or_business_type", "product", "business_type", "product_or_service_names"),
        "price": ("price", "prices", "selling_price"),
        "cost": ("cost", "costs", "ingredients_costs", "unit_cost", "cost_per_unit"),
        "quantity": ("quantity", "quantities", "total_units", "units"),
        "date": ("date", "dates"),
        "daily_capacity_or_available_quantity": ("daily_capacity_or_available_quantity", "daily_capacity", "available_quantity", "quantities"),
        "selling_window_or_sales_channel": ("selling_window_or_sales_channel", "selling_window", "sales_channel"),
    }.get(entity, (entity,))
    return any(data.get(alias) not in (None, "", [], {}) for alias in aliases)
