"""V5.15.24.7.4.20 passive deployment/rollback attestation foundation.

PREPARED means only that exact deployment and rollback evidence is structurally
cross-bound.  This module grants no approval, activation, deployment, rollback,
runtime mutation, or successful attestation authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from typing import Any, Mapping

from brain.production_deployment_artifact_evidence_foundation import (
    PREPARED as DEPLOYMENT_EVIDENCE_PREPARED,
    ProductionDeploymentArtifactEvidence,
    verify_production_deployment_artifact_evidence,
)
from brain.production_failure_containment_acceptance import (
    ProductionFailureContainmentAcceptanceReport,
    verify_production_failure_containment_acceptance_report,
)
from brain.production_rollback_evidence_foundation import (
    STATUS as ROLLBACK_EVIDENCE_BOUND,
    ProductionRollbackEvidenceFoundation,
    verify_production_rollback_evidence_foundation,
)
from brain.production_rollback_readiness_acceptance import (
    ACCEPTED as ROLLBACK_READINESS_ACCEPTED,
    ProductionRollbackReadinessAcceptance,
    verify_production_rollback_readiness_acceptance,
)

VERSION = "5.15.24.7.4.20"
SCOPE = "PRODUCTION_DEPLOYMENT_ROLLBACK_ATTESTATION_FOUNDATION"
PREPARED = "DEPLOYMENT_ROLLBACK_ATTESTATION_PREPARED"
REJECTED = "DEPLOYMENT_ROLLBACK_ATTESTATION_REJECTED"
POLICY_IDENTITY = "production-deployment-rollback-attestation-preparation-policy"
POLICY_VERSION = "1"
SUBJECT_SCHEMA = "production-deployment-rollback-attestation-subject/v1"
CHECK_ORDER = (
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
    "DEPLOYMENT_AND_ROLLBACK_PROPOSAL_BINDING_VERIFIED",
    "DEPLOYMENT_AND_ROLLBACK_REVISION_BINDING_VERIFIED",
    "DEPLOYMENT_AND_ROLLBACK_GATE_BINDING_VERIFIED",
    "DEPLOYMENT_AND_ROLLBACK_CONFIGURATION_BINDING_VERIFIED",
    "ATTESTATION_POLICY_VERIFIED",
    "DEPLOYMENT_NOT_EXECUTED",
    "ROLLBACK_NOT_EXECUTED",
    "FEATURE_GATE_NOT_MUTATED",
    "TRANSITION_NOT_APPROVED",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionDeploymentRollbackAttestationPolicy:
    identity: str
    version: str
    required_checks: tuple[str, ...]
    accepted_upstream_statuses: tuple[str, ...]
    prohibited_state_fields: tuple[str, ...]
    policy_digest: str = ""


@dataclass(frozen=True)
class ProductionDeploymentRollbackAttestationSubject:
    schema: str
    policy_identity: str
    policy_version: str
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
    subject_digest: str = ""


@dataclass(frozen=True)
class ProductionDeploymentRollbackAttestationCheck:
    check_id: str
    ordinal: int
    evidence_digests: tuple[str, ...]
    verified: bool
    reason: str
    check_digest: str = ""


@dataclass(frozen=True)
class ProductionDeploymentRollbackAttestationFoundation:
    version: str
    scope: str
    status: str
    policy: ProductionDeploymentRollbackAttestationPolicy
    subject: ProductionDeploymentRollbackAttestationSubject
    deployment_evidence: ProductionDeploymentArtifactEvidence
    rollback_evidence: ProductionRollbackEvidenceFoundation
    rollback_readiness: ProductionRollbackReadinessAcceptance
    failure_containment: ProductionFailureContainmentAcceptanceReport
    policy_digest: str
    subject_digest: str
    deployment_evidence_digest: str
    rollback_evidence_digest: str
    rollback_readiness_digest: str
    failure_containment_digest: str
    checks: tuple[ProductionDeploymentRollbackAttestationCheck, ...]
    issues: tuple[str, ...]
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
    foundation_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, Mapping):
        return [[str(key), _canonical(value[key])] for key in sorted(value)]
    if is_dataclass(value) and not isinstance(value, type):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported attestation-foundation material")


def _digest(label: str, value: Any) -> str:
    encoded = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any, *excluded: str) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value)
        if field.name not in excluded)


def _build_policy():
    draft = ProductionDeploymentRollbackAttestationPolicy(
        POLICY_IDENTITY, POLICY_VERSION, CHECK_ORDER,
        (DEPLOYMENT_EVIDENCE_PREPARED, ROLLBACK_EVIDENCE_BOUND,
            ROLLBACK_READINESS_ACCEPTED),
        ("transition_approved", "feature_gate_mutated", "deployment_executed",
            "rollback_executed", "activation_permitted", "approval_permitted",
            "runtime_mutated", "successful_attestation"))
    return replace(draft, policy_digest=_digest(
        "ATTESTATION_POLICY", _material(draft, "policy_digest")))


CANONICAL_ATTESTATION_POLICY = _build_policy()


def verify_production_deployment_rollback_attestation_policy(value: Any) -> bool:
    return type(value) is ProductionDeploymentRollbackAttestationPolicy and value == (
        CANONICAL_ATTESTATION_POLICY) and bool(_HEX.fullmatch(value.policy_digest or ""))


def _upstream_valid(deployment: Any, rollback: Any, readiness: Any,
                    containment: Any) -> bool:
    if type(deployment) is not ProductionDeploymentArtifactEvidence:
        return False
    if type(rollback) is not ProductionRollbackEvidenceFoundation:
        return False
    if type(readiness) is not ProductionRollbackReadinessAcceptance:
        return False
    if type(containment) is not ProductionFailureContainmentAcceptanceReport:
        return False
    if not verify_production_deployment_artifact_evidence(deployment):
        return False
    if not verify_production_rollback_evidence_foundation(rollback):
        return False
    if not verify_production_rollback_readiness_acceptance(readiness):
        return False
    if not verify_production_failure_containment_acceptance_report(containment):
        return False
    if deployment.status != DEPLOYMENT_EVIDENCE_PREPARED:
        return False
    if rollback.status != ROLLBACK_EVIDENCE_BOUND:
        return False
    if readiness.status != ROLLBACK_READINESS_ACCEPTED or not readiness.accepted:
        return False
    if deployment.readiness_acceptance is not readiness:
        return False
    if readiness.foundation is not rollback:
        return False
    if rollback.failure_containment is not containment:
        return False
    return (
        deployment.proposal_id == readiness.proposal_digest == rollback.proposal_digest
        and deployment.requested_state is readiness.requested_target_state is True
        and rollback.requested_target_state is True
        and deployment.proposal_revision == readiness.release_revision_id == rollback.release_revision_id
        and deployment.proposal_revision_digest == readiness.release_revision_digest == rollback.release_revision_digest
        and deployment.feature_gate_name == readiness.feature_gate_identity == rollback.feature_gate_identity
        and deployment.feature_gate_requested_state is True
        and deployment.runtime_configuration_identity == readiness.rollback_configuration_identity == rollback.rollback_configuration_identity
        and deployment.runtime_configuration_digest == readiness.rollback_configuration_digest == rollback.rollback_configuration_digest
        and readiness.rollback_target_identity == rollback.rollback_target_identity
        and readiness.rollback_target_digest == rollback.rollback_target_digest
        and readiness.rollback_artifact_identity == rollback.rollback_artifact_identity
        and readiness.rollback_artifact_digest == rollback.rollback_artifact_digest
        and readiness.containment_report_digest == containment.report_digest == rollback.containment_report_digest
        and readiness.containment_topology_digest == containment.topology_digest == rollback.containment_topology_digest
        and not any((deployment.deployment_executed, deployment.feature_gate_mutated,
            deployment.transition_approved, deployment.deployment_attested,
            deployment.rollback_executed, deployment.approval_permitted,
            readiness.deployment_attested, readiness.rollback_executed,
            readiness.transition_approved, readiness.activation_permitted,
            readiness.mutation_permitted, rollback.rollback_executed,
            rollback.activation_permitted, rollback.mutation_permitted))
    )


def _build_subject(deployment: ProductionDeploymentArtifactEvidence,
                   rollback: ProductionRollbackEvidenceFoundation,
                   readiness: ProductionRollbackReadinessAcceptance,
                   containment: ProductionFailureContainmentAcceptanceReport):
    draft = ProductionDeploymentRollbackAttestationSubject(
        SUBJECT_SCHEMA, POLICY_IDENTITY, POLICY_VERSION, deployment.proposal_id,
        deployment.requested_state, deployment.proposal_revision,
        deployment.proposal_revision_digest, deployment.feature_gate_name,
        deployment.feature_gate_requested_state,
        deployment.runtime_configuration_identity,
        deployment.runtime_configuration_digest,
        deployment.deployment_artifact_identity,
        deployment.deployment_artifact_digest, deployment.evidence_digest,
        rollback.rollback_artifact_identity, rollback.rollback_artifact_digest,
        rollback.foundation_digest, rollback.rollback_target_identity,
        rollback.rollback_target_digest, readiness.acceptance_digest,
        containment.report_digest)
    return replace(draft, subject_digest=_digest(
        "ATTESTATION_SUBJECT", _material(draft, "subject_digest")))


def verify_production_deployment_rollback_attestation_subject(
    value: Any, deployment: Any, rollback: Any, readiness: Any, containment: Any,
) -> bool:
    try:
        if type(value) is not ProductionDeploymentRollbackAttestationSubject:
            return False
        if not _upstream_valid(deployment, rollback, readiness, containment):
            return False
        expected = _build_subject(deployment, rollback, readiness, containment)
        return value == expected and bool(_HEX.fullmatch(value.subject_digest or ""))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def _check(identifier: str, ordinal: int, digests: tuple[str, ...], reason: str):
    draft = ProductionDeploymentRollbackAttestationCheck(
        identifier, ordinal, digests, True, reason)
    return replace(draft, check_digest=_digest(
        "ATTESTATION_CHECK", _material(draft, "check_digest")))


def _build_checks(subject: ProductionDeploymentRollbackAttestationSubject,
                  deployment: ProductionDeploymentArtifactEvidence,
                  rollback: ProductionRollbackEvidenceFoundation,
                  readiness: ProductionRollbackReadinessAcceptance,
                  containment: ProductionFailureContainmentAcceptanceReport):
    common = readiness.acceptance_digest
    evidence = (
        (subject.proposal_digest,), (subject.proposal_digest,),
        (subject.proposal_revision_digest,), (subject.proposal_digest,),
        (subject.proposal_digest,), (subject.runtime_configuration_digest,),
        (subject.runtime_configuration_digest,), (deployment.evidence_digest,),
        (subject.deployment_artifact_identity,), (subject.deployment_artifact_digest,),
        (rollback.foundation_digest,), (_digest("ROLLBACK_ARTIFACT_IDENTITY_EVIDENCE",
            subject.rollback_artifact_identity),),
        (subject.rollback_artifact_digest,), (subject.rollback_target_digest,),
        (readiness.acceptance_digest,), (readiness.acceptance_digest,),
        (containment.report_digest, containment.topology_digest),
        (deployment.evidence_digest, rollback.foundation_digest),
        (deployment.evidence_digest, rollback.release_revision_digest),
        (deployment.evidence_digest, rollback.proposal_digest),
        (deployment.evidence_digest, rollback.rollback_configuration_digest),
        (CANONICAL_ATTESTATION_POLICY.policy_digest,), (common,), (common,),
        (common,), (common,),
    )
    reasons = tuple(identifier.lower().replace("_", " ") for identifier in CHECK_ORDER)
    return tuple(_check(identifier, index + 1, evidence[index], reasons[index])
        for index, identifier in enumerate(CHECK_ORDER))


def _build(deployment: ProductionDeploymentArtifactEvidence,
           rollback: ProductionRollbackEvidenceFoundation,
           readiness: ProductionRollbackReadinessAcceptance,
           containment: ProductionFailureContainmentAcceptanceReport):
    subject = _build_subject(deployment, rollback, readiness, containment)
    checks = _build_checks(subject, deployment, rollback, readiness, containment)
    topology = _digest("ATTESTATION_TOPOLOGY", (
        CANONICAL_ATTESTATION_POLICY.policy_digest, subject.subject_digest,
        deployment.evidence_digest, rollback.foundation_digest,
        readiness.acceptance_digest, containment.report_digest,
        tuple(item.check_digest for item in checks)))
    draft = ProductionDeploymentRollbackAttestationFoundation(
        VERSION, SCOPE, PREPARED, CANONICAL_ATTESTATION_POLICY, subject,
        deployment, rollback, readiness, containment,
        CANONICAL_ATTESTATION_POLICY.policy_digest, subject.subject_digest,
        deployment.evidence_digest, rollback.foundation_digest,
        readiness.acceptance_digest, containment.report_digest, checks, (),
        topology_digest=topology)
    return replace(draft, foundation_digest=_digest(
        "ATTESTATION_FOUNDATION", _material(draft, "foundation_digest")))


def prepare_production_deployment_rollback_attestation_foundation(
    deployment_evidence: Any, rollback_evidence: Any,
    rollback_readiness: Any, failure_containment: Any,
) -> ProductionDeploymentRollbackAttestationFoundation | None:
    try:
        if not _upstream_valid(deployment_evidence, rollback_evidence,
                rollback_readiness, failure_containment):
            return None
        return _build(deployment_evidence, rollback_evidence,
            rollback_readiness, failure_containment)
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def classify_production_deployment_rollback_attestation_foundation(
    deployment_evidence: Any, rollback_evidence: Any,
    rollback_readiness: Any, failure_containment: Any,
) -> str:
    return PREPARED if prepare_production_deployment_rollback_attestation_foundation(
        deployment_evidence, rollback_evidence, rollback_readiness,
        failure_containment) is not None else REJECTED


def verify_production_deployment_rollback_attestation_check(value: Any) -> bool:
    try:
        return (
            type(value) is ProductionDeploymentRollbackAttestationCheck
            and value.check_id in CHECK_ORDER
            and value.ordinal == CHECK_ORDER.index(value.check_id) + 1
            and value.verified is True and bool(value.reason)
            and bool(value.evidence_digests)
            and all(_HEX.fullmatch(item or "") for item in value.evidence_digests)
            and bool(_HEX.fullmatch(value.check_digest or ""))
            and value.check_digest == _digest(
                "ATTESTATION_CHECK", _material(value, "check_digest"))
        )
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def verify_production_deployment_rollback_attestation_foundation(value: Any) -> bool:
    try:
        if type(value) is not ProductionDeploymentRollbackAttestationFoundation:
            return False
        if value.version != VERSION or value.scope != SCOPE or value.status != PREPARED:
            return False
        if not verify_production_deployment_rollback_attestation_policy(value.policy):
            return False
        if value.policy is not CANONICAL_ATTESTATION_POLICY:
            return False
        if value.issues != () or any((value.transition_approved,
                value.feature_gate_mutated, value.deployment_executed,
                value.rollback_executed, value.activation_permitted,
                value.approval_permitted, value.runtime_mutated,
                value.successful_attestation)) or value.executable_output is not None:
            return False
        if tuple(item.check_id for item in value.checks) != CHECK_ORDER:
            return False
        if len(value.checks) != len(CHECK_ORDER) or len(
                {item.check_id for item in value.checks}) != len(CHECK_ORDER):
            return False
        if not all(verify_production_deployment_rollback_attestation_check(item)
                for item in value.checks):
            return False
        if not verify_production_deployment_rollback_attestation_subject(
                value.subject, value.deployment_evidence, value.rollback_evidence,
                value.rollback_readiness, value.failure_containment):
            return False
        expected = prepare_production_deployment_rollback_attestation_foundation(
            value.deployment_evidence, value.rollback_evidence,
            value.rollback_readiness, value.failure_containment)
        return expected is not None and value == expected and bool(
            _HEX.fullmatch(value.topology_digest or "")) and bool(
            _HEX.fullmatch(value.foundation_digest or "")) and value.foundation_digest == _digest(
                "ATTESTATION_FOUNDATION", _material(value, "foundation_digest"))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


__all__ = (
    "VERSION", "SCOPE", "PREPARED", "REJECTED", "POLICY_IDENTITY",
    "POLICY_VERSION", "SUBJECT_SCHEMA", "CHECK_ORDER",
    "ProductionDeploymentRollbackAttestationPolicy",
    "ProductionDeploymentRollbackAttestationSubject",
    "ProductionDeploymentRollbackAttestationCheck",
    "ProductionDeploymentRollbackAttestationFoundation",
    "CANONICAL_ATTESTATION_POLICY",
    "prepare_production_deployment_rollback_attestation_foundation",
    "classify_production_deployment_rollback_attestation_foundation",
    "verify_production_deployment_rollback_attestation_policy",
    "verify_production_deployment_rollback_attestation_subject",
    "verify_production_deployment_rollback_attestation_check",
    "verify_production_deployment_rollback_attestation_foundation",
)
