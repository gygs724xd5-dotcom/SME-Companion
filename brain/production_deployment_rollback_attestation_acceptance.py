"""V5.15.24.7.4.21 passive attestation-foundation acceptance.

ACCEPTED means the canonical PREPARED foundation satisfies this evidence
acceptance policy.  It is not operational attestation, approval, activation,
deployment, rollback, or runtime authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from typing import Any, Mapping

from brain.production_deployment_rollback_attestation_foundation import (
    CHECK_ORDER as FOUNDATION_CHECK_ORDER,
    PREPARED as FOUNDATION_PREPARED,
    VERSION as FOUNDATION_VERSION,
    ProductionDeploymentRollbackAttestationFoundation,
    verify_production_deployment_rollback_attestation_foundation,
    verify_production_deployment_rollback_attestation_policy,
    verify_production_deployment_rollback_attestation_subject,
)
from brain.production_rollback_readiness_acceptance import (
    ACCEPTED as ROLLBACK_READINESS_ACCEPTED,
)

VERSION = "5.15.24.7.4.21"
SCOPE = "PRODUCTION_DEPLOYMENT_ROLLBACK_ATTESTATION_ACCEPTANCE"
ACCEPTED = "DEPLOYMENT_ROLLBACK_ATTESTATION_ACCEPTED"
REJECTED = "DEPLOYMENT_ROLLBACK_ATTESTATION_REJECTED"
POLICY_IDENTITY = "production-deployment-rollback-attestation-acceptance-policy"
POLICY_VERSION = "1"
CHECK_ORDER = (
    "ATTESTATION_FOUNDATION_TYPE_VERIFIED",
    "ATTESTATION_FOUNDATION_SCHEMA_VERIFIED",
    "ATTESTATION_FOUNDATION_STATUS_PREPARED",
    "ATTESTATION_FOUNDATION_DIGEST_VERIFIED",
    "ATTESTATION_POLICY_VERIFIED",
    "ATTESTATION_SUBJECT_VERIFIED",
    "PROPOSAL_IDENTITY_VERIFIED",
    "REQUESTED_STATE_VERIFIED",
    "PROPOSAL_REVISION_VERIFIED",
    "FEATURE_GATE_IDENTITY_VERIFIED",
    "FEATURE_GATE_REQUESTED_STATE_VERIFIED",
    "RUNTIME_CONFIGURATION_IDENTITY_VERIFIED",
    "RUNTIME_CONFIGURATION_DIGEST_VERIFIED",
    "DEPLOYMENT_ARTIFACT_EVIDENCE_VERIFIED",
    "DEPLOYMENT_ARTIFACT_IDENTITY_VERIFIED",
    "DEPLOYMENT_ARTIFACT_DIGEST_VERIFIED",
    "ROLLBACK_EVIDENCE_VERIFIED",
    "ROLLBACK_ARTIFACT_IDENTITY_VERIFIED",
    "ROLLBACK_ARTIFACT_DIGEST_VERIFIED",
    "ROLLBACK_TARGET_VERIFIED",
    "ROLLBACK_READINESS_ACCEPTANCE_VERIFIED",
    "ROLLBACK_READINESS_STATUS_ACCEPTED",
    "FAILURE_CONTAINMENT_LINEAGE_VERIFIED",
    "DEPLOYMENT_ROLLBACK_PROPOSAL_CROSS_BINDING_VERIFIED",
    "DEPLOYMENT_ROLLBACK_REVISION_CROSS_BINDING_VERIFIED",
    "DEPLOYMENT_ROLLBACK_GATE_CROSS_BINDING_VERIFIED",
    "DEPLOYMENT_ROLLBACK_CONFIGURATION_CROSS_BINDING_VERIFIED",
    "ORDERED_FOUNDATION_CHECKS_VERIFIED",
    "FOUNDATION_BOUNDARY_INVARIANTS_VERIFIED",
    "DEPLOYMENT_NOT_EXECUTED",
    "ROLLBACK_NOT_EXECUTED",
    "FEATURE_GATE_NOT_MUTATED",
    "TRANSITION_NOT_APPROVED",
    "ACTIVATION_NOT_PERMITTED",
    "APPROVAL_NOT_PERMITTED",
    "RUNTIME_NOT_MUTATED",
    "SUCCESSFUL_ATTESTATION_NOT_CLAIMED",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionDeploymentRollbackAttestationAcceptancePolicy:
    identity: str
    version: str
    expected_foundation_version: str
    required_foundation_status: str
    required_checks: tuple[str, ...]
    accepted_upstream_statuses: tuple[str, ...]
    prohibited_operational_fields: tuple[str, ...]
    policy_digest: str = ""


@dataclass(frozen=True)
class ProductionDeploymentRollbackAttestationAcceptanceCheck:
    check_id: str
    ordinal: int
    evidence_digests: tuple[str, ...]
    verified: bool
    reason: str
    check_digest: str = ""


@dataclass(frozen=True)
class ProductionDeploymentRollbackAttestationAcceptance:
    version: str
    scope: str
    status: str
    policy: ProductionDeploymentRollbackAttestationAcceptancePolicy
    foundation: ProductionDeploymentRollbackAttestationFoundation
    policy_identity: str
    policy_version: str
    policy_digest: str
    attestation_foundation_digest: str
    attestation_subject_digest: str
    attestation_policy_digest: str
    proposal_digest: str
    requested_state: bool
    proposal_revision: str
    proposal_revision_digest: str
    feature_gate_identity: str
    feature_gate_requested_state: bool
    runtime_configuration_identity: str
    runtime_configuration_digest: str
    deployment_artifact_identity: str
    deployment_artifact_digest: str
    deployment_artifact_evidence_digest: str
    rollback_artifact_identity: str
    rollback_artifact_digest: str
    rollback_evidence_digest: str
    rollback_target_identity: str
    rollback_target_digest: str
    rollback_readiness_acceptance_digest: str
    failure_containment_acceptance_digest: str
    checks: tuple[ProductionDeploymentRollbackAttestationAcceptanceCheck, ...]
    issues: tuple[str, ...]
    accepted: bool
    transition_approved: bool = False
    feature_gate_mutated: bool = False
    deployment_executed: bool = False
    rollback_executed: bool = False
    activation_permitted: bool = False
    approval_permitted: bool = False
    runtime_mutated: bool = False
    successful_attestation: bool = False
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
    raise ValueError("unsupported attestation-acceptance material")


def _digest(label: str, value: Any) -> str:
    encoded = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any, *excluded: str) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value)
        if field.name not in excluded)


def _build_policy():
    draft = ProductionDeploymentRollbackAttestationAcceptancePolicy(
        POLICY_IDENTITY, POLICY_VERSION, FOUNDATION_VERSION, FOUNDATION_PREPARED,
        CHECK_ORDER, (FOUNDATION_PREPARED, ROLLBACK_READINESS_ACCEPTED),
        ("transition_approved", "feature_gate_mutated", "deployment_executed",
            "rollback_executed", "activation_permitted", "approval_permitted",
            "runtime_mutated", "successful_attestation"))
    return replace(draft, policy_digest=_digest(
        "ACCEPTANCE_POLICY", _material(draft, "policy_digest")))


CANONICAL_ACCEPTANCE_POLICY = _build_policy()


def verify_production_deployment_rollback_attestation_acceptance_policy(value: Any) -> bool:
    return (
        type(value) is ProductionDeploymentRollbackAttestationAcceptancePolicy
        and value == CANONICAL_ACCEPTANCE_POLICY
        and bool(_HEX.fullmatch(value.policy_digest or ""))
    )


def _foundation_valid(value: Any) -> bool:
    if type(value) is not ProductionDeploymentRollbackAttestationFoundation:
        return False
    if value.version != FOUNDATION_VERSION or value.status != FOUNDATION_PREPARED:
        return False
    if not verify_production_deployment_rollback_attestation_foundation(value):
        return False
    if not verify_production_deployment_rollback_attestation_policy(value.policy):
        return False
    if not verify_production_deployment_rollback_attestation_subject(
            value.subject, value.deployment_evidence, value.rollback_evidence,
            value.rollback_readiness, value.failure_containment):
        return False
    return (
        tuple(item.check_id for item in value.checks) == FOUNDATION_CHECK_ORDER
        and value.rollback_readiness.status == ROLLBACK_READINESS_ACCEPTED
        and value.rollback_readiness.accepted is True
        and value.issues == ()
        and not any((value.transition_approved, value.feature_gate_mutated,
            value.deployment_executed, value.rollback_executed,
            value.activation_permitted, value.approval_permitted,
            value.runtime_mutated, value.successful_attestation))
        and value.executable_output is None
    )


def _check(identifier: str, ordinal: int, digests: tuple[str, ...], reason: str):
    draft = ProductionDeploymentRollbackAttestationAcceptanceCheck(
        identifier, ordinal, digests, True, reason)
    return replace(draft, check_digest=_digest(
        "ACCEPTANCE_CHECK", _material(draft, "check_digest")))


def _checks(value: ProductionDeploymentRollbackAttestationFoundation):
    subject = value.subject
    common = value.foundation_digest
    evidence = (
        (common,), (common,), (common,), (common,),
        (value.policy_digest,), (value.subject_digest,),
        (subject.proposal_digest,), (subject.proposal_digest,),
        (subject.proposal_revision_digest,), (subject.proposal_digest,),
        (subject.proposal_digest,), (subject.runtime_configuration_digest,),
        (subject.runtime_configuration_digest,), (subject.deployment_artifact_evidence_digest,),
        (subject.deployment_artifact_identity,), (subject.deployment_artifact_digest,),
        (subject.rollback_evidence_digest,),
        (_digest("ROLLBACK_ARTIFACT_IDENTITY_EVIDENCE", subject.rollback_artifact_identity),),
        (subject.rollback_artifact_digest,), (subject.rollback_target_digest,),
        (subject.rollback_readiness_acceptance_digest,),
        (subject.rollback_readiness_acceptance_digest,),
        (subject.failure_containment_acceptance_digest,),
        (value.deployment_evidence_digest, value.rollback_evidence_digest),
        (value.deployment_evidence_digest, subject.proposal_revision_digest),
        (value.deployment_evidence_digest, subject.proposal_digest),
        (value.deployment_evidence_digest, subject.runtime_configuration_digest),
        (_digest("ORDERED_FOUNDATION_CHECKS",
            tuple(item.check_digest for item in value.checks)),),
        (common,), (common,), (common,), (common,), (common,), (common,),
        (common,), (common,), (common,),
    )
    reasons = tuple(identifier.lower().replace("_", " ") for identifier in CHECK_ORDER)
    return tuple(_check(identifier, index + 1, evidence[index], reasons[index])
        for index, identifier in enumerate(CHECK_ORDER))


def _build(value: ProductionDeploymentRollbackAttestationFoundation):
    subject = value.subject
    checks = _checks(value)
    topology = _digest("ACCEPTANCE_TOPOLOGY", (
        CANONICAL_ACCEPTANCE_POLICY.policy_digest, value.foundation_digest,
        value.subject_digest, tuple(item.check_digest for item in checks)))
    draft = ProductionDeploymentRollbackAttestationAcceptance(
        VERSION, SCOPE, ACCEPTED, CANONICAL_ACCEPTANCE_POLICY, value,
        POLICY_IDENTITY, POLICY_VERSION, CANONICAL_ACCEPTANCE_POLICY.policy_digest,
        value.foundation_digest, value.subject_digest, value.policy_digest,
        subject.proposal_digest, subject.requested_state,
        subject.proposal_revision, subject.proposal_revision_digest,
        subject.feature_gate_identity, subject.feature_gate_requested_state,
        subject.runtime_configuration_identity, subject.runtime_configuration_digest,
        subject.deployment_artifact_identity, subject.deployment_artifact_digest,
        subject.deployment_artifact_evidence_digest,
        subject.rollback_artifact_identity, subject.rollback_artifact_digest,
        subject.rollback_evidence_digest, subject.rollback_target_identity,
        subject.rollback_target_digest, subject.rollback_readiness_acceptance_digest,
        subject.failure_containment_acceptance_digest, checks, (), True,
        topology_digest=topology)
    return replace(draft, acceptance_digest=_digest(
        "ATTESTATION_ACCEPTANCE", _material(draft, "acceptance_digest")))


def evaluate_production_deployment_rollback_attestation_acceptance(
    attestation_foundation: Any,
) -> ProductionDeploymentRollbackAttestationAcceptance | None:
    try:
        if not _foundation_valid(attestation_foundation):
            return None
        return _build(attestation_foundation)
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def classify_production_deployment_rollback_attestation_acceptance(
    attestation_foundation: Any,
) -> str:
    return ACCEPTED if evaluate_production_deployment_rollback_attestation_acceptance(
        attestation_foundation) is not None else REJECTED


def verify_production_deployment_rollback_attestation_acceptance_check(value: Any) -> bool:
    try:
        return (
            type(value) is ProductionDeploymentRollbackAttestationAcceptanceCheck
            and value.check_id in CHECK_ORDER
            and value.ordinal == CHECK_ORDER.index(value.check_id) + 1
            and value.verified is True and bool(value.reason)
            and bool(value.evidence_digests)
            and all(_HEX.fullmatch(item or "") for item in value.evidence_digests)
            and bool(_HEX.fullmatch(value.check_digest or ""))
            and value.check_digest == _digest(
                "ACCEPTANCE_CHECK", _material(value, "check_digest"))
        )
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def verify_production_deployment_rollback_attestation_acceptance(value: Any) -> bool:
    try:
        if type(value) is not ProductionDeploymentRollbackAttestationAcceptance:
            return False
        if value.version != VERSION or value.scope != SCOPE or value.status != ACCEPTED:
            return False
        if value.accepted is not True or value.issues != ():
            return False
        if not verify_production_deployment_rollback_attestation_acceptance_policy(value.policy):
            return False
        if value.policy is not CANONICAL_ACCEPTANCE_POLICY:
            return False
        if any((value.transition_approved, value.feature_gate_mutated,
                value.deployment_executed, value.rollback_executed,
                value.activation_permitted, value.approval_permitted,
                value.runtime_mutated, value.successful_attestation)):
            return False
        if value.executable_output is not None:
            return False
        if tuple(item.check_id for item in value.checks) != CHECK_ORDER:
            return False
        if len(value.checks) != len(CHECK_ORDER) or len(
                {item.check_id for item in value.checks}) != len(CHECK_ORDER):
            return False
        if not all(verify_production_deployment_rollback_attestation_acceptance_check(item)
                for item in value.checks):
            return False
        expected = evaluate_production_deployment_rollback_attestation_acceptance(
            value.foundation)
        return expected is not None and value == expected and bool(
            _HEX.fullmatch(value.topology_digest or "")) and bool(
            _HEX.fullmatch(value.acceptance_digest or "")) and value.acceptance_digest == _digest(
                "ATTESTATION_ACCEPTANCE", _material(value, "acceptance_digest"))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


__all__ = (
    "VERSION", "SCOPE", "ACCEPTED", "REJECTED", "POLICY_IDENTITY",
    "POLICY_VERSION", "CHECK_ORDER",
    "ProductionDeploymentRollbackAttestationAcceptancePolicy",
    "ProductionDeploymentRollbackAttestationAcceptanceCheck",
    "ProductionDeploymentRollbackAttestationAcceptance",
    "CANONICAL_ACCEPTANCE_POLICY",
    "evaluate_production_deployment_rollback_attestation_acceptance",
    "classify_production_deployment_rollback_attestation_acceptance",
    "verify_production_deployment_rollback_attestation_acceptance_policy",
    "verify_production_deployment_rollback_attestation_acceptance_check",
    "verify_production_deployment_rollback_attestation_acceptance",
)
