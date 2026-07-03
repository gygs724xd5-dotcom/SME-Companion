from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4


EVIDENCE_RUNTIME_VERSION = "5.6.0"
EVIDENCE_RUNTIME_SOURCE = "evidence_runtime"


def _new_evidence_id() -> str:
    return f"evidence_{uuid4().hex}"


def _as_dict(value: Any) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return list(value)
    if value in (None, "", {}, ()):
        return []
    return [value]


def _confidence(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _field_name(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("field", "name", "entity", "description", "kind"):
            if value.get(key) not in (None, "", [], {}):
                return str(value.get(key))
        return str(value)
    return str(value)


@dataclass
class EvidenceItem:
    evidence_id: str = field(default_factory=_new_evidence_id)
    evidence_type: str = ""
    source: str = ""
    value: Any = None
    relevance: str = ""
    confidence: float = 0.0
    supports: list = field(default_factory=list)
    conflicts_with: list = field(default_factory=list)
    diagnostic_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvidenceRuntime:
    evidence_available: bool = False
    evidence_items: list = field(default_factory=list)
    missing_evidence: list = field(default_factory=list)
    conflicting_evidence: list = field(default_factory=list)
    evidence_confidence: float = 0.0
    evidence_source: str = EVIDENCE_RUNTIME_SOURCE
    evidence_diagnostics: dict = field(default_factory=dict)
    runtime_only: bool = True
    diagnostic_only: bool = True
    version: str = EVIDENCE_RUNTIME_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def _evidence_items_from_situation(business_situation: dict) -> list[dict]:
    items: list[dict] = []
    for index, item in enumerate(_as_list(business_situation.get("known_evidence")), start=1):
        payload = _as_dict(item)
        if not payload:
            continue
        evidence_type = str(payload.get("kind") or payload.get("evidence_type") or "business_situation_evidence")
        source = str(payload.get("source") or "business_situation")
        evidence = EvidenceItem(
            evidence_id=f"evidence_runtime_{index}_{source}_{evidence_type}",
            evidence_type=evidence_type,
            source=source,
            value=deepcopy(payload.get("summary") if "summary" in payload else payload.get("value")),
            relevance="business_situation_support",
            confidence=_confidence(payload.get("confidence"), default=0.0),
            supports=["business_situation"],
        )
        items.append(evidence.to_dict())
    return items


def _missing_evidence_from_situation(business_situation: dict) -> list[dict]:
    missing: list[dict] = []
    seen = set()
    for uncertainty in _as_list(business_situation.get("material_uncertainty")):
        payload = _as_dict(uncertainty)
        field_name = _field_name(payload or uncertainty)
        if field_name in seen:
            continue
        seen.add(field_name)
        missing.append(
            {
                "field": field_name,
                "source": payload.get("kind") or "business_situation_uncertainty",
                "reason": payload.get("why_material") or "Information may be required to support the current Business Situation.",
                "diagnostic_only": True,
            }
        )
    return missing


def _conflicting_evidence_from_situation(business_situation: dict) -> list[dict]:
    diagnostics = _as_dict(business_situation.get("situation_diagnostics"))
    if not diagnostics.get("memory_conflict"):
        return []
    return [
        {
            "conflict_type": "business_memory_conversation_conflict",
            "source": "business_situation_runtime",
            "memory_value": diagnostics.get("memory_value"),
            "conversation_value": diagnostics.get("conversation_value"),
            "current_value": diagnostics.get("current_value"),
            "diagnostic_only": True,
        }
    ]


def _runtime_confidence(items: list[dict], missing: list[dict], conflicts: list[dict]) -> float:
    if not items:
        return 0.0
    confidences = [_confidence(item.get("confidence"), default=0.0) for item in items]
    base = sum(confidences) / len(confidences) if confidences else 0.0
    penalty = min(0.5, (0.05 * len(missing)) + (0.15 * len(conflicts)))
    return max(0.0, round(base - penalty, 4))


def build_evidence_runtime(
    *,
    business_situation: dict | None = None,
    perception_diagnostics: dict | None = None,
    conversation_context: dict | None = None,
    business_memory_reference: Any = None,
    structured_business_data: dict | None = None,
) -> dict:
    """Create diagnostics-only Evidence Runtime from existing runtime context.

    Evidence records available, missing, and conflicting information. It does
    not decide truth, alter routing, choose workflows, generate responses, or
    write memory.
    """

    del perception_diagnostics, conversation_context, business_memory_reference, structured_business_data
    situation = _as_dict(business_situation)
    items = _evidence_items_from_situation(situation)
    missing = _missing_evidence_from_situation(situation)
    conflicts = _conflicting_evidence_from_situation(situation)
    confidence = _runtime_confidence(items, missing, conflicts)
    diagnostics = {
        "evidence_runtime_created": True,
        "evidence_runtime_version": EVIDENCE_RUNTIME_VERSION,
        "evidence_runtime_source": EVIDENCE_RUNTIME_SOURCE,
        "evidence_available": bool(items),
        "evidence_item_count": len(items),
        "missing_evidence_count": len(missing),
        "conflicting_evidence_count": len(conflicts),
        "diagnostic_only": True,
        "runtime_only": True,
        "used_for_routing": False,
        "used_for_planner": False,
        "used_for_workflow": False,
        "used_for_response": False,
        "used_for_execution": False,
        "used_for_commit": False,
        "business_situation_modified": False,
        "business_memory_modified": False,
        "authority_modified": False,
        "truth_status_determined": False,
        "business_judgment_produced": False,
        "decision_made": False,
    }
    runtime = EvidenceRuntime(
        evidence_available=bool(items),
        evidence_items=items,
        missing_evidence=missing,
        conflicting_evidence=conflicts,
        evidence_confidence=confidence,
        evidence_diagnostics=diagnostics,
    )
    return runtime.to_dict()
