"""V5.15.24.7.4.23 operational failure-containment evidence foundation.

The foundation prepares immutable evidence bindings for one explicit canonical
incident type.  It does not claim that an incident occurred, execute
containment, recover, approve, activate, deploy, or roll back anything.
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
    STATUS as CONTAINMENT_ACCEPTED,
    ProductionFailureContainmentAcceptanceReport,
    verify_production_failure_containment_acceptance_report,
)

VERSION = "5.15.24.7.4.23"
SCHEMA = "operational-failure-containment-evidence-foundation/v1"
POLICY_IDENTITY = "operational-failure-containment-evidence-preparation-policy"
POLICY_VERSION = "1"
FOUNDATION_PREPARED = "FOUNDATION_PREPARED"
FOUNDATION_REJECTED = "FOUNDATION_REJECTED"
INCIDENT_TYPES = (
    "EXECUTOR_INVOCATION_FAILURE",
    "BUSINESS_SKILL_FAILURE",
    "CALCULATION_FAILURE",
    "SERIALIZATION_FAILURE",
    "DELIVERY_FAILURE",
    "RUNTIME_EXCEPTION",
    "DEPLOYED_RUNTIME_INCIDENT",
    "PARTIAL_SIDE_EFFECT_DETECTED",
    "UNKNOWN_OPERATIONAL_FAILURE",
)
CHECK_ORDER = (
    "SCHEMA_VERIFIED",
    "POLICY_VERIFIED",
    "INCIDENT_IDENTITY_VERIFIED",
    "PROPOSAL_CONTINUITY_VERIFIED",
    "REQUESTED_STATE_CONTINUITY_VERIFIED",
    "REVISION_CONTINUITY_VERIFIED",
    "RUNTIME_CONFIGURATION_CONTINUITY_VERIFIED",
    "FEATURE_GATE_CONTINUITY_VERIFIED",
    "DEPLOYMENT_ARTIFACT_CONTINUITY_VERIFIED",
    "CONTAINMENT_ACCEPTANCE_CONTINUITY_VERIFIED",
    "EVIDENCE_DIGEST_VERIFIED",
    "BOUNDARY_INVARIANTS_VERIFIED",
)
BOUNDARY_FIELDS = (
    "transition_approved", "activation_permitted", "deployment_executed",
    "rollback_executed", "runtime_mutated", "feature_gate_mutated",
    "approval_permitted",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class OperationalFailureContainmentEvidencePolicy:
    schema: str
    identity: str
    version: str
    incident_types: tuple[str, ...]
    required_deployment_status: str
    required_containment_status: str
    required_checks: tuple[str, ...]
    required_false_boundaries: tuple[str, ...]
    policy_digest: str = ""


@dataclass(frozen=True)
class OperationalFailureIncidentIdentity:
    schema: str
    incident_type: str
    proposal_digest: str
    release_revision_id: str
    deployment_artifact_identity: str
    identity_digest: str = ""


@dataclass(frozen=True)
class OperationalFailureEvidence:
    incident_identity: OperationalFailureIncidentIdentity
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
    incident_observed: bool = False
    containment_executed: bool = False
    evidence_digest: str = ""


@dataclass(frozen=True)
class OperationalFailureContainmentEvidenceCheck:
    check_id: str
    ordinal: int
    evidence_digests: tuple[str, ...]
    verified: bool
    check_digest: str = ""


@dataclass(frozen=True)
class OperationalFailureContainmentEvidenceFoundation:
    version: str
    schema: str
    status: str
    policy: OperationalFailureContainmentEvidencePolicy
    deployment_evidence: ProductionDeploymentArtifactEvidence
    containment_acceptance: ProductionFailureContainmentAcceptanceReport
    evidence: OperationalFailureEvidence
    policy_digest: str
    incident_identity_digest: str
    deployment_evidence_digest: str
    containment_acceptance_digest: str
    checks: tuple[OperationalFailureContainmentEvidenceCheck, ...]
    issues: tuple[str, ...]
    transition_approved: bool = False
    activation_permitted: bool = False
    deployment_executed: bool = False
    rollback_executed: bool = False
    runtime_mutated: bool = False
    feature_gate_mutated: bool = False
    approval_permitted: bool = False
    executable_output: None = None
    topology_digest: str = ""
    foundation_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int): return value
    if isinstance(value, (tuple, list)): return [_canonical(item) for item in value]
    if isinstance(value, Mapping):
        return [[str(key), _canonical(value[key])] for key in sorted(value)]
    if is_dataclass(value) and not isinstance(value, type):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported operational-containment evidence material")


def _digest(label: str, value: Any) -> str:
    encoded = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any, *excluded: str) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value)
        if field.name not in excluded)


def _build_policy():
    draft = OperationalFailureContainmentEvidencePolicy(
        SCHEMA, POLICY_IDENTITY, POLICY_VERSION, INCIDENT_TYPES,
        DEPLOYMENT_EVIDENCE_PREPARED, CONTAINMENT_ACCEPTED,
        CHECK_ORDER, BOUNDARY_FIELDS)
    return replace(draft, policy_digest=_digest(
        "EVIDENCE_POLICY", _material(draft, "policy_digest")))


CANONICAL_EVIDENCE_POLICY = _build_policy()


def verify_operational_failure_containment_evidence_policy(value: Any) -> bool:
    return type(value) is OperationalFailureContainmentEvidencePolicy and value == (
        CANONICAL_EVIDENCE_POLICY) and bool(_HEX.fullmatch(value.policy_digest or ""))


def _upstream_valid(deployment: Any, containment: Any) -> bool:
    if type(deployment) is not ProductionDeploymentArtifactEvidence: return False
    if type(containment) is not ProductionFailureContainmentAcceptanceReport: return False
    if not verify_production_deployment_artifact_evidence(deployment): return False
    if not verify_production_failure_containment_acceptance_report(containment): return False
    rollback = deployment.readiness_acceptance.foundation
    return (
        deployment.status == DEPLOYMENT_EVIDENCE_PREPARED
        and containment.status == CONTAINMENT_ACCEPTED and containment.accepted is True
        and rollback.failure_containment is containment
        and deployment.proposal_id == rollback.proposal_digest
        and deployment.proposal_revision == rollback.release_revision_id
        and deployment.feature_gate_name == rollback.feature_gate_identity
        and deployment.runtime_configuration_digest == rollback.rollback_configuration_digest
        and not any((deployment.deployment_executed, deployment.feature_gate_mutated,
            deployment.transition_approved, deployment.rollback_executed,
            deployment.approval_permitted))
    )


def _build_identity(incident_type: str, deployment: ProductionDeploymentArtifactEvidence):
    draft = OperationalFailureIncidentIdentity(
        SCHEMA, incident_type, deployment.proposal_id,
        deployment.proposal_revision, deployment.deployment_artifact_identity)
    return replace(draft, identity_digest=_digest(
        "INCIDENT_IDENTITY", _material(draft, "identity_digest")))


def verify_operational_failure_incident_identity(
    value: Any, deployment_evidence: Any,
) -> bool:
    try:
        return (type(value) is OperationalFailureIncidentIdentity
            and type(deployment_evidence) is ProductionDeploymentArtifactEvidence
            and value.incident_type in INCIDENT_TYPES
            and verify_production_deployment_artifact_evidence(deployment_evidence)
            and value == _build_identity(value.incident_type, deployment_evidence)
            and bool(_HEX.fullmatch(value.identity_digest or "")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return False


def _build_evidence(identity: OperationalFailureIncidentIdentity,
                    deployment: ProductionDeploymentArtifactEvidence,
                    containment: ProductionFailureContainmentAcceptanceReport):
    draft = OperationalFailureEvidence(
        identity, deployment.proposal_id, deployment.requested_state,
        deployment.proposal_revision, deployment.proposal_revision_digest,
        deployment.runtime_configuration_identity, deployment.runtime_configuration_digest,
        deployment.feature_gate_name, deployment.feature_gate_requested_state,
        deployment.deployment_artifact_identity, deployment.deployment_artifact_digest,
        deployment.evidence_digest, containment.report_digest, containment.topology_digest)
    return replace(draft, evidence_digest=_digest(
        "FAILURE_EVIDENCE", _material(draft, "evidence_digest")))


def _check(identifier: str, ordinal: int, digests: tuple[str, ...]):
    draft = OperationalFailureContainmentEvidenceCheck(
        identifier, ordinal, digests, True)
    return replace(draft, check_digest=_digest(
        "EVIDENCE_CHECK", _material(draft, "check_digest")))


def _build(incident_type: str, deployment: ProductionDeploymentArtifactEvidence,
           containment: ProductionFailureContainmentAcceptanceReport):
    identity = _build_identity(incident_type, deployment)
    evidence = _build_evidence(identity, deployment, containment)
    common = evidence.evidence_digest
    check_evidence = (
        (common,), (CANONICAL_EVIDENCE_POLICY.policy_digest,),
        (identity.identity_digest,), (deployment.proposal_id,),
        (deployment.proposal_id,), (deployment.proposal_revision_digest,),
        (deployment.runtime_configuration_digest,), (deployment.proposal_id,),
        (deployment.deployment_artifact_digest,), (containment.report_digest,),
        (evidence.evidence_digest,), (common,),
    )
    checks = tuple(_check(identifier, index + 1, check_evidence[index])
        for index, identifier in enumerate(CHECK_ORDER))
    topology = _digest("FOUNDATION_TOPOLOGY", (
        CANONICAL_EVIDENCE_POLICY.policy_digest, identity.identity_digest,
        evidence.evidence_digest, tuple(item.check_digest for item in checks)))
    draft = OperationalFailureContainmentEvidenceFoundation(
        VERSION, SCHEMA, FOUNDATION_PREPARED, CANONICAL_EVIDENCE_POLICY,
        deployment, containment, evidence, CANONICAL_EVIDENCE_POLICY.policy_digest,
        identity.identity_digest, deployment.evidence_digest,
        containment.report_digest, checks, (), topology_digest=topology)
    return replace(draft, foundation_digest=_digest(
        "EVIDENCE_FOUNDATION", _material(draft, "foundation_digest")))


def prepare_operational_failure_containment_evidence_foundation(
    incident_type: Any, deployment_evidence: Any, containment_acceptance: Any,
) -> OperationalFailureContainmentEvidenceFoundation | None:
    try:
        if type(incident_type) is not str or incident_type not in INCIDENT_TYPES: return None
        if not _upstream_valid(deployment_evidence, containment_acceptance): return None
        return _build(incident_type, deployment_evidence, containment_acceptance)
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return None


def classify_operational_failure_containment_evidence_foundation(
    incident_type: Any, deployment_evidence: Any, containment_acceptance: Any,
) -> str:
    return FOUNDATION_PREPARED if prepare_operational_failure_containment_evidence_foundation(
        incident_type, deployment_evidence, containment_acceptance) is not None else FOUNDATION_REJECTED


def verify_operational_failure_containment_evidence_check(value: Any) -> bool:
    try:
        return (type(value) is OperationalFailureContainmentEvidenceCheck
            and value.check_id in CHECK_ORDER
            and value.ordinal == CHECK_ORDER.index(value.check_id) + 1
            and value.verified is True and bool(value.evidence_digests)
            and all(_HEX.fullmatch(item or "") for item in value.evidence_digests)
            and bool(_HEX.fullmatch(value.check_digest or ""))
            and value.check_digest == _digest("EVIDENCE_CHECK", _material(value, "check_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return False


def verify_operational_failure_containment_evidence_foundation(value: Any) -> bool:
    try:
        if type(value) is not OperationalFailureContainmentEvidenceFoundation: return False
        if value.version != VERSION or value.schema != SCHEMA or value.status != FOUNDATION_PREPARED: return False
        if not verify_operational_failure_containment_evidence_policy(value.policy): return False
        if value.policy is not CANONICAL_EVIDENCE_POLICY: return False
        if value.issues != () or any(getattr(value, field) for field in BOUNDARY_FIELDS): return False
        if value.executable_output is not None or value.evidence.incident_observed or value.evidence.containment_executed: return False
        if tuple(item.check_id for item in value.checks) != CHECK_ORDER: return False
        if len(value.checks) != len(CHECK_ORDER) or len({item.check_id for item in value.checks}) != len(CHECK_ORDER): return False
        if not all(verify_operational_failure_containment_evidence_check(item) for item in value.checks): return False
        if not verify_operational_failure_incident_identity(value.evidence.incident_identity, value.deployment_evidence): return False
        expected = prepare_operational_failure_containment_evidence_foundation(
            value.evidence.incident_identity.incident_type,
            value.deployment_evidence, value.containment_acceptance)
        return expected is not None and value == expected and bool(
            _HEX.fullmatch(value.topology_digest or "")) and bool(
            _HEX.fullmatch(value.foundation_digest or "")) and value.foundation_digest == _digest(
                "EVIDENCE_FOUNDATION", _material(value, "foundation_digest"))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return False


__all__ = (
    "VERSION", "SCHEMA", "POLICY_IDENTITY", "POLICY_VERSION",
    "FOUNDATION_PREPARED", "FOUNDATION_REJECTED", "INCIDENT_TYPES", "CHECK_ORDER",
    "OperationalFailureContainmentEvidencePolicy", "OperationalFailureIncidentIdentity",
    "OperationalFailureEvidence", "OperationalFailureContainmentEvidenceCheck",
    "OperationalFailureContainmentEvidenceFoundation", "CANONICAL_EVIDENCE_POLICY",
    "prepare_operational_failure_containment_evidence_foundation",
    "classify_operational_failure_containment_evidence_foundation",
    "verify_operational_failure_containment_evidence_policy",
    "verify_operational_failure_incident_identity",
    "verify_operational_failure_containment_evidence_check",
    "verify_operational_failure_containment_evidence_foundation",
)
