"""V5.15.24.7.4.19 passive production deployment-artifact evidence.

The artifact is a deterministic logical contract derived from exact verified
rollback-readiness inputs.  PREPARED means structurally evidence-bound only;
it does not mean deployed, approved, activated, or attested.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from typing import Any, Mapping

from brain.production_rollback_readiness_acceptance import (
    ACCEPTED as ROLLBACK_READINESS_ACCEPTED,
    ProductionRollbackReadinessAcceptance,
    verify_production_rollback_readiness_acceptance,
)

VERSION = "5.15.24.7.4.19"
SCOPE = "PRODUCTION_DEPLOYMENT_ARTIFACT_EVIDENCE_FOUNDATION"
PREPARED = "DEPLOYMENT_ARTIFACT_EVIDENCE_PREPARED"
REJECTED = "DEPLOYMENT_ARTIFACT_EVIDENCE_REJECTED"
ARTIFACT_SCHEMA = "production-deployment-artifact/v1"
ARTIFACT_TYPE = "PRODUCTION_DEPLOYMENT_ARTIFACT"
CHECK_ORDER = (
    "PROPOSAL_IDENTITY_VERIFIED",
    "REQUESTED_STATE_VERIFIED",
    "PROPOSAL_REVISION_VERIFIED",
    "FEATURE_GATE_IDENTITY_VERIFIED",
    "FEATURE_GATE_STATE_VERIFIED",
    "RUNTIME_CONFIGURATION_IDENTITY_VERIFIED",
    "RUNTIME_CONFIGURATION_DIGEST_VERIFIED",
    "DEPLOYMENT_ARTIFACT_IDENTITY_VERIFIED",
    "DEPLOYMENT_ARTIFACT_DIGEST_VERIFIED",
    "ARTIFACT_PROPOSAL_BINDING_VERIFIED",
    "ARTIFACT_REVISION_BINDING_VERIFIED",
    "ARTIFACT_GATE_BINDING_VERIFIED",
    "ARTIFACT_RUNTIME_CONFIGURATION_BINDING_VERIFIED",
    "DEPLOYMENT_NOT_EXECUTED",
    "FEATURE_GATE_NOT_MUTATED",
    "TRANSITION_NOT_APPROVED",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionDeploymentArtifactIdentity:
    schema: str
    artifact_type: str
    logical_name: str
    artifact_revision: str
    content_digest: str
    proposal_digest: str
    feature_gate_name: str
    feature_gate_requested_state: bool
    runtime_configuration_digest: str
    identity_digest: str = ""


@dataclass(frozen=True)
class ProductionDeploymentArtifactEvidenceCheck:
    check_id: str
    ordinal: int
    evidence_digests: tuple[str, ...]
    verified: bool
    reason: str
    check_digest: str = ""


@dataclass(frozen=True)
class ProductionDeploymentArtifactEvidence:
    version: str
    scope: str
    status: str
    readiness_acceptance: ProductionRollbackReadinessAcceptance
    readiness_acceptance_digest: str
    proposal_id: str
    requested_state: bool
    proposal_revision: str
    proposal_revision_digest: str
    feature_gate_name: str
    feature_gate_requested_state: bool
    runtime_configuration_identity: str
    runtime_configuration_digest: str
    artifact: ProductionDeploymentArtifactIdentity
    deployment_artifact_identity: str
    deployment_artifact_digest: str
    artifact_to_proposal_binding_digest: str
    artifact_to_revision_binding_digest: str
    artifact_to_gate_binding_digest: str
    artifact_to_runtime_configuration_binding_digest: str
    checks: tuple[ProductionDeploymentArtifactEvidenceCheck, ...]
    issues: tuple[str, ...]
    deployment_executed: bool = False
    feature_gate_mutated: bool = False
    transition_approved: bool = False
    deployment_attested: bool = False
    rollback_executed: bool = False
    approval_permitted: bool = False
    executable_output: None = None
    topology_digest: str = ""
    evidence_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, Mapping):
        return [[str(key), _canonical(value[key])] for key in sorted(value)]
    if is_dataclass(value) and not isinstance(value, type):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported deployment-artifact evidence material")


def _digest(label: str, value: Any) -> str:
    encoded = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any, *excluded: str) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value)
        if field.name not in excluded)


def _upstream_valid(value: Any) -> bool:
    if type(value) is not ProductionRollbackReadinessAcceptance:
        return False
    if not verify_production_rollback_readiness_acceptance(value):
        return False
    foundation = value.foundation
    return (
        value.status == ROLLBACK_READINESS_ACCEPTED
        and value.accepted is True
        and value.readiness_evidence_permitted is True
        and value.requested_target_state is True
        and value.proposal_digest == foundation.proposal_digest
        and value.release_revision_id == foundation.release_revision_id
        and value.release_revision_digest == foundation.release_revision_digest
        and value.feature_gate_identity == foundation.feature_gate_identity
        and value.rollback_configuration_identity == foundation.rollback_configuration_identity
        and value.rollback_configuration_digest == foundation.rollback_configuration_digest
        and foundation.rollback_entries == ()
        and not any((value.deployment_attested, value.rollback_executed,
            value.transition_approved, value.activation_permitted, value.mutation_permitted))
        and value.executable_output is None
    )


def _build_artifact(value: ProductionRollbackReadinessAcceptance):
    logical_name = f"{value.feature_gate_identity}:deployment-artifact"
    content_digest = _digest("ARTIFACT_CONTENT", (
        value.proposal_digest, value.release_revision_id,
        value.release_revision_digest, value.feature_gate_identity,
        value.requested_target_state, value.rollback_configuration_identity,
        value.rollback_configuration_digest, value.acceptance_digest))
    draft = ProductionDeploymentArtifactIdentity(
        ARTIFACT_SCHEMA, ARTIFACT_TYPE, logical_name, value.release_revision_id,
        content_digest, value.proposal_digest, value.feature_gate_identity,
        value.requested_target_state, value.rollback_configuration_digest)
    return replace(draft, identity_digest=_digest(
        "DEPLOYMENT_ARTIFACT_IDENTITY", _material(draft, "identity_digest")))


def verify_production_deployment_artifact_identity(
    value: Any, readiness_acceptance: Any,
) -> bool:
    try:
        if type(value) is not ProductionDeploymentArtifactIdentity:
            return False
        if not _upstream_valid(readiness_acceptance):
            return False
        expected = _build_artifact(readiness_acceptance)
        return value == expected and bool(_HEX.fullmatch(value.content_digest or "")) and bool(
            _HEX.fullmatch(value.identity_digest or ""))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def _binding(label: str, artifact: ProductionDeploymentArtifactIdentity, *values: Any):
    return _digest(label, (artifact.identity_digest,) + values)


def _check(identifier: str, ordinal: int, evidence: tuple[str, ...], reason: str):
    draft = ProductionDeploymentArtifactEvidenceCheck(
        identifier, ordinal, evidence, True, reason)
    return replace(draft, check_digest=_digest(
        "DEPLOYMENT_ARTIFACT_CHECK", _material(draft, "check_digest")))


def _build(value: ProductionRollbackReadinessAcceptance):
    artifact = _build_artifact(value)
    proposal_binding = _binding("ARTIFACT_PROPOSAL_BINDING", artifact, value.proposal_digest)
    revision_binding = _binding("ARTIFACT_REVISION_BINDING", artifact,
        value.release_revision_id, value.release_revision_digest)
    gate_binding = _binding("ARTIFACT_GATE_BINDING", artifact,
        value.feature_gate_identity, value.requested_target_state)
    configuration_binding = _binding("ARTIFACT_CONFIGURATION_BINDING", artifact,
        value.rollback_configuration_identity, value.rollback_configuration_digest)
    evidence = (
        (value.proposal_digest,), (value.proposal_digest,),
        (value.release_revision_digest,), (value.proposal_digest,),
        (value.proposal_digest,), (value.rollback_configuration_digest,),
        (value.rollback_configuration_digest,), (artifact.identity_digest,),
        (artifact.content_digest,), (proposal_binding,), (revision_binding,),
        (gate_binding,), (configuration_binding,), (value.acceptance_digest,),
        (value.acceptance_digest,), (value.acceptance_digest,),
    )
    reasons = (
        "canonical proposal identity verified", "exact requested production state verified",
        "exact proposal revision verified", "supported feature gate identity verified",
        "exact requested gate state verified", "runtime configuration identity verified",
        "runtime configuration digest verified", "deployment artifact identity verified",
        "deployment artifact content digest verified", "artifact bound to exact proposal",
        "artifact bound to exact revision", "artifact bound to exact gate and state",
        "artifact bound to exact runtime configuration", "deployment execution remains absent",
        "feature gate mutation remains absent", "transition approval remains absent",
    )
    checks = tuple(_check(identifier, index + 1, evidence[index], reasons[index])
        for index, identifier in enumerate(CHECK_ORDER))
    topology = _digest("DEPLOYMENT_ARTIFACT_TOPOLOGY", (
        value.acceptance_digest, artifact.identity_digest,
        proposal_binding, revision_binding, gate_binding, configuration_binding,
        tuple(item.check_digest for item in checks)))
    draft = ProductionDeploymentArtifactEvidence(
        VERSION, SCOPE, PREPARED, value, value.acceptance_digest,
        value.proposal_digest, value.requested_target_state,
        value.release_revision_id, value.release_revision_digest,
        value.feature_gate_identity, value.requested_target_state,
        value.rollback_configuration_identity, value.rollback_configuration_digest,
        artifact, artifact.identity_digest, artifact.content_digest,
        proposal_binding, revision_binding, gate_binding, configuration_binding,
        checks, (), topology_digest=topology)
    return replace(draft, evidence_digest=_digest(
        "DEPLOYMENT_ARTIFACT_EVIDENCE", _material(draft, "evidence_digest")))


def prepare_production_deployment_artifact_evidence(
    readiness_acceptance: Any,
) -> ProductionDeploymentArtifactEvidence | None:
    """Prepare evidence from one exact verified upstream acceptance only."""
    try:
        if not _upstream_valid(readiness_acceptance):
            return None
        return _build(readiness_acceptance)
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def classify_production_deployment_artifact_evidence(readiness_acceptance: Any) -> str:
    return PREPARED if prepare_production_deployment_artifact_evidence(
        readiness_acceptance) is not None else REJECTED


def verify_production_deployment_artifact_evidence_check(value: Any) -> bool:
    try:
        return (
            type(value) is ProductionDeploymentArtifactEvidenceCheck
            and value.check_id in CHECK_ORDER
            and value.ordinal == CHECK_ORDER.index(value.check_id) + 1
            and value.verified is True and bool(value.reason)
            and bool(value.evidence_digests)
            and all(_HEX.fullmatch(item or "") for item in value.evidence_digests)
            and bool(_HEX.fullmatch(value.check_digest or ""))
            and value.check_digest == _digest(
                "DEPLOYMENT_ARTIFACT_CHECK", _material(value, "check_digest"))
        )
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def verify_production_deployment_artifact_evidence(value: Any) -> bool:
    try:
        if type(value) is not ProductionDeploymentArtifactEvidence:
            return False
        if value.version != VERSION or value.scope != SCOPE or value.status != PREPARED:
            return False
        if value.issues != () or any((value.deployment_executed,
                value.feature_gate_mutated, value.transition_approved,
                value.deployment_attested, value.rollback_executed,
                value.approval_permitted)) or value.executable_output is not None:
            return False
        if tuple(item.check_id for item in value.checks) != CHECK_ORDER:
            return False
        if len({item.check_id for item in value.checks}) != len(CHECK_ORDER):
            return False
        if not all(verify_production_deployment_artifact_evidence_check(item)
                for item in value.checks):
            return False
        if not verify_production_deployment_artifact_identity(
                value.artifact, value.readiness_acceptance):
            return False
        expected = prepare_production_deployment_artifact_evidence(
            value.readiness_acceptance)
        return expected is not None and value == expected and bool(
            _HEX.fullmatch(value.topology_digest or "")) and bool(
            _HEX.fullmatch(value.evidence_digest or "")) and value.evidence_digest == _digest(
                "DEPLOYMENT_ARTIFACT_EVIDENCE", _material(value, "evidence_digest"))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


__all__ = (
    "VERSION", "SCOPE", "PREPARED", "REJECTED", "ARTIFACT_SCHEMA",
    "ARTIFACT_TYPE", "CHECK_ORDER", "ProductionDeploymentArtifactIdentity",
    "ProductionDeploymentArtifactEvidenceCheck", "ProductionDeploymentArtifactEvidence",
    "prepare_production_deployment_artifact_evidence",
    "classify_production_deployment_artifact_evidence",
    "verify_production_deployment_artifact_identity",
    "verify_production_deployment_artifact_evidence_check",
    "verify_production_deployment_artifact_evidence",
)
