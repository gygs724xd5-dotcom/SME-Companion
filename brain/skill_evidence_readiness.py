from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from brain.knowledge_skill_reference import as_dict
from brain.skill_applicability import SkillApplicabilityResult


SKILL_EVIDENCE_READINESS_VERSION = "5.9.1"


@dataclass
class SkillEvidenceReadinessResult:
    skill_id: str
    status: str
    support_strength: float = 0.0
    required_evidence: list[str] = field(default_factory=list)
    available_required_evidence: list[str] = field(default_factory=list)
    incomplete_required_evidence: list[str] = field(default_factory=list)
    missing_required_evidence: list[str] = field(default_factory=list)
    conflicting_required_evidence: list[str] = field(default_factory=list)
    stale_required_evidence: list[str] = field(default_factory=list)
    unverified_required_evidence: list[str] = field(default_factory=list)
    optional_evidence_available: list[str] = field(default_factory=list)
    optional_evidence_missing: list[str] = field(default_factory=list)
    conditionally_required_evidence: list[str] = field(default_factory=list)
    unresolved_conditions: list[str] = field(default_factory=list)
    blocking_relationship_rules: list[str] = field(default_factory=list)
    workflow_owned_evidence: list[str] = field(default_factory=list)
    next_evidence_gap: dict = field(default_factory=dict)
    readiness_reason: str = ""
    usable_for_procedural_analysis: bool = False
    usable_for_judgment_handoff: bool = False
    version: str = SKILL_EVIDENCE_READINESS_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def _metric_status(metric: dict) -> str:
    return str(metric.get("completeness_status") or "")


def evaluate_skill_evidence_readiness(
    skill: Any,
    *,
    available_metrics: dict | None = None,
    incomplete_metrics: dict | None = None,
    missing_metrics: list | None = None,
    applicability_result: SkillApplicabilityResult | None = None,
    workflow_owned_fields: list[str] | None = None,
    reference_valid: bool = True,
) -> SkillEvidenceReadinessResult:
    required = [item.evidence_id for item in getattr(skill, "evidence_requirements", []) if item.requirement_level == "REQUIRED"]
    optional = [item.evidence_id for item in getattr(skill, "evidence_requirements", []) if item.requirement_level == "OPTIONAL"]
    conditional = [item.evidence_id for item in getattr(skill, "evidence_requirements", []) if item.requirement_level == "CONDITIONALLY_REQUIRED"]
    available_metrics = available_metrics or {}
    incomplete_metrics = incomplete_metrics or {}
    workflow_owned = set(workflow_owned_fields or [])
    if not reference_valid:
        return SkillEvidenceReadinessResult(skill.skill_id, "INVALID_REFERENCE", required_evidence=required, readiness_reason="canonical reference invalid")
    if applicability_result and applicability_result.status in {"NOT_APPLICABLE", "EXCLUDED"}:
        return SkillEvidenceReadinessResult(skill.skill_id, "NOT_APPLICABLE", required_evidence=required, readiness_reason=applicability_result.status)

    available, incomplete, missing, conflicting, stale, unverified, owned = [], [], [], [], [], [], []
    for evidence_id in required:
        metric = as_dict(available_metrics.get(evidence_id)) or as_dict(incomplete_metrics.get(evidence_id))
        if evidence_id == "output_time_period":
            quantity_metric = as_dict(available_metrics.get("output_quantity")) or as_dict(incomplete_metrics.get("output_quantity"))
            if quantity_metric.get("timeframe"):
                available.append(evidence_id)
                continue
        if evidence_id in workflow_owned:
            owned.append(evidence_id)
        if not metric:
            missing.append(evidence_id)
            continue
        status = _metric_status(metric)
        if status == "AVAILABLE_COMPLETE":
            available.append(evidence_id)
        elif status == "CONFLICTING":
            conflicting.append(evidence_id)
        elif status == "HISTORICAL":
            stale.append(evidence_id)
        elif status == "UNVERIFIED":
            unverified.append(evidence_id)
        else:
            incomplete.append(evidence_id)
    optional_available = [item for item in optional if item in available_metrics or item in incomplete_metrics]
    optional_missing = [item for item in optional if item not in optional_available]
    if conflicting:
        status = "BLOCKED_BY_CONFLICT"
    elif owned:
        status = "BLOCKED_BY_WORKFLOW_OWNERSHIP"
    elif missing or incomplete:
        status = "BLOCKED_BY_REQUIRED_EVIDENCE"
    elif stale:
        status = "BLOCKED_BY_FRESHNESS"
    elif unverified:
        status = "PARTIALLY_READY"
    elif optional_missing:
        status = "READY_WITH_LIMITATIONS"
    else:
        status = "READY"
    next_gap_metric = (conflicting + owned + missing + incomplete + stale + unverified + conditional)[0] if (conflicting + owned + missing + incomplete + stale + unverified + conditional) else ""
    next_gap = {"metric_id": next_gap_metric, "gap_type": "CONFLICT_UNRESOLVED" if next_gap_metric in conflicting else "MISSING_REQUIRED_EVIDENCE"} if next_gap_metric else {}
    strength = 1.0 if status == "READY" else 0.75 if status == "READY_WITH_LIMITATIONS" else 0.45 if status == "PARTIALLY_READY" else 0.15
    return SkillEvidenceReadinessResult(
        skill.skill_id,
        status,
        strength,
        required,
        available,
        incomplete,
        missing,
        conflicting,
        stale,
        unverified,
        optional_available,
        optional_missing,
        conditional,
        [],
        list(getattr(skill, "relationship_rule_references", [])),
        owned,
        next_gap,
        status.lower(),
        usable_for_procedural_analysis=status in {"READY", "READY_WITH_LIMITATIONS", "PARTIALLY_READY", "BLOCKED_BY_REQUIRED_EVIDENCE"},
        usable_for_judgment_handoff=status in {"READY", "READY_WITH_LIMITATIONS"},
    )
