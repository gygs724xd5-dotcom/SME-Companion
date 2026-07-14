"""Pure current-state production admission boundary.

This module consumes one immutable V5.15.24.7.2 evidence artifact and makes a
deterministic governance decision.  It has no runtime or execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
import hashlib
import json
import re
from typing import Any

from brain.production_feature_gate_owner import (
    GATE_MISSING_DEFAULT_DENY,
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_SOURCE_IDENTITY,
)
from brain.production_single_skill_admission_evidence import (
    PRODUCTION_SINGLE_SKILL_ADMISSION_EVIDENCE_SCOPE,
    PRODUCTION_SINGLE_SKILL_ADMISSION_EVIDENCE_VERSION,
    ProductionSingleSkillAdmissionEvidence,
    verify_production_single_skill_admission_evidence,
)

PRODUCTION_DEFAULT_DENIED_ADMISSION_BOUNDARY_VERSION = "5.15.24.7.3"
PRODUCTION_DEFAULT_DENIED_ADMISSION_BOUNDARY_SCOPE = (
    "CURRENT_DEFAULT_DENIED_PRODUCTION_SINGLE_SKILL_ADMISSION_BOUNDARY")

DENIED_DEFAULT_PRODUCTION_GATE = "DENIED_DEFAULT_PRODUCTION_GATE"
DENIED_MALFORMED_REQUEST = "DENIED_MALFORMED_REQUEST"
DENIED_INVALID_PRODUCTION_EVIDENCE = "DENIED_INVALID_PRODUCTION_EVIDENCE"
DENIED_SKILL_IDENTITY_MISMATCH = "DENIED_SKILL_IDENTITY_MISMATCH"
DENIED_OUT_OF_SCOPE_GATE_STATE = "DENIED_OUT_OF_SCOPE_GATE_STATE"
DENIED_AUTHORITY_BOUNDARY = "DENIED_AUTHORITY_BOUNDARY"

PRODUCTION_FEATURE_GATE_DEFAULT_DENIED = "PRODUCTION_FEATURE_GATE_DEFAULT_DENIED"
MALFORMED_PRODUCTION_ADMISSION_REQUEST = "MALFORMED_PRODUCTION_ADMISSION_REQUEST"
INVALID_PRODUCTION_ADMISSION_EVIDENCE = "INVALID_PRODUCTION_ADMISSION_EVIDENCE"
PRODUCTION_SKILL_IDENTITY_MISMATCH = "PRODUCTION_SKILL_IDENTITY_MISMATCH"
PRODUCTION_GATE_STATE_OUT_OF_SCOPE = "PRODUCTION_GATE_STATE_OUT_OF_SCOPE"
PRODUCTION_AUTHORITY_BOUNDARY_VIOLATION = "PRODUCTION_AUTHORITY_BOUNDARY_VIOLATION"

GATE_ORDER = (
    "REQUEST_IDENTITY", "REQUEST_SCOPE", "EVIDENCE_VERSION", "EVIDENCE_INTEGRITY",
    "TURN_IDENTITY", "REFERENCE_TIME", "SELECTED_SKILL_IDENTITY",
    "PRODUCTION_LINEAGE", "FEATURE_GATE_IDENTITY", "DEFAULT_DENY_GATE_STATE",
    "SINGLE_SKILL_CARDINALITY", "SUBSTITUTION_RESISTANCE", "AUTHORITY_BOUNDARY",
    "ADMISSION_ISOLATION",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")
_SKILLS = ("cost.change_analysis.v1", "cost.per_unit_calculation.v1")


@dataclass(frozen=True)
class ProductionAdmissionBoundaryAuthorityBoundary:
    admission: bool = False
    activation: bool = False
    execution: bool = False
    delivery: bool = False
    runtime: bool = False
    routing: bool = False
    planning: bool = False
    selection: bool = False
    commit: bool = False
    persistence: bool = False
    tool_execution: bool = False
    feature_gate_mutation: bool = False


@dataclass(frozen=True)
class ProductionAdmissionBoundaryGateResult:
    gate: str
    satisfied: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ProductionAdmissionBoundaryRequest:
    version: str
    scope: str
    evidence: ProductionSingleSkillAdmissionEvidence
    selected_skill_id: str
    evidence_id: str
    evidence_digest: str
    request_id: str = ""
    request_digest: str = ""


@dataclass(frozen=True)
class ProductionAdmissionBoundaryDecision:
    version: str
    scope: str
    request_id: str
    request_digest: str
    evidence_id: str
    evidence_digest: str
    conversation_id: str
    turn_id: str
    turn_ordinal: int
    turn_digest: str
    reference_time_digest: str
    accepted_at_iso: str
    selected_skill_id: str
    feature_gate_name: str
    feature_gate_evaluation_digest: str
    configured_state: bool
    effective_state: bool
    default_denied: bool
    request_verified: bool
    evidence_verified: bool
    lineage_verified: bool
    gate_results: tuple[ProductionAdmissionBoundaryGateResult, ...]
    decision_status: str
    admitted: bool
    admission_input_ready: bool
    executable_output: None
    denial_code: str
    denial_reason: str
    reasons: tuple[str, ...]
    diagnostics: tuple[str, ...]
    authority_boundary: ProductionAdmissionBoundaryAuthorityBoundary
    decision_digest: str = ""


def _sha(label: str, material: Any) -> str:
    return hashlib.sha256(json.dumps(
        (label, material), ensure_ascii=False, allow_nan=False,
        separators=(",", ":")).encode("utf-8")).hexdigest()


def _request_material(value: ProductionAdmissionBoundaryRequest) -> tuple[Any, ...]:
    return (value.version, value.scope, value.evidence_id, value.evidence_digest,
            value.selected_skill_id)


def _decision_material(value: ProductionAdmissionBoundaryDecision) -> tuple[Any, ...]:
    material = []
    for field in fields(value):
        if field.name == "decision_digest":
            continue
        item = getattr(value, field.name)
        if type(item) is ProductionAdmissionBoundaryAuthorityBoundary:
            item = tuple(getattr(item, name) for name in item.__dataclass_fields__)
        elif field.name == "gate_results":
            item = tuple((gate.gate, gate.satisfied, gate.reason_codes) for gate in item)
        material.append(item)
    return tuple(material)


def _digest(value: Any) -> bool:
    return type(value) is str and _HEX.fullmatch(value) is not None


def create_production_admission_boundary_request(
    evidence: Any, selected_skill_id: Any,
) -> ProductionAdmissionBoundaryRequest | None:
    """Create an exact request; all identities and digests are derived here."""
    try:
        if (type(evidence) is not ProductionSingleSkillAdmissionEvidence
                or not verify_production_single_skill_admission_evidence(evidence)
                or type(selected_skill_id) is not str
                or selected_skill_id not in _SKILLS
                or selected_skill_id != evidence.selected_skill_id):
            return None
        draft = ProductionAdmissionBoundaryRequest(
            PRODUCTION_DEFAULT_DENIED_ADMISSION_BOUNDARY_VERSION,
            PRODUCTION_DEFAULT_DENIED_ADMISSION_BOUNDARY_SCOPE,
            evidence, selected_skill_id, evidence.evidence_id, evidence.evidence_digest)
        request_digest = _sha("PRODUCTION_ADMISSION_BOUNDARY_REQUEST", _request_material(draft))
        request_id = "production-admission-boundary-request-" + _sha(
            "PRODUCTION_ADMISSION_BOUNDARY_REQUEST_ID", _request_material(draft))
        return replace(draft, request_id=request_id, request_digest=request_digest)
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_production_admission_boundary_request(value: Any) -> bool:
    try:
        if (type(value) is not ProductionAdmissionBoundaryRequest
                or not _digest(value.evidence_digest) or not _digest(value.request_digest)):
            return False
        expected = create_production_admission_boundary_request(
            value.evidence, value.selected_skill_id)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def _checks(request: ProductionAdmissionBoundaryRequest) -> tuple[ProductionAdmissionBoundaryGateResult, ...]:
    e = request.evidence
    expected_request_digest = _sha(
        "PRODUCTION_ADMISSION_BOUNDARY_REQUEST", _request_material(request))
    expected_request_id = "production-admission-boundary-request-" + _sha(
        "PRODUCTION_ADMISSION_BOUNDARY_REQUEST_ID", _request_material(request))
    exact_request_identity = (_digest(request.request_digest)
                              and request.request_digest == expected_request_digest
                              and request.request_id == expected_request_id)
    evidence_type = type(e) is ProductionSingleSkillAdmissionEvidence
    evidence_valid = evidence_type and verify_production_single_skill_admission_evidence(e)
    def gate(name: str, passed: bool) -> ProductionAdmissionBoundaryGateResult:
        return ProductionAdmissionBoundaryGateResult(
            name, bool(passed), ("SATISFIED",) if passed else (name + "_DENIED",))
    safe = lambda name, default=None: getattr(e, name, default)
    source = safe("source")
    feature = getattr(source, "feature_gate_evaluation", None)
    authority = safe("authority_boundary")
    authority_ok = authority is not None and all(
        getattr(authority, name, None) is False for name in authority.__dataclass_fields__)
    return (
        gate(GATE_ORDER[0], exact_request_identity),
        gate(GATE_ORDER[1], request.version == PRODUCTION_DEFAULT_DENIED_ADMISSION_BOUNDARY_VERSION
             and request.scope == PRODUCTION_DEFAULT_DENIED_ADMISSION_BOUNDARY_SCOPE),
        gate(GATE_ORDER[2], evidence_type and safe("version") == PRODUCTION_SINGLE_SKILL_ADMISSION_EVIDENCE_VERSION
             and safe("scope") == PRODUCTION_SINGLE_SKILL_ADMISSION_EVIDENCE_SCOPE),
        gate(GATE_ORDER[3], evidence_valid),
        gate(GATE_ORDER[4], evidence_type and bool(safe("conversation_id")) and bool(safe("turn_id"))
             and _digest(safe("turn_digest"))),
        gate(GATE_ORDER[5], evidence_type and _digest(safe("reference_time_digest"))
             and bool(safe("accepted_at_iso")) and safe("accepted_at_iso") == safe("delivery_reference_time")),
        gate(GATE_ORDER[6], type(request.selected_skill_id) is str
             and request.selected_skill_id in _SKILLS and request.selected_skill_id == safe("selected_skill_id")),
        gate(GATE_ORDER[7], evidence_valid and safe("lineage_verified") is True
             and safe("evidence_complete") is True and safe("governance_evidence_verified") is True),
        gate(GATE_ORDER[8], feature is not None
             and safe("feature_gate_name") == LIMITED_COST_RESPONSE_RUNTIME_BRIDGE
             and safe("feature_gate_evaluation_digest") == getattr(feature, "evaluation_digest", None)
             and getattr(feature, "source_identity", None) == PRODUCTION_DEFAULT_DENY_SOURCE_IDENTITY
             and getattr(feature, "evaluation_reason", None) == GATE_MISSING_DEFAULT_DENY),
        # This is the actual admission gate.  Exact current state intentionally
        # does not satisfy it, producing the canonical default-denied decision.
        gate(GATE_ORDER[9], False),
        gate(GATE_ORDER[10], safe("selected_skill_id") in _SKILLS),
        gate(GATE_ORDER[11], request.evidence_id == safe("evidence_id")
             and request.evidence_digest == safe("evidence_digest")
             and request.selected_skill_id == safe("selected_skill_id")),
        gate(GATE_ORDER[12], authority_ok),
        gate(GATE_ORDER[13], safe("admission_input_ready") is False
             and safe("admitted") is False and safe("executable_output") is None
             and safe("runtime_invoked") is False and safe("bridge_invoked") is False),
    )


def _outcome(checks: tuple[ProductionAdmissionBoundaryGateResult, ...]):
    first = next((item.gate for item in checks if not item.satisfied), None)
    if first == "DEFAULT_DENY_GATE_STATE" or first is None:
        return (DENIED_DEFAULT_PRODUCTION_GATE, PRODUCTION_FEATURE_GATE_DEFAULT_DENIED,
                "CURRENT_PRODUCTION_FEATURE_GATE_IS_DEFAULT_DENIED")
    if first in ("REQUEST_IDENTITY", "REQUEST_SCOPE"):
        return (DENIED_MALFORMED_REQUEST, MALFORMED_PRODUCTION_ADMISSION_REQUEST,
                "REQUEST_IS_NOT_EXACT_CURRENT_BOUNDARY_INPUT")
    if first in ("EVIDENCE_VERSION", "EVIDENCE_INTEGRITY", "TURN_IDENTITY",
                 "REFERENCE_TIME", "PRODUCTION_LINEAGE"):
        return (DENIED_INVALID_PRODUCTION_EVIDENCE, INVALID_PRODUCTION_ADMISSION_EVIDENCE,
                "PRODUCTION_EVIDENCE_IS_NOT_CANONICAL")
    if first in ("SELECTED_SKILL_IDENTITY", "SINGLE_SKILL_CARDINALITY", "SUBSTITUTION_RESISTANCE"):
        return (DENIED_SKILL_IDENTITY_MISMATCH, PRODUCTION_SKILL_IDENTITY_MISMATCH,
                "SELECTED_SKILL_IDENTITY_DOES_NOT_MATCH_EVIDENCE")
    if first in ("FEATURE_GATE_IDENTITY",):
        return (DENIED_OUT_OF_SCOPE_GATE_STATE, PRODUCTION_GATE_STATE_OUT_OF_SCOPE,
                "FEATURE_GATE_EVIDENCE_IS_OUT_OF_CURRENT_DEFAULT_DENY_SCOPE")
    if first == "AUTHORITY_BOUNDARY":
        return (DENIED_AUTHORITY_BOUNDARY, PRODUCTION_AUTHORITY_BOUNDARY_VIOLATION,
                "PRODUCTION_AUTHORITY_BOUNDARY_MUST_REMAIN_FALSE")
    return (DENIED_MALFORMED_REQUEST, MALFORMED_PRODUCTION_ADMISSION_REQUEST,
            "ADMISSION_BOUNDARY_FAILED_CLOSED")


def evaluate_default_denied_production_admission(
    request: Any,
) -> ProductionAdmissionBoundaryDecision | None:
    """Evaluate only an immutable request; never produce executable output."""
    try:
        if type(request) is not ProductionAdmissionBoundaryRequest:
            return None
        e = request.evidence
        if type(e) is not ProductionSingleSkillAdmissionEvidence:
            return None
        checks = _checks(request)
        status, code, reason = _outcome(checks)
        verified = verify_production_admission_boundary_request(request)
        evidence_verified = verify_production_single_skill_admission_evidence(e)
        draft = ProductionAdmissionBoundaryDecision(
            PRODUCTION_DEFAULT_DENIED_ADMISSION_BOUNDARY_VERSION,
            PRODUCTION_DEFAULT_DENIED_ADMISSION_BOUNDARY_SCOPE,
            request.request_id, request.request_digest, request.evidence_id,
            request.evidence_digest, e.conversation_id, e.turn_id, e.turn_ordinal,
            e.turn_digest, e.reference_time_digest, e.accepted_at_iso,
            request.selected_skill_id, e.feature_gate_name,
            e.feature_gate_evaluation_digest, e.configured_state, e.effective_state,
            e.default_denied, verified, evidence_verified,
            evidence_verified and e.lineage_verified, checks, status, False, False,
            None, code, reason, (code,),
            ("FIRST_FAILED_GATE:" + next(x.gate for x in checks if not x.satisfied),
             "PURE_BOUNDARY_EVALUATION", "NO_EXECUTABLE_AUTHORITY"),
            ProductionAdmissionBoundaryAuthorityBoundary())
        return replace(draft, decision_digest=_sha(
            "PRODUCTION_ADMISSION_BOUNDARY_DECISION", _decision_material(draft)))
    except (AttributeError, TypeError, ValueError, StopIteration, UnicodeEncodeError):
        return None


def verify_production_admission_boundary_decision(
    request: Any, decision: Any,
) -> bool:
    """Recompute the pure boundary evaluation and compare the complete decision."""
    try:
        if (type(request) is not ProductionAdmissionBoundaryRequest
                or type(decision) is not ProductionAdmissionBoundaryDecision
                or not _digest(decision.decision_digest)):
            return False
        expected = evaluate_default_denied_production_admission(request)
        return expected is not None and decision == expected and decision.decision_digest == _sha(
            "PRODUCTION_ADMISSION_BOUNDARY_DECISION", _decision_material(decision))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


__all__ = tuple(name for name in globals() if name.startswith("PRODUCTION_") or name.startswith("DENIED_") or name in (
    "GATE_ORDER", "ProductionAdmissionBoundaryAuthorityBoundary",
    "ProductionAdmissionBoundaryGateResult", "ProductionAdmissionBoundaryRequest",
    "ProductionAdmissionBoundaryDecision", "create_production_admission_boundary_request",
    "evaluate_default_denied_production_admission",
    "verify_production_admission_boundary_request",
    "verify_production_admission_boundary_decision"))
