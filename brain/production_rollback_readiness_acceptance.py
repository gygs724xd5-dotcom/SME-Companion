"""V5.15.24.7.4.18 passive production rollback-readiness acceptance.

Acceptance is derived only from the exact V5.15.24.7.4.17 foundation.  It is
not deployment attestation, transition approval, activation, or rollback.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from typing import Any, Mapping

from brain.production_rollback_evidence_foundation import (
    IN_FLIGHT_POLICY,
    ROLLBACK_ARTIFACT_KIND,
    VERIFICATION_REQUIREMENTS,
    ProductionRollbackEvidenceFoundation,
    verify_production_rollback_evidence_foundation,
)

VERSION = "5.15.24.7.4.18"
SCOPE = "PRODUCTION_ROLLBACK_READINESS_ACCEPTANCE"
ACCEPTED = "ROLLBACK_READINESS_ACCEPTED"
REJECTED = "ROLLBACK_READINESS_REJECTED"
CHECK_ORDER = (
    "EXACT_FOUNDATION_VERIFIED",
    "EXACT_PROPOSAL_REVISION_BOUND",
    "EXACT_FEATURE_GATE_BOUND",
    "ROLLBACK_TARGET_VERIFIED",
    "ROLLBACK_ARTIFACT_VERIFIED",
    "ROLLBACK_CONFIGURATION_VERIFIED",
    "DEFAULT_DENY_RESTORATION_VERIFIED",
    "IN_FLIGHT_CONTAINMENT_VERIFIED",
    "FAILURE_CONTAINMENT_LINEAGE_VERIFIED",
    "VERIFICATION_REQUIREMENTS_VERIFIED",
    "AUTHORITY_AND_EXECUTION_ABSENT",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionRollbackReadinessAuthorityBoundary:
    approval: bool = False
    transition: bool = False
    activation: bool = False
    mutation: bool = False
    deployment: bool = False
    rollback_execution: bool = False
    runtime: bool = False
    dispatch: bool = False
    delivery: bool = False
    persistence: bool = False


@dataclass(frozen=True)
class ProductionRollbackReadinessCheck:
    check_id: str
    ordinal: int
    evidence_digests: tuple[str, ...]
    verified: bool
    reason: str
    check_digest: str = ""


@dataclass(frozen=True)
class ProductionRollbackReadinessAcceptance:
    version: str
    scope: str
    foundation: ProductionRollbackEvidenceFoundation
    foundation_digest: str
    release_owner_digest: str
    release_revision_id: str
    release_revision_digest: str
    proposal_digest: str
    feature_gate_identity: str
    requested_target_state: bool
    rollback_target_identity: str
    rollback_target_digest: str
    rollback_artifact_identity: str
    rollback_artifact_digest: str
    rollback_configuration_identity: str
    rollback_configuration_digest: str
    containment_report_digest: str
    containment_topology_digest: str
    checks: tuple[ProductionRollbackReadinessCheck, ...]
    issues: tuple[str, ...]
    status: str
    accepted: bool
    readiness_evidence_permitted: bool
    deployment_attested: bool = False
    rollback_executed: bool = False
    transition_approved: bool = False
    activation_permitted: bool = False
    mutation_permitted: bool = False
    executable_output: None = None
    authority_boundary: ProductionRollbackReadinessAuthorityBoundary = (
        ProductionRollbackReadinessAuthorityBoundary()
    )
    topology_digest: str = ""
    acceptance_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, Mapping):
        return [[str(key), _canonical(value[key])] for key in sorted(value)]
    if is_dataclass(value) and not isinstance(value, type):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported rollback-readiness material")


def _digest(label: str, value: Any) -> str:
    encoded = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any, *excluded: str) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value)
        if field.name not in excluded)


def _all_false(value: Any) -> bool:
    return type(value) is ProductionRollbackReadinessAuthorityBoundary and all(
        type(getattr(value, field.name)) is bool and not getattr(value, field.name)
        for field in fields(value))


def _check(identifier: str, ordinal: int, evidence: tuple[str, ...], reason: str):
    draft = ProductionRollbackReadinessCheck(identifier, ordinal, evidence, True, reason)
    return replace(draft, check_digest=_digest(
        "READINESS_CHECK", _material(draft, "check_digest")))


def _checks(value: ProductionRollbackEvidenceFoundation):
    material = (
        ((value.foundation_digest,), "exact canonical rollback evidence foundation verified"),
        ((value.proposal_digest, value.release_revision_digest), "proposal and release revision exactly bound"),
        ((value.proposal_digest,), "requested production feature gate exactly bound"),
        ((value.rollback_target_digest,), "canonical rollback target verified"),
        ((value.rollback_artifact_digest,), "source-controlled rollback artifact digest verified"),
        ((value.rollback_configuration_digest,), "default-deny rollback configuration verified"),
        ((value.rollback_configuration_digest,), "empty default-deny restoration represented"),
        ((value.containment_report_digest,), "in-flight denial and response suppression represented"),
        ((value.containment_report_digest, value.containment_topology_digest),
            "accepted failure-containment lineage verified"),
        ((value.foundation_digest,), "ordered rollback verification requirements verified"),
        ((value.foundation_digest,), "approval activation mutation deployment and execution remain absent"),
    )
    return tuple(_check(identifier, index + 1, material[index][0], material[index][1])
        for index, identifier in enumerate(CHECK_ORDER))


def _foundation_semantics(value: ProductionRollbackEvidenceFoundation) -> bool:
    return (
        verify_production_rollback_evidence_foundation(value)
        and value.rollback_artifact_kind == ROLLBACK_ARTIFACT_KIND
        and value.requested_target_state is True
        and value.rollback_entries == ()
        and value.default_deny_restoration is True
        and value.in_flight_policy == IN_FLIGHT_POLICY
        and value.verification_requirements == VERIFICATION_REQUIREMENTS
        and len(value.evidence_lineage) == 7
        and value.evidence_lineage[2] == value.proposal_digest
        and value.evidence_lineage[3] == value.rollback_target_digest
        and value.evidence_lineage[4] == value.rollback_artifact_digest
        and value.evidence_lineage[5:] == (
            value.containment_report_digest, value.containment_topology_digest)
        and not any((value.rollback_attested, value.deployment_attested,
            value.readiness_accepted, value.approval_evidence_permitted,
            value.activation_permitted, value.mutation_permitted,
            value.rollback_executed))
        and value.executable_output is None
    )


def _build(value: ProductionRollbackEvidenceFoundation):
    checks = _checks(value)
    topology = _digest("READINESS_TOPOLOGY", (
        value.foundation_digest, tuple(item.check_digest for item in checks),
        value.evidence_lineage))
    draft = ProductionRollbackReadinessAcceptance(
        VERSION, SCOPE, value, value.foundation_digest, value.release_owner_digest,
        value.release_revision_id, value.release_revision_digest, value.proposal_digest,
        value.feature_gate_identity, value.requested_target_state,
        value.rollback_target_identity, value.rollback_target_digest,
        value.rollback_artifact_identity, value.rollback_artifact_digest,
        value.rollback_configuration_identity, value.rollback_configuration_digest,
        value.containment_report_digest, value.containment_topology_digest,
        checks, (), ACCEPTED, True, True, topology_digest=topology)
    return replace(draft, acceptance_digest=_digest(
        "READINESS_ACCEPTANCE", _material(draft, "acceptance_digest")))


def evaluate_production_rollback_readiness(
    evidence_foundation: Any,
) -> ProductionRollbackReadinessAcceptance | None:
    """Accept only exact evidence; malformed or incomplete input fails closed."""
    try:
        if type(evidence_foundation) is not ProductionRollbackEvidenceFoundation:
            return None
        if not _foundation_semantics(evidence_foundation):
            return None
        return _build(evidence_foundation)
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def classify_production_rollback_readiness(evidence_foundation: Any) -> str:
    """Return an explicit fail-closed status without accepting caller outcomes."""
    return ACCEPTED if evaluate_production_rollback_readiness(
        evidence_foundation) is not None else REJECTED


def verify_production_rollback_readiness_check(value: Any) -> bool:
    try:
        return (
            type(value) is ProductionRollbackReadinessCheck
            and value.check_id in CHECK_ORDER
            and value.ordinal == CHECK_ORDER.index(value.check_id) + 1
            and value.verified is True
            and bool(value.reason)
            and bool(value.evidence_digests)
            and all(_HEX.fullmatch(item or "") for item in value.evidence_digests)
            and _HEX.fullmatch(value.check_digest or "") is not None
            and value.check_digest == _digest(
                "READINESS_CHECK", _material(value, "check_digest"))
        )
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def verify_production_rollback_readiness_acceptance(value: Any) -> bool:
    try:
        if type(value) is not ProductionRollbackReadinessAcceptance:
            return False
        if not _all_false(value.authority_boundary):
            return False
        if any((value.deployment_attested, value.rollback_executed,
                value.transition_approved, value.activation_permitted,
                value.mutation_permitted)):
            return False
        if value.executable_output is not None:
            return False
        if value.status != ACCEPTED or value.accepted is not True:
            return False
        if value.readiness_evidence_permitted is not True or value.issues != ():
            return False
        if tuple(item.check_id for item in value.checks) != CHECK_ORDER:
            return False
        if not all(verify_production_rollback_readiness_check(item) for item in value.checks):
            return False
        expected = evaluate_production_rollback_readiness(value.foundation)
        return expected is not None and value == expected and bool(
            _HEX.fullmatch(value.topology_digest or "")) and bool(
            _HEX.fullmatch(value.acceptance_digest or "")) and value.acceptance_digest == _digest(
                "READINESS_ACCEPTANCE", _material(value, "acceptance_digest"))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


__all__ = (
    "VERSION", "SCOPE", "ACCEPTED", "REJECTED", "CHECK_ORDER",
    "ProductionRollbackReadinessAuthorityBoundary",
    "ProductionRollbackReadinessCheck", "ProductionRollbackReadinessAcceptance",
    "evaluate_production_rollback_readiness", "classify_production_rollback_readiness",
    "verify_production_rollback_readiness_check",
    "verify_production_rollback_readiness_acceptance",
)
