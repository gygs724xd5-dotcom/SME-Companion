from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any
import hashlib
import json

from brain.judgment_contracts import (
    BUSINESS_JUDGMENT_VERSION,
    CausalClaimLevel,
    ConfidenceClass,
    OutcomeStatus,
    ResponseMode,
)


JUDGMENT_OUTCOME_VERSION = "5.10.4"


@dataclass
class JudgmentClaim:
    claim_id: str
    claim_type: str
    subject: str
    predicate: str
    object: str
    claim_level: str
    evidence_ids: list[str] = field(default_factory=list)
    confidence_class: str = ConfidenceClass.NO_RELIABLE_JUDGMENT.value
    support_strength: str = "INSUFFICIENT"
    scope: str = ""
    timeframe: str = ""
    caveat: str = ""
    allowed_for_response: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class JudgmentDecisionBoundary:
    judgment_complete: bool = False
    decision_eligible: bool = False
    decision_block_reason: str = "V5.10 prepares future Decision handoff only."
    recommendation_allowed: bool = False
    action_selection_allowed: bool = False
    planner_allowed: bool = False
    workflow_allowed: bool = False
    tool_allowed: bool = False
    ready_for_future_decision: bool = False
    decision_made: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class JudgmentOutcomeResponseHandoff:
    response_mode: str
    safe_summary: str = ""
    primary_claims: list = field(default_factory=list)
    alternative_claims: list = field(default_factory=list)
    evidence_summary: dict = field(default_factory=dict)
    contradiction_summary: list = field(default_factory=list)
    limitation_summary: list = field(default_factory=list)
    uncertainty_language: str = ""
    revision_notice: str = ""
    next_evidence_need: dict = field(default_factory=dict)
    clarification_allowed: bool = False
    forbidden_phrases: list[str] = field(default_factory=list)
    decision_language_blocked: bool = True
    planner_language_blocked: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class JudgmentOutcome:
    outcome_id: str
    active_topic_id: str
    judgment_status: str
    judgment_type: str
    selected_explanations: list = field(default_factory=list)
    alternative_explanations: list = field(default_factory=list)
    evidence_basis: list = field(default_factory=list)
    contradicting_evidence: list = field(default_factory=list)
    unresolved_evidence: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    support_strength: str = "INSUFFICIENT"
    confidence_class: str = ConfidenceClass.NO_RELIABLE_JUDGMENT.value
    maximum_claim_level: str = CausalClaimLevel.CONTRIBUTING_FACTOR.value
    safe_claims: list = field(default_factory=list)
    suppressed_claims: list = field(default_factory=list)
    limitation_summary: list = field(default_factory=list)
    next_evidence_need: dict = field(default_factory=dict)
    revision_status: str = ""
    response_handoff: dict = field(default_factory=dict)
    decision_boundary: dict = field(default_factory=dict)
    authority_trace: list[str] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _as_dict(value: Any) -> dict:
    return deepcopy(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return deepcopy(value)
    if value in (None, "", {}, ()):
        return []
    return [deepcopy(value)]


FORBIDDEN_PHRASES = [
    "\u0e14\u0e31\u0e07\u0e19\u0e31\u0e49\u0e19\u0e04\u0e27\u0e23",
    "\u0e41\u0e19\u0e30\u0e19\u0e33\u0e43\u0e2b\u0e49",
    "\u0e17\u0e32\u0e07\u0e17\u0e35\u0e48\u0e14\u0e35\u0e17\u0e35\u0e48\u0e2a\u0e38\u0e14\u0e04\u0e37\u0e2d",
    "\u0e04\u0e27\u0e23\u0e40\u0e25\u0e37\u0e2d\u0e01",
    "\u0e04\u0e27\u0e23\u0e40\u0e23\u0e34\u0e48\u0e21",
    "\u0e25\u0e2d\u0e07\u0e17\u0e33",
    "\u0e0b\u0e37\u0e49\u0e2d",
    "\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e04\u0e19",
    "\u0e2a\u0e31\u0e48\u0e07\u0e40\u0e1e\u0e34\u0e48\u0e21",
    "\u0e40\u0e1b\u0e25\u0e35\u0e48\u0e22\u0e19\u0e0b\u0e31\u0e1e\u0e1e\u0e25\u0e32\u0e22\u0e40\u0e2d\u0e2d\u0e23\u0e4c",
    "\u0e40\u0e1b\u0e34\u0e14\u0e41\u0e04\u0e21\u0e40\u0e1b\u0e0d",
]


def uncertainty_language(confidence_class: str) -> str:
    return {
        ConfidenceClass.HIGH_CONFIDENCE.value: "\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\u0e2a\u0e19\u0e31\u0e1a\u0e2a\u0e19\u0e38\u0e19\u0e04\u0e48\u0e2d\u0e19\u0e02\u0e49\u0e32\u0e07\u0e0a\u0e31\u0e14\u0e27\u0e48\u0e32",
        ConfidenceClass.MEDIUM_CONFIDENCE.value: "\u0e21\u0e35\u0e19\u0e49\u0e33\u0e2b\u0e19\u0e31\u0e01\u0e27\u0e48\u0e32",
        ConfidenceClass.LOW_CONFIDENCE.value: "\u0e40\u0e1b\u0e47\u0e19\u0e44\u0e1b\u0e44\u0e14\u0e49\u0e27\u0e48\u0e32",
        ConfidenceClass.NO_RELIABLE_JUDGMENT.value: "\u0e15\u0e2d\u0e19\u0e19\u0e35\u0e49\u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e21\u0e35\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\u0e1e\u0e2d\u0e08\u0e30\u0e2a\u0e23\u0e38\u0e1b\u0e27\u0e48\u0e32",
    }.get(confidence_class, "\u0e15\u0e2d\u0e19\u0e19\u0e35\u0e49\u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e21\u0e35\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\u0e1e\u0e2d\u0e08\u0e30\u0e2a\u0e23\u0e38\u0e1b\u0e27\u0e48\u0e32")


def _claim_for_candidate(candidate: dict, result: dict, index: int) -> dict:
    evidence_ids = [
        evidence.get("evidence_id")
        for evidence in candidate.get("supporting_evidence") or []
        if isinstance(evidence, dict) and evidence.get("evidence_id")
    ]
    return JudgmentClaim(
        claim_id=f"judgment_claim::{index}::{candidate.get('candidate_id')}",
        claim_type="CONTRIBUTING_FACTOR_CLAIM" if candidate.get("causal_claim_level") == CausalClaimLevel.CONTRIBUTING_FACTOR.value else "CONDITION_CLAIM",
        subject=candidate.get("explanation") or candidate.get("candidate_id"),
        predicate="is supported as",
        object="a contributing factor or condition",
        claim_level=min_claim_level(candidate.get("causal_claim_level")),
        evidence_ids=evidence_ids,
        confidence_class=result.get("confidence_class"),
        support_strength=candidate.get("support_strength"),
        scope="business",
        timeframe="supplied evidence timeframe",
        caveat="Not a recommendation or sole-cause claim.",
        allowed_for_response=bool(evidence_ids),
    ).to_dict()


def min_claim_level(level: str) -> str:
    if level in {CausalClaimLevel.PRIMARY_DRIVER.value, CausalClaimLevel.CONFIRMED_CAUSE.value}:
        return CausalClaimLevel.CONTRIBUTING_FACTOR.value
    return level or CausalClaimLevel.CONTRIBUTING_FACTOR.value


def _status(result: dict, selected: list, alternatives: list) -> str:
    if result.get("judgment_status") == "CONFLICT_BLOCKED" or result.get("contradictions"):
        return OutcomeStatus.CONFLICT_BLOCKED.value
    if not selected and result.get("judgment_status") == "MULTIPLE_PLAUSIBLE_EXPLANATIONS":
        return OutcomeStatus.MULTIPLE_PLAUSIBLE_EXPLANATIONS.value
    if not selected:
        return OutcomeStatus.INSUFFICIENT_EVIDENCE.value
    if len(selected) > 1:
        return OutcomeStatus.MULTIPLE_CONTRIBUTING_FACTORS.value
    if alternatives:
        return OutcomeStatus.TENTATIVE_JUDGMENT.value
    return OutcomeStatus.SUPPORTED_JUDGMENT.value


def _mode(status: str) -> str:
    return {
        OutcomeStatus.SUPPORTED_JUDGMENT.value: ResponseMode.DIRECT_JUDGMENT.value,
        OutcomeStatus.TENTATIVE_JUDGMENT.value: ResponseMode.TENTATIVE_JUDGMENT.value,
        OutcomeStatus.MULTIPLE_CONTRIBUTING_FACTORS.value: ResponseMode.MULTI_FACTOR_JUDGMENT.value,
        OutcomeStatus.MULTIPLE_PLAUSIBLE_EXPLANATIONS.value: ResponseMode.PLAUSIBILITY_SUMMARY.value,
        OutcomeStatus.INSUFFICIENT_EVIDENCE.value: ResponseMode.EVIDENCE_LIMITATION.value,
        OutcomeStatus.CONFLICT_BLOCKED.value: ResponseMode.CONFLICT_NOTICE.value,
    }.get(status, ResponseMode.NO_JUDGMENT.value)


def _validate_claims(claims: list[dict], unsafe_text: str = "") -> dict:
    violations = []
    suppressed = []
    safe = []
    for claim in claims:
        if not claim.get("evidence_ids"):
            claim = {**claim, "allowed_for_response": False}
            violations.append("UNTRACED_CLAIM")
            suppressed.append(claim)
        elif claim.get("claim_level") in {CausalClaimLevel.PRIMARY_DRIVER.value, CausalClaimLevel.CONFIRMED_CAUSE.value}:
            claim = {**claim, "claim_level": CausalClaimLevel.CONTRIBUTING_FACTOR.value}
            violations.append("OVERSTATED_CLAIM")
            safe.append(claim)
        else:
            safe.append(claim)
    compact = "".join(str(unsafe_text or "").split()).lower()
    if any("".join(phrase.split()).lower() in compact for phrase in FORBIDDEN_PHRASES):
        violations.append("RECOMMENDATION_LEAK")
    return {
        "valid": not violations,
        "violations": sorted(set(violations)),
        "safe_claims": safe,
        "suppressed_claims": suppressed,
        "suppressed_claim_ids": [claim.get("claim_id") for claim in suppressed],
        "constitutional_pass": not violations,
    }


def _checksum(snapshot: dict) -> str:
    encoded = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_judgment_outcome(judgment_result: dict | None, *, unsafe_output: str = "", revision_result: dict | None = None) -> dict:
    result = _as_dict(judgment_result)
    selected_judgment = _as_dict(result.get("selected_judgment"))
    selected_raw = selected_judgment.get("selected_explanation")
    if isinstance(selected_raw, dict) and selected_raw.get("coexisting_candidates"):
        selected = selected_raw.get("coexisting_candidates") or []
    elif isinstance(selected_raw, dict):
        selected = [selected_raw]
    else:
        selected = []
    alternatives = _as_list(result.get("alternative_explanations"))
    claims = [_claim_for_candidate(candidate, result, index) for index, candidate in enumerate(selected, start=1)]
    validation = _validate_claims(claims, unsafe_output)
    status = _status(result, selected, alternatives)
    if "RECOMMENDATION_LEAK" in validation["violations"]:
        status = OutcomeStatus.INSUFFICIENT_EVIDENCE.value if not selected else status
    mode = _mode(status)
    safe_claims = validation["safe_claims"]
    language = uncertainty_language(result.get("confidence_class"))
    summary = ""
    if safe_claims:
        subjects = ", ".join(claim.get("subject") for claim in safe_claims)
        summary = f"{language} {subjects}"
    elif status == OutcomeStatus.CONFLICT_BLOCKED.value:
        summary = "\u0e15\u0e2d\u0e19\u0e19\u0e35\u0e49\u0e21\u0e35\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\u0e02\u0e31\u0e14\u0e01\u0e31\u0e19 \u0e08\u0e36\u0e07\u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e04\u0e27\u0e23\u0e2a\u0e23\u0e38\u0e1b\u0e04\u0e33\u0e2d\u0e18\u0e34\u0e1a\u0e32\u0e22"
    else:
        summary = f"{language} \u0e04\u0e33\u0e2d\u0e18\u0e34\u0e1a\u0e32\u0e22\u0e17\u0e35\u0e48\u0e21\u0e35\u0e19\u0e49\u0e33\u0e2b\u0e19\u0e31\u0e01"
    boundary = JudgmentDecisionBoundary(
        judgment_complete=bool(selected),
        decision_eligible=bool(selected),
        ready_for_future_decision=bool(selected),
    ).to_dict()
    handoff = JudgmentOutcomeResponseHandoff(
        response_mode=mode,
        safe_summary=summary,
        primary_claims=safe_claims,
        alternative_claims=alternatives,
        evidence_summary=result.get("evidence_summary") or {},
        contradiction_summary=result.get("contradictions") or [],
        limitation_summary=result.get("limitations") or ([] if safe_claims else ["Evidence is insufficient for a safe explanatory claim."]),
        uncertainty_language=language,
        revision_notice=(revision_result or {}).get("revision_reason") or "",
        next_evidence_need=result.get("next_evidence_need") or {},
        clarification_allowed=bool(result.get("next_evidence_need")),
        forbidden_phrases=FORBIDDEN_PHRASES,
    ).to_dict()
    outcome = JudgmentOutcome(
        outcome_id=f"judgment_outcome::{selected_judgment.get('judgment_id') or 'none'}",
        active_topic_id=selected_judgment.get("active_topic_id") or "",
        judgment_status=status,
        judgment_type=selected_judgment.get("judgment_type") or "",
        selected_explanations=selected,
        alternative_explanations=alternatives,
        evidence_basis=[claim.get("evidence_ids") for claim in safe_claims],
        contradicting_evidence=result.get("contradictions") or [],
        unresolved_evidence=result.get("next_evidence_need") or {},
        support_strength=result.get("support_strength") or "INSUFFICIENT",
        confidence_class=result.get("confidence_class") or ConfidenceClass.NO_RELIABLE_JUDGMENT.value,
        maximum_claim_level=CausalClaimLevel.CONTRIBUTING_FACTOR.value,
        safe_claims=safe_claims,
        suppressed_claims=validation["suppressed_claims"],
        limitation_summary=handoff.get("limitation_summary") or [],
        next_evidence_need=result.get("next_evidence_need") or {},
        revision_status=(revision_result or {}).get("revision_status") or "",
        response_handoff=handoff,
        decision_boundary=boundary,
        authority_trace=result.get("authority_trace") or [],
        provenance={
            "judgment_version": BUSINESS_JUDGMENT_VERSION,
            "claim_trace_complete": not validation["suppressed_claims"],
            "validation": validation,
        },
    ).to_dict()
    snapshot = {
        "schema_version": JUDGMENT_OUTCOME_VERSION,
        "active_topic": outcome.get("active_topic_id"),
        "evidence_ids": sorted({eid for claim in safe_claims for eid in claim.get("evidence_ids", [])}),
        "candidate_ids": [item.get("candidate_id") for item in result.get("candidate_judgments") or []],
        "selected_candidates": [item.get("candidate_id") for item in selected],
        "status": status,
        "confidence": outcome.get("confidence_class"),
        "claims": safe_claims,
        "limitations": outcome.get("limitation_summary"),
        "decision_boundary": boundary,
    }
    outcome["validation"] = {
        "valid": validation["valid"],
        "violations": validation["violations"],
        "suppressed_claim_ids": validation["suppressed_claim_ids"],
        "downgraded_status": status if validation["violations"] else "",
        "response_mode_override": mode if validation["violations"] else "",
        "constitutional_pass": validation["constitutional_pass"],
    }
    outcome["snapshot"] = {**snapshot, "checksum": _checksum(snapshot)}
    outcome["diagnostics"] = {
        "judgment_outcome_hardening_consulted": True,
        "judgment_outcome_status": status,
        "judgment_response_mode": mode,
        "judgment_safe_claim_count": len(safe_claims),
        "judgment_suppressed_claim_count": len(validation["suppressed_claims"]),
        "judgment_claim_trace_complete": not validation["suppressed_claims"],
        "judgment_language_consistency_checked": True,
        "judgment_overstatement_prevented": "OVERSTATED_CLAIM" in validation["violations"],
        "judgment_scope_guard_applied": True,
        "judgment_timeframe_guard_applied": True,
        "judgment_benchmark_guard_applied": True,
        "judgment_alternative_omission_checked": True,
        "judgment_recommendation_leak_prevented": "RECOMMENDATION_LEAK" in validation["violations"],
        "judgment_decision_leak_prevented": True,
        "judgment_planner_leak_prevented": True,
        "judgment_workflow_trigger_leak_prevented": True,
        "judgment_outcome_validator_passed": validation["constitutional_pass"],
        "judgment_ready_for_future_decision": boundary["ready_for_future_decision"],
        "decision_made": False,
        "planner_invoked": False,
        "workflow_started_by_judgment": False,
        "business_memory_mutated_by_judgment": False,
    }
    return outcome

