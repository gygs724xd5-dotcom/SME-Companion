"""V5.15.24.7.4.24 passive operational failure-containment evidence acceptance.

Acceptance means that one canonical, immutable evidence foundation satisfies
the evidence policy.  It does not claim an incident, perform containment, or
grant approval, activation, deployment, rollback, or runtime authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from typing import Any, Mapping

from brain.operational_failure_containment_evidence_foundation import (
    BOUNDARY_FIELDS as FOUNDATION_BOUNDARY_FIELDS,
    CHECK_ORDER as FOUNDATION_CHECK_ORDER,
    FOUNDATION_PREPARED,
    VERSION as FOUNDATION_VERSION,
    OperationalFailureContainmentEvidenceFoundation,
    verify_operational_failure_containment_evidence_foundation,
    verify_operational_failure_containment_evidence_policy,
    verify_operational_failure_incident_identity,
)

VERSION = "5.15.24.7.4.24"
SCOPE = "OPERATIONAL_FAILURE_CONTAINMENT_EVIDENCE_ACCEPTANCE"
ACCEPTED = "OPERATIONAL_FAILURE_CONTAINMENT_EVIDENCE_ACCEPTED"
REJECTED = "OPERATIONAL_FAILURE_CONTAINMENT_EVIDENCE_REJECTED"
POLICY_IDENTITY = "operational-failure-containment-evidence-acceptance-policy"
POLICY_VERSION = "1"
CHECK_ORDER = (
    "EVIDENCE_FOUNDATION_TYPE_VERIFIED",
    "EVIDENCE_FOUNDATION_VERSION_VERIFIED",
    "EVIDENCE_FOUNDATION_STATUS_PREPARED",
    "EVIDENCE_FOUNDATION_DIGEST_VERIFIED",
    "EVIDENCE_FOUNDATION_POLICY_VERIFIED",
    "INCIDENT_IDENTITY_VERIFIED",
    "INCIDENT_TYPE_VERIFIED",
    "PROPOSAL_CONTINUITY_VERIFIED",
    "REQUESTED_STATE_CONTINUITY_VERIFIED",
    "REVISION_CONTINUITY_VERIFIED",
    "RUNTIME_CONFIGURATION_CONTINUITY_VERIFIED",
    "FEATURE_GATE_CONTINUITY_VERIFIED",
    "DEPLOYMENT_ARTIFACT_CONTINUITY_VERIFIED",
    "DEPLOYMENT_EVIDENCE_CONTINUITY_VERIFIED",
    "CONTAINMENT_ACCEPTANCE_CONTINUITY_VERIFIED",
    "CONTAINMENT_TOPOLOGY_CONTINUITY_VERIFIED",
    "ORDERED_FOUNDATION_CHECKS_VERIFIED",
    "FOUNDATION_BOUNDARY_INVARIANTS_VERIFIED",
    "INCIDENT_NOT_CLAIMED",
    "CONTAINMENT_NOT_EXECUTED",
    "TRANSITION_NOT_APPROVED",
    "ACTIVATION_NOT_PERMITTED",
    "DEPLOYMENT_NOT_EXECUTED",
    "ROLLBACK_NOT_EXECUTED",
    "RUNTIME_NOT_MUTATED",
    "FEATURE_GATE_NOT_MUTATED",
    "APPROVAL_NOT_PERMITTED",
)
BOUNDARY_FIELDS = (
    "incident_observed", "containment_executed", "transition_approved",
    "activation_permitted", "deployment_executed", "rollback_executed",
    "runtime_mutated", "feature_gate_mutated", "approval_permitted",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class OperationalFailureContainmentEvidenceAcceptancePolicy:
    identity: str
    version: str
    expected_foundation_version: str
    required_foundation_status: str
    required_checks: tuple[str, ...]
    required_false_boundaries: tuple[str, ...]
    policy_digest: str = ""


@dataclass(frozen=True)
class OperationalFailureContainmentEvidenceAcceptanceCheck:
    check_id: str
    ordinal: int
    evidence_digests: tuple[str, ...]
    verified: bool
    reason: str
    check_digest: str = ""


@dataclass(frozen=True)
class OperationalFailureContainmentEvidenceAcceptance:
    version: str
    scope: str
    status: str
    policy: OperationalFailureContainmentEvidenceAcceptancePolicy
    foundation: OperationalFailureContainmentEvidenceFoundation
    policy_identity: str
    policy_version: str
    policy_digest: str
    foundation_digest: str
    foundation_topology_digest: str
    foundation_policy_digest: str
    incident_identity_digest: str
    incident_type: str
    proposal_digest: str
    requested_state: bool
    release_revision_id: str
    release_revision_digest: str
    runtime_configuration_identity: str
    runtime_configuration_digest: str
    feature_gate_identity: str
    feature_gate_state: bool
    deployment_artifact_identity: str
    deployment_artifact_digest: str
    deployment_evidence_digest: str
    failure_containment_acceptance_digest: str
    failure_containment_topology_digest: str
    evidence_digest: str
    checks: tuple[OperationalFailureContainmentEvidenceAcceptanceCheck, ...]
    issues: tuple[str, ...]
    accepted: bool
    incident_observed: bool = False
    containment_executed: bool = False
    transition_approved: bool = False
    activation_permitted: bool = False
    deployment_executed: bool = False
    rollback_executed: bool = False
    runtime_mutated: bool = False
    feature_gate_mutated: bool = False
    approval_permitted: bool = False
    executable_output: None = None
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
    raise ValueError("unsupported operational-containment acceptance material")


def _digest(label: str, value: Any) -> str:
    encoded = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any, *excluded: str) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value)
        if field.name not in excluded)


def _build_policy() -> OperationalFailureContainmentEvidenceAcceptancePolicy:
    draft = OperationalFailureContainmentEvidenceAcceptancePolicy(
        POLICY_IDENTITY, POLICY_VERSION, FOUNDATION_VERSION,
        FOUNDATION_PREPARED, CHECK_ORDER, BOUNDARY_FIELDS)
    return replace(draft, policy_digest=_digest(
        "ACCEPTANCE_POLICY", _material(draft, "policy_digest")))


CANONICAL_ACCEPTANCE_POLICY = _build_policy()


def verify_operational_failure_containment_evidence_acceptance_policy(value: Any) -> bool:
    return (type(value) is OperationalFailureContainmentEvidenceAcceptancePolicy
        and value == CANONICAL_ACCEPTANCE_POLICY
        and bool(_HEX.fullmatch(value.policy_digest or "")))


def _foundation_valid(value: Any) -> bool:
    if type(value) is not OperationalFailureContainmentEvidenceFoundation:
        return False
    if value.version != FOUNDATION_VERSION or value.status != FOUNDATION_PREPARED:
        return False
    if not verify_operational_failure_containment_evidence_foundation(value):
        return False
    if not verify_operational_failure_containment_evidence_policy(value.policy):
        return False
    if not verify_operational_failure_incident_identity(
            value.evidence.incident_identity, value.deployment_evidence):
        return False
    return (tuple(item.check_id for item in value.checks) == FOUNDATION_CHECK_ORDER
        and value.issues == () and value.executable_output is None
        and not any(getattr(value, name) for name in FOUNDATION_BOUNDARY_FIELDS)
        and value.evidence.incident_observed is False
        and value.evidence.containment_executed is False)


def _check(identifier: str, ordinal: int, evidence: tuple[str, ...]):
    draft = OperationalFailureContainmentEvidenceAcceptanceCheck(
        identifier, ordinal, evidence, True,
        identifier.lower().replace("_", " "))
    return replace(draft, check_digest=_digest(
        "ACCEPTANCE_CHECK", _material(draft, "check_digest")))


def _checks(value: OperationalFailureContainmentEvidenceFoundation):
    evidence = value.evidence
    common = value.foundation_digest
    materials = (
        (common,), (common,), (common,), (common,), (value.policy_digest,),
        (value.incident_identity_digest,), (value.incident_identity_digest,),
        (evidence.proposal_digest,), (evidence.proposal_digest,),
        (evidence.release_revision_digest,), (evidence.runtime_configuration_digest,),
        (evidence.proposal_digest,), (evidence.deployment_artifact_digest,),
        (evidence.deployment_evidence_digest,),
        (evidence.failure_containment_acceptance_digest,),
        (evidence.failure_containment_topology_digest,),
        (_digest("ORDERED_FOUNDATION_CHECKS",
            tuple(item.check_digest for item in value.checks)),),
        (common,), (common,), (common,), (common,), (common,), (common,),
        (common,), (common,), (common,), (common,),
    )
    return tuple(_check(identifier, index + 1, materials[index])
        for index, identifier in enumerate(CHECK_ORDER))


def _build(value: OperationalFailureContainmentEvidenceFoundation):
    evidence = value.evidence
    checks = _checks(value)
    topology = _digest("ACCEPTANCE_TOPOLOGY", (
        CANONICAL_ACCEPTANCE_POLICY.policy_digest, value.foundation_digest,
        evidence.evidence_digest, tuple(item.check_digest for item in checks)))
    draft = OperationalFailureContainmentEvidenceAcceptance(
        VERSION, SCOPE, ACCEPTED, CANONICAL_ACCEPTANCE_POLICY, value,
        POLICY_IDENTITY, POLICY_VERSION, CANONICAL_ACCEPTANCE_POLICY.policy_digest,
        value.foundation_digest, value.topology_digest, value.policy_digest,
        value.incident_identity_digest, evidence.incident_identity.incident_type,
        evidence.proposal_digest, evidence.requested_state,
        evidence.release_revision_id, evidence.release_revision_digest,
        evidence.runtime_configuration_identity, evidence.runtime_configuration_digest,
        evidence.feature_gate_identity, evidence.feature_gate_state,
        evidence.deployment_artifact_identity, evidence.deployment_artifact_digest,
        evidence.deployment_evidence_digest,
        evidence.failure_containment_acceptance_digest,
        evidence.failure_containment_topology_digest, evidence.evidence_digest,
        checks, (), True, topology_digest=topology)
    return replace(draft, acceptance_digest=_digest(
        "EVIDENCE_ACCEPTANCE", _material(draft, "acceptance_digest")))


def evaluate_operational_failure_containment_evidence_acceptance(
    evidence_foundation: Any,
) -> OperationalFailureContainmentEvidenceAcceptance | None:
    try:
        if not _foundation_valid(evidence_foundation):
            return None
        return _build(evidence_foundation)
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def classify_operational_failure_containment_evidence_acceptance(
    evidence_foundation: Any,
) -> str:
    return ACCEPTED if evaluate_operational_failure_containment_evidence_acceptance(
        evidence_foundation) is not None else REJECTED


def verify_operational_failure_containment_evidence_acceptance_check(value: Any) -> bool:
    try:
        return (type(value) is OperationalFailureContainmentEvidenceAcceptanceCheck
            and value.check_id in CHECK_ORDER
            and value.ordinal == CHECK_ORDER.index(value.check_id) + 1
            and value.verified is True and bool(value.reason)
            and type(value.evidence_digests) is tuple and bool(value.evidence_digests)
            and all(type(item) is str and bool(_HEX.fullmatch(item))
                for item in value.evidence_digests)
            and bool(_HEX.fullmatch(value.check_digest or ""))
            and value.check_digest == _digest(
                "ACCEPTANCE_CHECK", _material(value, "check_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def verify_operational_failure_containment_evidence_acceptance(value: Any) -> bool:
    try:
        if type(value) is not OperationalFailureContainmentEvidenceAcceptance:
            return False
        if value.version != VERSION or value.scope != SCOPE or value.status != ACCEPTED:
            return False
        if value.accepted is not True or value.issues != ():
            return False
        if not verify_operational_failure_containment_evidence_acceptance_policy(value.policy):
            return False
        if value.policy is not CANONICAL_ACCEPTANCE_POLICY:
            return False
        if any(getattr(value, name) for name in BOUNDARY_FIELDS):
            return False
        if value.executable_output is not None:
            return False
        if type(value.checks) is not tuple or tuple(
                item.check_id for item in value.checks) != CHECK_ORDER:
            return False
        if len(value.checks) != len(CHECK_ORDER) or len(
                {item.check_id for item in value.checks}) != len(CHECK_ORDER):
            return False
        if not all(verify_operational_failure_containment_evidence_acceptance_check(item)
                for item in value.checks):
            return False
        expected = evaluate_operational_failure_containment_evidence_acceptance(
            value.foundation)
        return (expected is not None and value == expected
            and bool(_HEX.fullmatch(value.topology_digest or ""))
            and bool(_HEX.fullmatch(value.acceptance_digest or ""))
            and value.acceptance_digest == _digest(
                "EVIDENCE_ACCEPTANCE", _material(value, "acceptance_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


__all__ = (
    "VERSION", "SCOPE", "ACCEPTED", "REJECTED", "POLICY_IDENTITY",
    "POLICY_VERSION", "CHECK_ORDER", "BOUNDARY_FIELDS",
    "OperationalFailureContainmentEvidenceAcceptancePolicy",
    "OperationalFailureContainmentEvidenceAcceptanceCheck",
    "OperationalFailureContainmentEvidenceAcceptance",
    "CANONICAL_ACCEPTANCE_POLICY",
    "evaluate_operational_failure_containment_evidence_acceptance",
    "classify_operational_failure_containment_evidence_acceptance",
    "verify_operational_failure_containment_evidence_acceptance_policy",
    "verify_operational_failure_containment_evidence_acceptance_check",
    "verify_operational_failure_containment_evidence_acceptance",
)
