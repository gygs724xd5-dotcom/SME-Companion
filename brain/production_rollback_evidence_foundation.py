"""V5.15.24.7.4.17 canonical, passive rollback-evidence foundation.

This module binds existing release-owned default-deny rollback material to one
exact transition proposal and accepted failure-containment evidence.  It grants
no approval, activation, deployment, or rollback execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from typing import Any, Mapping

from brain.production_failure_containment_acceptance import (
    ProductionFailureContainmentAcceptanceReport,
    verify_production_failure_containment_acceptance_report,
)
from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    verify_production_feature_gate_configuration,
)
from brain.production_feature_gate_release_owner import (
    ProductionFeatureGateReleaseOwnerSnapshot,
    ProductionFeatureGateTransitionProposal,
    get_production_feature_gate_release_owner,
    verify_production_feature_gate_release_owner,
    verify_production_feature_gate_rollback_target,
    verify_production_feature_gate_transition_proposal,
)

VERSION = "5.15.24.7.4.17"
SCOPE = "CANONICAL_PRODUCTION_ROLLBACK_EVIDENCE_FOUNDATION"
STATUS = "ROLLBACK_EVIDENCE_BOUND_NOT_ATTESTED"
ROLLBACK_ARTIFACT_KIND = "SOURCE_CONTROLLED_DEFAULT_DENY_CONFIGURATION_ARTIFACT"
IN_FLIGHT_POLICY = "DENY_NEW_EXECUTION_AND_SUPPRESS_DOWNSTREAM_RESPONSE_COMMIT"
VERIFICATION_REQUIREMENTS = (
    "VERIFY_EXACT_RELEASE_OWNER",
    "VERIFY_EXACT_PROPOSAL_AND_REVISION",
    "VERIFY_EXACT_ROLLBACK_TARGET",
    "VERIFY_ROLLBACK_ARTIFACT_DIGEST",
    "VERIFY_DEFAULT_DENY_CONFIGURATION",
    "VERIFY_FAILURE_CONTAINMENT_ACCEPTANCE",
    "VERIFY_IN_FLIGHT_SUPPRESSION_POLICY",
    "VERIFY_NO_AUTHORITY_OR_EXECUTION",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionRollbackEvidenceAuthorityBoundary:
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
class ProductionRollbackEvidenceFoundation:
    version: str
    scope: str
    status: str
    release_owner: ProductionFeatureGateReleaseOwnerSnapshot
    proposal: ProductionFeatureGateTransitionProposal
    failure_containment: ProductionFailureContainmentAcceptanceReport
    release_owner_digest: str
    release_revision_id: str
    release_revision_digest: str
    proposal_digest: str
    feature_gate_identity: str
    requested_target_state: bool
    rollback_target_identity: str
    rollback_target_digest: str
    rollback_artifact_kind: str
    rollback_artifact_identity: str
    rollback_artifact_digest: str
    rollback_configuration_identity: str
    rollback_configuration_digest: str
    rollback_entries: tuple[tuple[str, bool], ...]
    default_deny_restoration: bool
    in_flight_policy: str
    containment_report_digest: str
    containment_topology_digest: str
    verification_requirements: tuple[str, ...]
    evidence_lineage: tuple[str, ...]
    rollback_attested: bool = False
    deployment_attested: bool = False
    readiness_accepted: bool = False
    approval_evidence_permitted: bool = False
    activation_permitted: bool = False
    mutation_permitted: bool = False
    rollback_executed: bool = False
    executable_output: None = None
    authority_boundary: ProductionRollbackEvidenceAuthorityBoundary = (
        ProductionRollbackEvidenceAuthorityBoundary()
    )
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
    raise ValueError("unsupported rollback-evidence material")


def _digest(label: str, value: Any) -> str:
    encoded = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any, excluded: str) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value) if field.name != excluded)


def _all_false(value: Any) -> bool:
    return type(value) is ProductionRollbackEvidenceAuthorityBoundary and all(
        type(getattr(value, field.name)) is bool and not getattr(value, field.name)
        for field in fields(value))


def _inputs_valid(owner: Any, proposal: Any, containment: Any) -> bool:
    if type(owner) is not ProductionFeatureGateReleaseOwnerSnapshot:
        return False
    if owner is not get_production_feature_gate_release_owner():
        return False
    if not verify_production_feature_gate_release_owner(owner):
        return False
    if type(proposal) is not ProductionFeatureGateTransitionProposal:
        return False
    if not verify_production_feature_gate_transition_proposal(proposal):
        return False
    if proposal.source_revision_id != owner.release_revision.revision_id:
        return False
    if proposal.requested_gate_name != LIMITED_COST_RESPONSE_RUNTIME_BRIDGE:
        return False
    if proposal.requested_gate_state is not True:
        return False
    if type(containment) is not ProductionFailureContainmentAcceptanceReport:
        return False
    if not verify_production_failure_containment_acceptance_report(containment):
        return False
    if not verify_production_feature_gate_rollback_target(owner.rollback_target):
        return False
    target = owner.rollback_target
    return (
        target.target_revision_id == owner.release_revision.revision_id
        and target.target_configuration_digest == owner.configuration_digest
        and target.target_entries == ()
        and target.rollback_available is True
        and target.rollback_applied is False
        and verify_production_feature_gate_configuration(target.target_configuration)
        and containment.production_default_denied is True
        and containment.state_unchanged is True
        and containment.response_commit_absent is True
        and containment.rollback_attestation is None
    )


def _build(owner: ProductionFeatureGateReleaseOwnerSnapshot,
           proposal: ProductionFeatureGateTransitionProposal,
           containment: ProductionFailureContainmentAcceptanceReport
           ) -> ProductionRollbackEvidenceFoundation:
    target = owner.rollback_target
    target_identity = f"{target.source_identity}:{target.target_revision_id}:ROLLBACK_TARGET"
    configuration_identity = (
        f"{target.target_configuration.configuration_version}:"
        f"{target.target_configuration.trusted_source_identity}"
    )
    artifact_identity = (
        f"{ROLLBACK_ARTIFACT_KIND}:{target.source_identity}:"
        f"{target.target_revision_id}:{target.target_configuration_digest}"
    )
    artifact_digest = _digest("ROLLBACK_ARTIFACT", (
        artifact_identity, target.rollback_digest, configuration_identity,
        target.target_configuration_digest, target.target_entries))
    lineage = (
        owner.owner_digest,
        owner.release_revision.revision_digest,
        proposal.proposal_digest,
        target.rollback_digest,
        artifact_digest,
        containment.report_digest,
        containment.topology_digest,
    )
    draft = ProductionRollbackEvidenceFoundation(
        VERSION, SCOPE, STATUS, owner, proposal, containment,
        owner.owner_digest, owner.release_revision.revision_id,
        owner.release_revision.revision_digest, proposal.proposal_digest,
        proposal.requested_gate_name, proposal.requested_gate_state,
        target_identity, target.rollback_digest, ROLLBACK_ARTIFACT_KIND,
        artifact_identity, artifact_digest, configuration_identity,
        target.target_configuration_digest, target.target_entries, True,
        IN_FLIGHT_POLICY, containment.report_digest, containment.topology_digest,
        VERIFICATION_REQUIREMENTS, lineage,
    )
    return replace(draft, foundation_digest=_digest(
        "ROLLBACK_EVIDENCE_FOUNDATION", _material(draft, "foundation_digest")))


def create_production_rollback_evidence_foundation(
    release_owner: Any, proposal: Any, failure_containment: Any,
) -> ProductionRollbackEvidenceFoundation | None:
    """Bind exact canonical inputs; never infer, attest, approve, or execute."""
    try:
        if not _inputs_valid(release_owner, proposal, failure_containment):
            return None
        return _build(release_owner, proposal, failure_containment)
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_production_rollback_evidence_foundation(value: Any) -> bool:
    """Strictly reconstruct the foundation from its embedded canonical inputs."""
    try:
        if type(value) is not ProductionRollbackEvidenceFoundation:
            return False
        if not _all_false(value.authority_boundary):
            return False
        if any((value.rollback_attested, value.deployment_attested,
                value.readiness_accepted, value.approval_evidence_permitted,
                value.activation_permitted, value.mutation_permitted,
                value.rollback_executed)):
            return False
        if value.executable_output is not None:
            return False
        if value.verification_requirements != VERIFICATION_REQUIREMENTS:
            return False
        if not _HEX.fullmatch(value.foundation_digest or ""):
            return False
        expected = create_production_rollback_evidence_foundation(
            value.release_owner, value.proposal, value.failure_containment)
        return expected is not None and value == expected and value.foundation_digest == _digest(
            "ROLLBACK_EVIDENCE_FOUNDATION", _material(value, "foundation_digest"))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


__all__ = (
    "VERSION", "SCOPE", "STATUS", "ROLLBACK_ARTIFACT_KIND", "IN_FLIGHT_POLICY",
    "VERIFICATION_REQUIREMENTS", "ProductionRollbackEvidenceAuthorityBoundary",
    "ProductionRollbackEvidenceFoundation",
    "create_production_rollback_evidence_foundation",
    "verify_production_rollback_evidence_foundation",
)
