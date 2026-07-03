from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


EVIDENCE_GAP_RUNTIME_VERSION = "5.7.1"
EVIDENCE_GAP_RUNTIME_SOURCE = "evidence_gap_runtime"


class EvidenceGapPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


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
    reason: str = ""
    question: str = ""
    diagnostic_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvidenceGapRuntime:
    gap_items: list = field(default_factory=list)
    missing_evidence: list = field(default_factory=list)
    priority_queue: list = field(default_factory=list)
    next_best_question: dict = field(default_factory=dict)
    duplicate_question_guard: dict = field(default_factory=dict)
    completeness_status: dict = field(default_factory=dict)
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


def _item(field: str, source: str, reason: str, index: int) -> dict:
    priority = _priority_for(source)
    return EvidenceGapItem(
        gap_id=_gap_id(source, field, index),
        field=field,
        source=source,
        priority=priority.value,
        reason=reason,
        question=_question_for(field),
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
        items.append(_item(field, source, reason, len(items) + 1))

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
    return sorted(
        deepcopy(items),
        key=lambda item: (rank.get(item.get("priority"), 99), item.get("gap_id") or ""),
    )


def _duplicate_question_guard(queue: list[dict]) -> dict:
    questions = []
    seen = set()
    duplicates = []
    for item in queue:
        question = item.get("question")
        if not question:
            continue
        if question in seen:
            duplicates.append(question)
            continue
        seen.add(question)
        questions.append(question)
    return {
        "enabled": True,
        "unique_questions": questions,
        "duplicate_questions": duplicates,
        "duplicate_count": len(duplicates),
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
            "diagnostic_only": True,
        }
        for item in items
    ]
    completeness = {
        "status": "incomplete" if items else "complete",
        "gap_count": len(items),
        "missing_evidence_count": len(missing),
        "diagnostic_only": True,
    }
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
        missing_evidence=missing,
        priority_queue=queue,
        next_best_question=next_question,
        duplicate_question_guard=guard,
        completeness_status=completeness,
        diagnostics=diagnostics,
    )
    return runtime.to_dict()
