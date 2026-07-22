"""V5.15.24.7.4.22 passive controlled-production activation qualification.

QUALIFIED proves only that the canonical safety evidence chain verifies.  It
creates no operational permission, approval, activation, deployment, rollback,
or runtime mutation.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from typing import Any, Mapping

from brain.production_deployment_rollback_attestation_acceptance import (
    ACCEPTED as REQUIRED_ACCEPTANCE_STATUS,
    ProductionDeploymentRollbackAttestationAcceptance,
    verify_production_deployment_rollback_attestation_acceptance,
    verify_production_deployment_rollback_attestation_acceptance_policy,
)
from brain.production_deployment_rollback_attestation_foundation import (
    PREPARED as REQUIRED_ATTESTATION_STATUS,
    verify_production_deployment_rollback_attestation_foundation,
)
from brain.production_deployment_artifact_evidence_foundation import (
    PREPARED as REQUIRED_DEPLOYMENT_EVIDENCE_STATUS,
    verify_production_deployment_artifact_evidence,
)
from brain.production_failure_containment_acceptance import (
    STATUS as REQUIRED_FAILURE_CONTAINMENT_STATUS,
    verify_production_failure_containment_acceptance_report,
)
from brain.production_rollback_evidence_foundation import (
    STATUS as REQUIRED_ROLLBACK_EVIDENCE_STATUS,
    verify_production_rollback_evidence_foundation,
)
from brain.production_rollback_readiness_acceptance import (
    ACCEPTED as REQUIRED_ROLLBACK_READINESS_STATUS,
    verify_production_rollback_readiness_acceptance,
)

VERSION = "5.15.24.7.4.22"
SCHEMA = "controlled-production-activation-qualification/v1"
SCOPE = "CONTROLLED_PRODUCTION_ACTIVATION_QUALIFICATION"
QUALIFIED = "CONTROLLED_PRODUCTION_ACTIVATION_QUALIFIED"
REJECTED = "CONTROLLED_PRODUCTION_ACTIVATION_REJECTED"
POLICY_IDENTITY = "controlled-production-activation-qualification-policy"
POLICY_VERSION = "1"
CHECK_ORDER = (
    "ACCEPTANCE_VERIFIED", "ACCEPTANCE_DIGEST_VERIFIED",
    "ACCEPTANCE_POLICY_VERIFIED", "ATTESTATION_FOUNDATION_VERIFIED",
    "PROPOSAL_VERIFIED", "REQUESTED_STATE_VERIFIED",
    "RELEASE_REVISION_VERIFIED", "FEATURE_GATE_VERIFIED",
    "RUNTIME_CONFIGURATION_VERIFIED", "DEPLOYMENT_ARTIFACT_VERIFIED",
    "ROLLBACK_ARTIFACT_VERIFIED", "ROLLBACK_TARGET_VERIFIED",
    "ROLLBACK_READINESS_VERIFIED", "FAILURE_CONTAINMENT_VERIFIED",
    "EVIDENCE_CHAIN_VERIFIED", "CROSS_BINDING_VERIFIED",
    "QUALIFICATION_POLICY_VERIFIED", "QUALIFICATION_DIGEST_VERIFIED",
    "DEPLOYMENT_NOT_EXECUTED", "ROLLBACK_NOT_EXECUTED",
    "TRANSITION_NOT_APPROVED", "FEATURE_GATE_NOT_MUTATED",
    "ACTIVATION_NOT_PERMITTED", "APPROVAL_NOT_PERMITTED",
    "RUNTIME_NOT_MUTATED", "SUCCESSFUL_ACTIVATION_NOT_CLAIMED",
)
BOUNDARY_FIELDS = (
    "transition_approved", "feature_gate_mutated", "deployment_executed",
    "rollback_executed", "activation_permitted", "approval_permitted",
    "runtime_mutated", "successful_activation",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ControlledProductionActivationQualificationPolicy:
    schema: str
    identity: str
    version: str
    required_acceptance_status: str
    required_attestation_status: str
    required_deployment_evidence_status: str
    required_rollback_evidence_status: str
    required_rollback_readiness_status: str
    required_failure_containment_status: str
    required_checks: tuple[str, ...]
    required_false_boundaries: tuple[str, ...]
    policy_digest: str = ""


@dataclass(frozen=True)
class ControlledProductionActivationQualificationCheck:
    check_id: str
    ordinal: int
    evidence_digests: tuple[str, ...]
    verified: bool
    reason: str
    check_digest: str = ""


@dataclass(frozen=True)
class ControlledProductionActivationQualification:
    version: str
    schema: str
    scope: str
    status: str
    policy: ControlledProductionActivationQualificationPolicy
    acceptance: ProductionDeploymentRollbackAttestationAcceptance
    policy_digest: str
    acceptance_digest: str
    attestation_digest: str
    deployment_digest: str
    rollback_digest: str
    readiness_digest: str
    failure_containment_digest: str
    proposal_digest: str
    revision_id: str
    revision_digest: str
    gate_identity: str
    requested_state: bool
    configuration_identity: str
    configuration_digest: str
    rollback_target_digest: str
    checks: tuple[ControlledProductionActivationQualificationCheck, ...]
    issues: tuple[str, ...]
    qualified: bool
    transition_approved: bool = False
    feature_gate_mutated: bool = False
    deployment_executed: bool = False
    rollback_executed: bool = False
    activation_permitted: bool = False
    approval_permitted: bool = False
    runtime_mutated: bool = False
    successful_activation: bool = False
    executable_output: None = None
    topology_digest: str = ""
    qualification_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int): return value
    if isinstance(value, (tuple, list)): return [_canonical(item) for item in value]
    if isinstance(value, Mapping):
        return [[str(key), _canonical(value[key])] for key in sorted(value)]
    if is_dataclass(value) and not isinstance(value, type):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported qualification material")


def _digest(label: str, value: Any) -> str:
    encoded = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any, *excluded: str) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value)
        if field.name not in excluded)


def _build_policy():
    draft = ControlledProductionActivationQualificationPolicy(
        SCHEMA, POLICY_IDENTITY, POLICY_VERSION, REQUIRED_ACCEPTANCE_STATUS,
        REQUIRED_ATTESTATION_STATUS, REQUIRED_DEPLOYMENT_EVIDENCE_STATUS,
        REQUIRED_ROLLBACK_EVIDENCE_STATUS, REQUIRED_ROLLBACK_READINESS_STATUS,
        REQUIRED_FAILURE_CONTAINMENT_STATUS, CHECK_ORDER, BOUNDARY_FIELDS)
    return replace(draft, policy_digest=_digest(
        "QUALIFICATION_POLICY", _material(draft, "policy_digest")))


CANONICAL_QUALIFICATION_POLICY = _build_policy()


def verify_controlled_production_activation_qualification_policy(value: Any) -> bool:
    return type(value) is ControlledProductionActivationQualificationPolicy and value == (
        CANONICAL_QUALIFICATION_POLICY) and bool(_HEX.fullmatch(value.policy_digest or ""))


def _acceptance_valid(value: Any) -> bool:
    if type(value) is not ProductionDeploymentRollbackAttestationAcceptance:
        return False
    if not verify_production_deployment_rollback_attestation_acceptance(value): return False
    if value.status != REQUIRED_ACCEPTANCE_STATUS or not value.accepted: return False
    if not verify_production_deployment_rollback_attestation_acceptance_policy(value.policy): return False
    foundation = value.foundation
    if not verify_production_deployment_rollback_attestation_foundation(foundation): return False
    deployment, rollback = foundation.deployment_evidence, foundation.rollback_evidence
    readiness, containment = foundation.rollback_readiness, foundation.failure_containment
    return (
        foundation.status == REQUIRED_ATTESTATION_STATUS
        and deployment.status == REQUIRED_DEPLOYMENT_EVIDENCE_STATUS
        and rollback.status == REQUIRED_ROLLBACK_EVIDENCE_STATUS
        and readiness.status == REQUIRED_ROLLBACK_READINESS_STATUS and readiness.accepted
        and containment.status == REQUIRED_FAILURE_CONTAINMENT_STATUS and containment.accepted
        and verify_production_deployment_artifact_evidence(deployment)
        and verify_production_rollback_evidence_foundation(rollback)
        and verify_production_rollback_readiness_acceptance(readiness)
        and verify_production_failure_containment_acceptance_report(containment)
        and deployment.readiness_acceptance is readiness
        and readiness.foundation is rollback
        and rollback.failure_containment is containment
        and not any(getattr(value, field) for field in BOUNDARY_FIELDS[:-1])
        and not value.successful_attestation
        and not any(getattr(foundation, field) for field in BOUNDARY_FIELDS[:-1])
        and not foundation.successful_attestation
    )


def _check(identifier: str, ordinal: int, digests: tuple[str, ...]):
    draft = ControlledProductionActivationQualificationCheck(
        identifier, ordinal, digests, True, identifier.lower().replace("_", " "))
    return replace(draft, check_digest=_digest(
        "QUALIFICATION_CHECK", _material(draft, "check_digest")))


def _checks(value: ProductionDeploymentRollbackAttestationAcceptance):
    foundation, subject = value.foundation, value.foundation.subject
    common = value.acceptance_digest
    evidence = (
        (common,), (common,), (value.policy_digest,), (foundation.foundation_digest,),
        (subject.proposal_digest,), (subject.proposal_digest,),
        (subject.proposal_revision_digest,), (subject.proposal_digest,),
        (subject.runtime_configuration_digest,), (subject.deployment_artifact_digest,),
        (subject.rollback_artifact_digest,), (subject.rollback_target_digest,),
        (subject.rollback_readiness_acceptance_digest,),
        (subject.failure_containment_acceptance_digest,),
        (foundation.foundation_digest, common),
        (value.deployment_artifact_evidence_digest, value.rollback_evidence_digest),
        (CANONICAL_QUALIFICATION_POLICY.policy_digest,),
        (_digest("QUALIFICATION_DIGEST_INPUT", common),),
        (common,), (common,), (common,), (common,), (common,), (common,),
        (common,), (common,),
    )
    return tuple(_check(identifier, index + 1, evidence[index])
        for index, identifier in enumerate(CHECK_ORDER))


def _build(value: ProductionDeploymentRollbackAttestationAcceptance):
    foundation, subject = value.foundation, value.foundation.subject
    checks = _checks(value)
    topology = _digest("QUALIFICATION_TOPOLOGY", (
        CANONICAL_QUALIFICATION_POLICY.policy_digest, value.acceptance_digest,
        foundation.foundation_digest, tuple(item.check_digest for item in checks)))
    draft = ControlledProductionActivationQualification(
        VERSION, SCHEMA, SCOPE, QUALIFIED, CANONICAL_QUALIFICATION_POLICY, value,
        CANONICAL_QUALIFICATION_POLICY.policy_digest, value.acceptance_digest,
        foundation.foundation_digest, value.deployment_artifact_evidence_digest,
        value.rollback_evidence_digest, value.rollback_readiness_acceptance_digest,
        value.failure_containment_acceptance_digest, value.proposal_digest,
        value.proposal_revision, value.proposal_revision_digest,
        value.feature_gate_identity, value.requested_state,
        value.runtime_configuration_identity, value.runtime_configuration_digest,
        value.rollback_target_digest, checks, (), True, topology_digest=topology)
    return replace(draft, qualification_digest=_digest(
        "ACTIVATION_QUALIFICATION", _material(draft, "qualification_digest")))


def evaluate_controlled_production_activation_qualification(
    attestation_acceptance: Any,
) -> ControlledProductionActivationQualification | None:
    try:
        if not _acceptance_valid(attestation_acceptance): return None
        return _build(attestation_acceptance)
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return None


def classify_controlled_production_activation_qualification(attestation_acceptance: Any) -> str:
    return QUALIFIED if evaluate_controlled_production_activation_qualification(
        attestation_acceptance) is not None else REJECTED


def verify_controlled_production_activation_qualification_check(value: Any) -> bool:
    try:
        return (type(value) is ControlledProductionActivationQualificationCheck
            and value.check_id in CHECK_ORDER
            and value.ordinal == CHECK_ORDER.index(value.check_id) + 1
            and value.verified is True and bool(value.reason) and bool(value.evidence_digests)
            and all(_HEX.fullmatch(item or "") for item in value.evidence_digests)
            and bool(_HEX.fullmatch(value.check_digest or ""))
            and value.check_digest == _digest(
                "QUALIFICATION_CHECK", _material(value, "check_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return False


def verify_controlled_production_activation_qualification(value: Any) -> bool:
    try:
        if type(value) is not ControlledProductionActivationQualification: return False
        if (value.version != VERSION or value.schema != SCHEMA or value.scope != SCOPE
                or value.status != QUALIFIED or value.qualified is not True): return False
        if not verify_controlled_production_activation_qualification_policy(value.policy): return False
        if value.policy is not CANONICAL_QUALIFICATION_POLICY: return False
        if value.issues != () or any(getattr(value, field) for field in BOUNDARY_FIELDS): return False
        if value.executable_output is not None: return False
        if tuple(item.check_id for item in value.checks) != CHECK_ORDER: return False
        if len(value.checks) != len(CHECK_ORDER) or len(
                {item.check_id for item in value.checks}) != len(CHECK_ORDER): return False
        if not all(verify_controlled_production_activation_qualification_check(item)
                for item in value.checks): return False
        expected = evaluate_controlled_production_activation_qualification(value.acceptance)
        return expected is not None and value == expected and bool(
            _HEX.fullmatch(value.topology_digest or "")) and bool(
            _HEX.fullmatch(value.qualification_digest or "")) and value.qualification_digest == _digest(
                "ACTIVATION_QUALIFICATION", _material(value, "qualification_digest"))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return False


__all__ = (
    "VERSION", "SCHEMA", "SCOPE", "QUALIFIED", "REJECTED", "POLICY_IDENTITY",
    "POLICY_VERSION", "CHECK_ORDER", "BOUNDARY_FIELDS",
    "ControlledProductionActivationQualificationPolicy",
    "ControlledProductionActivationQualificationCheck",
    "ControlledProductionActivationQualification", "CANONICAL_QUALIFICATION_POLICY",
    "evaluate_controlled_production_activation_qualification",
    "classify_controlled_production_activation_qualification",
    "verify_controlled_production_activation_qualification_policy",
    "verify_controlled_production_activation_qualification_check",
    "verify_controlled_production_activation_qualification",
)
