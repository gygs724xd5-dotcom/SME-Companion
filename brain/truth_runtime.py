from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


TRUTH_RUNTIME_VERSION = "5.7.0"
TRUTH_RUNTIME_SOURCE = "truth_runtime"


class TruthClassification(str, Enum):
    OBSERVED = "OBSERVED"
    REPORTED = "REPORTED"
    DERIVED = "DERIVED"
    HISTORICAL = "HISTORICAL"
    RUNTIME = "RUNTIME"
    OFFICIAL = "OFFICIAL"
    UNVERIFIED = "UNVERIFIED"
    CONFLICTING = "CONFLICTING"
    INSUFFICIENT = "INSUFFICIENT"
    UNKNOWN = "UNKNOWN"


def _new_truth_id() -> str:
    return f"truth_{uuid4().hex}"


def _as_dict(value: Any) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return list(value)
    if value in (None, "", {}, ()):
        return []
    return [value]


def _classification_for_evidence(item: dict) -> TruthClassification:
    source = str(item.get("source") or "").strip().lower()
    evidence_type = str(item.get("evidence_type") or item.get("kind") or "").strip().lower()
    confidence = item.get("confidence")
    try:
        confidence_value = float(confidence)
    except (TypeError, ValueError):
        confidence_value = 0.0

    if source in {"official", "official_record", "system_of_record"}:
        return TruthClassification.OFFICIAL
    if source in {"memory", "business_memory", "conversation_memory"} or "memory" in source:
        return TruthClassification.HISTORICAL
    if source in {"user", "current_message"} or evidence_type == "current_message":
        return TruthClassification.OBSERVED
    if source in {"business_situation", "business_situation_runtime"}:
        return TruthClassification.RUNTIME
    if source in {"conversation_understanding", "canonical_entities", "business_context"}:
        return TruthClassification.DERIVED
    if confidence_value <= 0.0:
        return TruthClassification.UNVERIFIED
    if source:
        return TruthClassification.REPORTED
    return TruthClassification.UNKNOWN


@dataclass
class TruthItem:
    truth_id: str = field(default_factory=_new_truth_id)
    classification: str = TruthClassification.UNKNOWN.value
    source: str = ""
    evidence_id: str = ""
    evidence_type: str = ""
    value: Any = None
    reliance_state: str = "unknown"
    diagnostic_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TruthRuntime:
    truth_items: list = field(default_factory=list)
    truth_summary: dict = field(default_factory=dict)
    runtime_truth: list = field(default_factory=list)
    historical_truth: list = field(default_factory=list)
    conflicting_truths: list = field(default_factory=list)
    unknown_truths: list = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)
    version: str = TRUTH_RUNTIME_VERSION
    source: str = TRUTH_RUNTIME_SOURCE
    runtime_only: bool = True
    diagnostic_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def _truth_item_from_evidence(item: dict, index: int) -> dict:
    classification = _classification_for_evidence(item)
    truth_item = TruthItem(
        truth_id=f"truth_runtime_{index}_{item.get('evidence_id') or 'evidence'}",
        classification=classification.value,
        source=str(item.get("source") or ""),
        evidence_id=str(item.get("evidence_id") or ""),
        evidence_type=str(item.get("evidence_type") or item.get("kind") or ""),
        value=deepcopy(item.get("value")),
        reliance_state=classification.value.lower(),
    )
    return truth_item.to_dict()


def _truth_item_from_conflict(item: dict, index: int) -> dict:
    truth_item = TruthItem(
        truth_id=f"truth_conflict_{index}_{item.get('conflict_type') or 'evidence'}",
        classification=TruthClassification.CONFLICTING.value,
        source=str(item.get("source") or ""),
        evidence_type=str(item.get("conflict_type") or "conflicting_evidence"),
        value=deepcopy(item),
        reliance_state="conflicting",
    )
    return truth_item.to_dict()


def _truth_item_from_missing(item: dict, index: int) -> dict:
    truth_item = TruthItem(
        truth_id=f"truth_insufficient_{index}_{item.get('field') or 'evidence'}",
        classification=TruthClassification.INSUFFICIENT.value,
        source=str(item.get("source") or ""),
        evidence_type=str(item.get("field") or "missing_evidence"),
        value=deepcopy(item),
        reliance_state="insufficient",
    )
    return truth_item.to_dict()


def _classification_counts(items: list[dict]) -> dict:
    counts = {classification.value: 0 for classification in TruthClassification}
    for item in items:
        classification = item.get("classification") or TruthClassification.UNKNOWN.value
        counts[classification] = counts.get(classification, 0) + 1
    return counts


def build_truth_runtime(*, evidence_runtime: dict | None = None) -> dict:
    """Create diagnostics-only Truth Runtime from Evidence Runtime.

    Truth Runtime classifies justified reliance over already available evidence.
    It does not discover evidence, retrieve knowledge, reason about business,
    decide truth, alter behavior, or write memory.
    """

    evidence = _as_dict(evidence_runtime)
    truth_items = [
        _truth_item_from_evidence(item, index)
        for index, item in enumerate(_as_list(evidence.get("evidence_items")), start=1)
        if isinstance(item, dict)
    ]
    conflicting_truths = [
        _truth_item_from_conflict(item, index)
        for index, item in enumerate(_as_list(evidence.get("conflicting_evidence")), start=1)
        if isinstance(item, dict)
    ]
    insufficient_truths = [
        _truth_item_from_missing(item, index)
        for index, item in enumerate(_as_list(evidence.get("missing_evidence")), start=1)
        if isinstance(item, dict)
    ]
    all_items = truth_items + conflicting_truths + insufficient_truths
    runtime_truth = [
        item
        for item in all_items
        if item.get("classification") in {TruthClassification.OBSERVED.value, TruthClassification.RUNTIME.value}
    ]
    historical_truth = [
        item
        for item in all_items
        if item.get("classification") == TruthClassification.HISTORICAL.value
    ]
    unknown_truths = [
        item
        for item in all_items
        if item.get("classification") in {TruthClassification.UNKNOWN.value, TruthClassification.UNVERIFIED.value}
    ]
    counts = _classification_counts(all_items)
    diagnostics = {
        "truth_runtime_created": True,
        "truth_runtime_version": TRUTH_RUNTIME_VERSION,
        "truth_runtime_source": TRUTH_RUNTIME_SOURCE,
        "truth_item_count": len(all_items),
        "runtime_truth_count": len(runtime_truth),
        "historical_truth_count": len(historical_truth),
        "conflicting_truth_count": len(conflicting_truths),
        "unknown_truth_count": len(unknown_truths),
        "classification_counts": counts,
        "diagnostic_only": True,
        "runtime_only": True,
        "reads_evidence_runtime_only": True,
        "used_for_routing": False,
        "used_for_planner": False,
        "used_for_workflow": False,
        "used_for_response": False,
        "used_for_execution": False,
        "used_for_commit": False,
        "business_situation_modified": False,
        "evidence_modified": False,
        "business_memory_modified": False,
        "authority_modified": False,
        "knowledge_retrieved": False,
        "business_reasoning_performed": False,
        "decision_made": False,
    }
    runtime = TruthRuntime(
        truth_items=all_items,
        truth_summary={
            "truth_item_count": len(all_items),
            "classification_counts": counts,
            "has_conflicts": bool(conflicting_truths),
            "has_unknowns": bool(unknown_truths),
            "has_insufficient_evidence": bool(insufficient_truths),
            "diagnostic_only": True,
        },
        runtime_truth=runtime_truth,
        historical_truth=historical_truth,
        conflicting_truths=conflicting_truths,
        unknown_truths=unknown_truths,
        diagnostics=diagnostics,
    )
    return runtime.to_dict()
