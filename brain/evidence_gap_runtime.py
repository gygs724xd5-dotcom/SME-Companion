from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


EVIDENCE_GAP_RUNTIME_VERSION = "5.7.2"
EVIDENCE_GAP_RUNTIME_SOURCE = "evidence_gap_runtime"


class EvidenceGapPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EvidenceGapDiagnosticPriority(str, Enum):
    CRITICAL = "CRITICAL"
    IMPORTANT = "IMPORTANT"
    HELPFUL = "HELPFUL"
    OPTIONAL = "OPTIONAL"


class EvidenceGapType(str, Enum):
    MISSING_FACT = "MISSING_FACT"
    MISSING_METRIC = "MISSING_METRIC"
    MISSING_TIMEFRAME = "MISSING_TIMEFRAME"
    MISSING_BUSINESS_CONTEXT = "MISSING_BUSINESS_CONTEXT"
    MISSING_CUSTOMER_CONTEXT = "MISSING_CUSTOMER_CONTEXT"
    MISSING_PRODUCT_CONTEXT = "MISSING_PRODUCT_CONTEXT"
    MISSING_INVENTORY_DATA = "MISSING_INVENTORY_DATA"
    MISSING_FINANCIAL_DATA = "MISSING_FINANCIAL_DATA"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    UNKNOWN_GAP = "UNKNOWN_GAP"


class EvidenceGapQuestionIntent(str, Enum):
    ASK_FACT = "ASK_FACT"
    ASK_METRIC = "ASK_METRIC"
    ASK_TIMEFRAME = "ASK_TIMEFRAME"
    ASK_BUSINESS_CONTEXT = "ASK_BUSINESS_CONTEXT"
    ASK_CUSTOMER_CONTEXT = "ASK_CUSTOMER_CONTEXT"
    ASK_PRODUCT_CONTEXT = "ASK_PRODUCT_CONTEXT"
    ASK_INVENTORY = "ASK_INVENTORY"
    ASK_FINANCIAL_DATA = "ASK_FINANCIAL_DATA"
    ASK_CLARIFICATION = "ASK_CLARIFICATION"
    NO_QUESTION = "NO_QUESTION"


def _as_dict(value: Any) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return list(value)
    if value in (None, "", {}, ()):
        return []
    return [value]


def _field_name(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("field", "evidence_type", "description", "name", "kind", "source"):
            if value.get(key) not in (None, "", [], {}):
                return str(value.get(key))
        return str(value)
    return str(value)


def _gap_id(source: str, field: str, index: int) -> str:
    normalized = "".join(char if char.isalnum() else "_" for char in field.lower()).strip("_")
    return f"evidence_gap_{source}_{index}_{normalized or 'unknown'}"


@dataclass
class EvidenceGapItem:
    gap_id: str
    field: str
    source: str
    priority: str = EvidenceGapPriority.MEDIUM.value
    diagnostic_priority: str = EvidenceGapDiagnosticPriority.OPTIONAL.value
    gap_type: str = EvidenceGapType.UNKNOWN_GAP.value
    question_intent: str = EvidenceGapQuestionIntent.ASK_CLARIFICATION.value
    reason: str = ""
    question: str = ""
    duplicate_guard_reason: str = ""
    duplicate_guard_hits: int = 0
    suppressed_questions: list = field(default_factory=list)
    diagnostic_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvidenceGapRuntime:
    gap_items: list = field(default_factory=list)
    gap_type: list = field(default_factory=list)
    question_intent: list = field(default_factory=list)
    missing_evidence: list = field(default_factory=list)
    priority_queue: list = field(default_factory=list)
    next_best_question: dict = field(default_factory=dict)
    duplicate_question_guard: dict = field(default_factory=dict)
    duplicate_guard_reason: str = ""
    duplicate_guard_hits: dict = field(default_factory=dict)
    suppressed_questions: list = field(default_factory=list)
    completeness_status: dict = field(default_factory=dict)
    completeness_reason: str = ""
    diagnostics: dict = field(default_factory=dict)
    version: str = EVIDENCE_GAP_RUNTIME_VERSION
    source: str = EVIDENCE_GAP_RUNTIME_SOURCE
    runtime_only: bool = True
    diagnostic_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def _question_for(field: str) -> str:
    return f"What evidence is available for {field}?"


def _priority_for(source: str) -> EvidenceGapPriority:
    if source in {"evidence_runtime_missing", "truth_runtime_insufficient"}:
        return EvidenceGapPriority.HIGH
    if source in {"truth_runtime_conflicting", "business_situation_uncertainty"}:
        return EvidenceGapPriority.MEDIUM
    return EvidenceGapPriority.LOW


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _combined_context(business_situation: dict, field: str, source: str, reason: str) -> str:
    parts = [
        field,
        source,
        reason,
        business_situation.get("current_goal"),
        business_situation.get("current_problem"),
        business_situation.get("current_operation"),
        business_situation.get("current_focus"),
        business_situation.get("conversation_purpose"),
        business_situation.get("business_topic"),
    ]
    return " ".join(str(part or "").lower() for part in parts)


def _classify_gap(
    *,
    business_situation: dict,
    evidence_runtime: dict,
    truth_runtime: dict,
    field: str,
    source: str,
    reason: str,
) -> tuple[str, str]:
    context = _combined_context(business_situation, field, source, reason)
    truth_summary = _as_dict(truth_runtime.get("truth_summary"))
    truth_diagnostics = _as_dict(truth_runtime.get("diagnostics"))
    evidence_confidence = evidence_runtime.get("evidence_confidence")
    try:
        confidence = float(evidence_confidence)
    except (TypeError, ValueError):
        confidence = None

    if (
        source == "truth_runtime_conflicting"
        or bool(truth_summary.get("has_conflicts"))
        or int(truth_diagnostics.get("conflicting_truth_count") or 0) > 0
        or bool(_as_list(evidence_runtime.get("conflicting_evidence")))
    ):
        return EvidenceGapType.CONFLICTING_EVIDENCE.value, EvidenceGapQuestionIntent.ASK_CLARIFICATION.value
    if source == "truth_runtime_unknown" or (confidence is not None and confidence < 0.35):
        return EvidenceGapType.LOW_CONFIDENCE.value, EvidenceGapQuestionIntent.ASK_CLARIFICATION.value
    if _contains_any(context, {"stock", "inventory", "remaining", "left", "on hand", "in stock"}):
        return EvidenceGapType.MISSING_INVENTORY_DATA.value, EvidenceGapQuestionIntent.ASK_INVENTORY.value
    if _contains_any(context, {"time_period", "timeframe", "period", "date", "month", "week", "year", "today", "yesterday", "daily", "weekly", "monthly"}):
        return EvidenceGapType.MISSING_TIMEFRAME.value, EvidenceGapQuestionIntent.ASK_TIMEFRAME.value
    if _contains_any(context, {"profit", "cost", "margin", "revenue", "price", "financial", "sales", "discount"}):
        if _contains_any(context, {"amount", "number", "metric", "rate", "percentage", "%"}):
            return EvidenceGapType.MISSING_METRIC.value, EvidenceGapQuestionIntent.ASK_METRIC.value
        return EvidenceGapType.MISSING_FINANCIAL_DATA.value, EvidenceGapQuestionIntent.ASK_FINANCIAL_DATA.value
    if _contains_any(context, {"customer", "buyer", "segment", "audience"}):
        return EvidenceGapType.MISSING_CUSTOMER_CONTEXT.value, EvidenceGapQuestionIntent.ASK_CUSTOMER_CONTEXT.value
    if _contains_any(context, {"product", "item", "sku", "service"}):
        return EvidenceGapType.MISSING_PRODUCT_CONTEXT.value, EvidenceGapQuestionIntent.ASK_PRODUCT_CONTEXT.value
    if _contains_any(context, {"business", "shop", "store", "operation"}):
        return EvidenceGapType.MISSING_BUSINESS_CONTEXT.value, EvidenceGapQuestionIntent.ASK_BUSINESS_CONTEXT.value
    if field:
        return EvidenceGapType.MISSING_FACT.value, EvidenceGapQuestionIntent.ASK_FACT.value
    return EvidenceGapType.UNKNOWN_GAP.value, EvidenceGapQuestionIntent.ASK_CLARIFICATION.value


def _diagnostic_priority_for(gap_type: str) -> str:
    mapping = {
        EvidenceGapType.CONFLICTING_EVIDENCE.value: EvidenceGapDiagnosticPriority.CRITICAL.value,
        EvidenceGapType.MISSING_FINANCIAL_DATA.value: EvidenceGapDiagnosticPriority.IMPORTANT.value,
        EvidenceGapType.MISSING_INVENTORY_DATA.value: EvidenceGapDiagnosticPriority.IMPORTANT.value,
        EvidenceGapType.MISSING_TIMEFRAME.value: EvidenceGapDiagnosticPriority.IMPORTANT.value,
        EvidenceGapType.MISSING_BUSINESS_CONTEXT.value: EvidenceGapDiagnosticPriority.HELPFUL.value,
        EvidenceGapType.LOW_CONFIDENCE.value: EvidenceGapDiagnosticPriority.HELPFUL.value,
    }
    return mapping.get(gap_type, EvidenceGapDiagnosticPriority.OPTIONAL.value)


def _item(
    business_situation: dict,
    evidence_runtime: dict,
    truth_runtime: dict,
    field: str,
    source: str,
    reason: str,
    index: int,
) -> dict:
    priority = _priority_for(source)
    gap_type, question_intent = _classify_gap(
        business_situation=business_situation,
        evidence_runtime=evidence_runtime,
        truth_runtime=truth_runtime,
        field=field,
        source=source,
        reason=reason,
    )
    return EvidenceGapItem(
        gap_id=_gap_id(source, field, index),
        field=field,
        source=source,
        priority=priority.value,
        diagnostic_priority=_diagnostic_priority_for(gap_type),
        gap_type=gap_type,
        question_intent=question_intent,
        reason=reason,
        question=_question_for(field),
        duplicate_guard_reason="unique_question_pending_guard",
    ).to_dict()


def _gap_items(
    business_situation: dict,
    evidence_runtime: dict,
    truth_runtime: dict,
) -> list[dict]:
    items: list[dict] = []
    seen = set()

    def add(field: str, source: str, reason: str) -> None:
        key = (field, source)
        if not field or key in seen:
            return
        seen.add(key)
        items.append(_item(business_situation, evidence_runtime, truth_runtime, field, source, reason, len(items) + 1))

    for missing in _as_list(evidence_runtime.get("missing_evidence")):
        payload = _as_dict(missing)
        add(
            _field_name(payload or missing),
            "evidence_runtime_missing",
            str(payload.get("reason") or "Evidence Runtime reports missing evidence."),
        )

    for truth in _as_list(truth_runtime.get("truth_items")):
        payload = _as_dict(truth)
        classification = str(payload.get("classification") or "")
        if classification == "INSUFFICIENT":
            value = _as_dict(payload.get("value"))
            add(
                _field_name(value or payload),
                "truth_runtime_insufficient",
                "Truth Runtime classifies reliance as insufficient.",
            )
        elif classification == "CONFLICTING":
            add(
                _field_name(payload.get("value") or payload),
                "truth_runtime_conflicting",
                "Truth Runtime reports conflicting evidence.",
            )
        elif classification in {"UNKNOWN", "UNVERIFIED"}:
            add(
                _field_name(payload),
                "truth_runtime_unknown",
                "Truth Runtime reports unknown or unverified reliance.",
            )

    for uncertainty in _as_list(business_situation.get("material_uncertainty")):
        payload = _as_dict(uncertainty)
        add(
            _field_name(payload or uncertainty),
            "business_situation_uncertainty",
            str(payload.get("why_material") or "Business Situation reports material uncertainty."),
        )

    return items


def _priority_queue(items: list[dict]) -> list[dict]:
    rank = {
        EvidenceGapPriority.HIGH.value: 0,
        EvidenceGapPriority.MEDIUM.value: 1,
        EvidenceGapPriority.LOW.value: 2,
    }
    diagnostic_rank = {
        EvidenceGapDiagnosticPriority.CRITICAL.value: 0,
        EvidenceGapDiagnosticPriority.IMPORTANT.value: 1,
        EvidenceGapDiagnosticPriority.HELPFUL.value: 2,
        EvidenceGapDiagnosticPriority.OPTIONAL.value: 3,
    }
    return sorted(
        deepcopy(items),
        key=lambda item: (
            diagnostic_rank.get(item.get("diagnostic_priority"), 99),
            rank.get(item.get("priority"), 99),
            item.get("gap_id") or "",
        ),
    )


def _duplicate_question_guard(queue: list[dict]) -> dict:
    questions = []
    seen = set()
    duplicates = []
    duplicate_hits = {}
    for item in queue:
        question = item.get("question")
        if not question:
            continue
        if question in seen:
            duplicates.append(question)
            duplicate_hits[question] = duplicate_hits.get(question, 1) + 1
            item["duplicate_guard_reason"] = "duplicate_question_suppressed"
            item["duplicate_guard_hits"] = duplicate_hits[question]
            item["suppressed_questions"] = [question]
            continue
        seen.add(question)
        questions.append(question)
        item["duplicate_guard_reason"] = "unique_question_allowed"
        item["duplicate_guard_hits"] = 0
        item["suppressed_questions"] = []
    return {
        "enabled": True,
        "unique_questions": questions,
        "duplicate_questions": duplicates,
        "duplicate_count": len(duplicates),
        "duplicate_guard_reason": "duplicate_question_scan_complete",
        "duplicate_guard_hits": duplicate_hits,
        "suppressed_questions": duplicates,
        "diagnostic_only": True,
    }


def _completeness_status(items: list[dict], missing: list[dict], evidence_runtime: dict, truth_runtime: dict) -> dict:
    evidence_items = _as_list(evidence_runtime.get("evidence_items"))
    conflicts = _as_list(evidence_runtime.get("conflicting_evidence")) + _as_list(truth_runtime.get("conflicting_truths"))
    score = max(0, len(evidence_items) - len(items) - len(conflicts))
    if not evidence_items and items:
        refined_status = "EMPTY"
    elif items or conflicts:
        refined_status = "PARTIAL"
    elif evidence_items:
        refined_status = "SUFFICIENT"
    else:
        refined_status = "ADEQUATE"
    legacy_status = "incomplete" if items else "complete"
    reason = (
        "No supporting evidence is available for the current diagnostic gaps."
        if refined_status == "EMPTY"
        else "Some evidence exists, but diagnostic gaps remain."
        if refined_status == "PARTIAL"
        else "Available evidence has no diagnostic gaps in this runtime."
    )
    return {
        "status": legacy_status,
        "completeness_status": refined_status,
        "completeness_score": score,
        "completeness_reason": reason,
        "gap_count": len(items),
        "missing_evidence_count": len(missing),
        "diagnostic_only": True,
    }


def build_evidence_gap_runtime(
    *,
    business_situation: dict | None = None,
    evidence_runtime: dict | None = None,
    truth_runtime: dict | None = None,
) -> dict:
    """Create diagnostics-only Evidence Gap Runtime.

    Evidence Gap Runtime identifies missing evidence only. It does not interpret
    meaning, recommend actions, decide next behavior, alter responses, or write
    memory.
    """

    situation = _as_dict(business_situation)
    situation_diagnostics = _as_dict(situation.get("diagnostics"))
    evidence = _as_dict(evidence_runtime) or _as_dict(situation_diagnostics.get("evidence"))
    truth = _as_dict(truth_runtime) or _as_dict(situation_diagnostics.get("truth"))
    items = _gap_items(situation, evidence, truth)
    queue = _priority_queue(items)
    guard = _duplicate_question_guard(queue)
    next_question = deepcopy(queue[0]) if queue else {}
    missing = [
        {
            "field": item.get("field"),
            "source": item.get("source"),
            "priority": item.get("priority"),
            "diagnostic_priority": item.get("diagnostic_priority"),
            "gap_type": item.get("gap_type"),
            "question_intent": item.get("question_intent"),
            "diagnostic_only": True,
        }
        for item in items
    ]
    completeness = _completeness_status(items, missing, evidence, truth)
    diagnostics = {
        "evidence_gap_runtime_created": True,
        "evidence_gap_runtime_version": EVIDENCE_GAP_RUNTIME_VERSION,
        "evidence_gap_runtime_source": EVIDENCE_GAP_RUNTIME_SOURCE,
        "gap_item_count": len(items),
        "missing_evidence_count": len(missing),
        "priority_queue_count": len(queue),
        "next_best_question_present": bool(next_question),
        "duplicate_question_guard_enabled": True,
        "completeness_status": completeness.get("status"),
        "completeness_status_refined": completeness.get("completeness_status"),
        "completeness_reason": completeness.get("completeness_reason"),
        "gap_types": [item.get("gap_type") for item in items],
        "question_intents": [item.get("question_intent") for item in items],
        "duplicate_guard_reason": guard.get("duplicate_guard_reason"),
        "duplicate_guard_hits": guard.get("duplicate_guard_hits"),
        "suppressed_questions": guard.get("suppressed_questions"),
        "diagnostic_only": True,
        "runtime_only": True,
        "reads_business_situation_diagnostics": True,
        "reads_evidence_runtime_diagnostics": True,
        "reads_truth_runtime_diagnostics": True,
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
        "business_situation_modified": False,
        "business_memory_modified": False,
        "evidence_runtime_modified": False,
        "truth_runtime_modified": False,
        "business_meaning_interpreted": False,
        "recommendation_produced": False,
        "decision_made": False,
    }
    runtime = EvidenceGapRuntime(
        gap_items=items,
        gap_type=[item.get("gap_type") for item in items],
        question_intent=[item.get("question_intent") for item in items],
        missing_evidence=missing,
        priority_queue=queue,
        next_best_question=next_question,
        duplicate_question_guard=guard,
        duplicate_guard_reason=guard.get("duplicate_guard_reason") or "",
        duplicate_guard_hits=guard.get("duplicate_guard_hits") or {},
        suppressed_questions=guard.get("suppressed_questions") or [],
        completeness_status=completeness,
        completeness_reason=completeness.get("completeness_reason") or "",
        diagnostics=diagnostics,
    )
    return runtime.to_dict()
